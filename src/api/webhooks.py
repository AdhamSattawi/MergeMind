"""
MergeMind — GitLab Webhook Endpoint

Receives incoming GitLab Merge Request events via webhook POST requests,
validates the payload, and triggers the Arbitration Agent for evaluation.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, status, BackgroundTasks, Header

from src.models.gitlab_payload import GitLabMergeRequestEvent
from src.models.evaluation import CodeEvaluation
from src.agent.arbitration_agent import create_arbitration_agent
from config.settings import settings
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
async def handle_gitlab_webhook(
    event: GitLabMergeRequestEvent,
    request: Request,
    background_tasks: BackgroundTasks,
    x_gitlab_token: str = Header(default="")
):
    """
    Handle incoming GitLab Merge Request webhook events.

    This endpoint:
    1. Validates the incoming payload against the GitLab MR event schema.
    2. Filters for actionable events (open, update, merge).
    3. Triggers the Arbitration Agent asynchronously.
    4. Returns 202 Accepted immediately.
    """
    if settings.gitlab_webhook_secret and x_gitlab_token != settings.gitlab_webhook_secret:
        logger.warning("Rejected webhook: invalid x-gitlab-token signature")
        raise HTTPException(status_code=401, detail="Invalid webhook token")

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


def run_agent_task(event: GitLabMergeRequestEvent):
    """
    Background task that actually invokes the ADK Agent.
    """
    mr = event.object_attributes
    try:
        logger.info(f"Starting background agent evaluation for MR {mr.iid}...")
        agent = create_arbitration_agent()
        runner = InMemoryRunner(agent=agent, app_name="mergemind")
        
        task_prompt = f"Please evaluate Merge Request IID {mr.iid} in the project '{event.project.name}' (Project ID: {event.project.id}). Ensure you do self-introspection first, check heuristics, and finally execute the payment and ledger logic."
        message = Content(role="user", parts=[Part.from_text(text=task_prompt)])
        
        try:
            runner.session_service.create_session_sync(app_name="mergemind", user_id="webhook", session_id=str(mr.iid))
        except Exception:
            pass
            
        # Invoke the agent
        responses = []
        for e in runner.run(user_id="webhook", session_id=str(mr.iid), new_message=message):
            responses.append(e)
            
        if not responses:
            logger.warning(f"Agent finished evaluating MR {mr.iid} but returned no response.")
            return

        # Attempt to parse and validate the JSON output to enforce the schema
        raw_response = responses[-1]
        try:
            # ADK often wraps JSON in markdown blocks, clean it first if needed
            clean_json = raw_response.text.strip() if hasattr(raw_response, 'text') else str(raw_response)
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:-3].strip()
            evaluation = CodeEvaluation.model_validate_json(clean_json)
            logger.info(f"Agent successfully evaluated MR {mr.iid}. Validated Schema: impact_score={evaluation.impact_score}")
        except Exception as parse_err:
            logger.error(f"Agent returned invalid schema for MR {mr.iid}. Raw: {raw_response}. Error: {parse_err}")
            
    except Exception as e:
        logger.error(f"Agent evaluation failed for MR {mr.iid}: {e}", exc_info=True)
