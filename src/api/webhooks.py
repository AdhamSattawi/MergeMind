"""
MergeMind — GitLab Webhook Endpoint

Receives incoming GitLab Merge Request events via webhook POST requests,
validates the payload, and triggers the Arbitration Agent for evaluation.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, status

from src.models.gitlab_payload import GitLabMergeRequestEvent

logger = logging.getLogger("mergemind.webhooks")

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post(
    "/gitlab",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive GitLab Merge Request Webhook",
    description="Accepts a GitLab webhook payload for Merge Request events "
    "and triggers the MergeMind Arbitration Agent.",
)
async def handle_gitlab_webhook(event: GitLabMergeRequestEvent, request: Request):
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

    # TODO: Trigger the Arbitration Agent here
    # This will be wired up when the agent is fully integrated.
    # agent_response = await run_arbitration_agent(event)

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
