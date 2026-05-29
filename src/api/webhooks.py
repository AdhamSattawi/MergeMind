"""
MergeMind — GitLab Webhook Endpoint

Receives incoming GitLab Merge Request events via webhook POST requests,
validates the payload, and triggers the Arbitration Agent for evaluation.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, status, BackgroundTasks

from src.models.gitlab_payload import GitLabMergeRequestEvent
from src.agent.arbitration_agent import create_arbitration_agent
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part

logger = logging.getLogger("mergemind.webhooks")

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post(
    "/gitlab",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive GitLab Merge Request Webhook",
    description="Accepts a GitLab webhook payload for Merge Request events "
    "and triggers the MergeMind Arbitration Agent.",
)
async def handle_gitlab_webhook(event: GitLabMergeRequestEvent, request: Request, background_tasks: BackgroundTasks):
    """
    Handle incoming GitLab Merge Request webhook events.

    This endpoint:
    1. Validates the incoming payload against the GitLab MR event schema.
    2. Filters for actionable events (open, update, merge).
    3. Triggers the Arbitration Agent asynchronously.
    4. Returns 202 Accepted immediately.
    """
    mr = event.object_attributes
    logger.info(
        "Received MR event: action=%s, mr_iid=%s, project=%s, author=%s",
        mr.action,
        mr.iid,
        event.project.name,
        event.user.username,
    )

    # Only process actionable MR events
    actionable_events = {"open", "update", "merge", "reopen"}
    if mr.action not in actionable_events:
        logger.info("Skipping non-actionable event: action=%s", mr.action)
        return {
            "status": "skipped",
            "reason": f"Action '{mr.action}' is not actionable",
        }

    # Trigger the Arbitration Agent in the background
    background_tasks.add_task(run_agent_task, event)

    logger.info(
        "MR event accepted for processing: mr_iid=%s, project=%s",
        mr.iid,
        event.project.name,
    )

    return {
        "status": "accepted",
        "merge_request_iid": mr.iid,
        "project": event.project.name,
        "action": mr.action,
    }


async def run_agent_task(event: GitLabMergeRequestEvent):
    """
    Background task that actually invokes the ADK Agent.
    """
    mr = event.object_attributes
    try:
        logger.info(f"Starting background agent evaluation for MR {mr.iid}...")
        agent = create_arbitration_agent()
        runner = InMemoryRunner(agent=agent)
        
        task_prompt = f"Please evaluate Merge Request IID {mr.iid} in the {event.project.name} repository. Ensure you do self-introspection first, check heuristics, and finally execute the payment and ledger logic."
        message = Content(role="user", parts=[Part.from_text(text=task_prompt)])
        
        # Invoke the agent
        responses = []
        for e in runner.run(user_id="webhook", new_message=message):
            responses.append(e)
            
        logger.info(f"Agent finished evaluating MR {mr.iid}. Final Response: {responses[-1] if responses else 'No response'}")
        
    except Exception as e:
        logger.error(f"Agent evaluation failed for MR {mr.iid}: {e}", exc_info=True)
