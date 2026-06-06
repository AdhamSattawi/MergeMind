"""
MergeMind — GitLab Webhook Endpoint

Receives incoming GitLab Merge Request events via webhook POST requests,
validates the payload, and triggers the Arbitration Agent for evaluation.
"""

import logging
import asyncio
import base64
import uuid
import re
import hmac
import hashlib
from fastapi import APIRouter, HTTPException, Request, status, BackgroundTasks, Header

from src.models.gitlab_payload import GitLabMergeRequestEvent
from src.models.evaluation import CodeEvaluation
from src.agent.arbitration_agent import get_arbitration_agent
from config.settings import settings
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part

logger = logging.getLogger("mergemind.webhooks")

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

def verify_signature(secret: str, webhook_id: str, timestamp: str, raw_body: bytes, received_signature: str) -> bool:
    """Verifies the HMAC-SHA256 signature from GitLab."""
    try:
        if secret.startswith("whsec_"):
            key = base64.b64decode(secret[6:])
        else:
            key = secret.encode('utf-8')
            
        message = f"{webhook_id}.{timestamp}.".encode('utf-8') + raw_body
        computed_hmac = hmac.new(key, message, hashlib.sha256).digest()
        computed_signature = f"v1,{base64.b64encode(computed_hmac).decode('utf-8')}"
        
        return hmac.compare_digest(computed_signature, received_signature)
    except Exception as e:
        logger.error(f"Error computing signature: {e}")
        return False


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
    x_gitlab_token: str = Header(default=""),
    webhook_id: str = Header(default="", alias="webhook-id"),
    webhook_timestamp: str = Header(default="", alias="webhook-timestamp"),
    webhook_signature: str = Header(default="", alias="webhook-signature"),
):
    """
    Handle incoming GitLab Merge Request webhook events.

    This endpoint:
    1. Validates the incoming payload against the GitLab MR event schema.
    2. Performs HMAC-SHA256 verification if signing token is configured.
    3. Filters for actionable events (open, update, merge).
    4. Triggers the Arbitration Agent asynchronously.
    5. Returns 202 Accepted immediately.
    """
    if settings.gitlab_webhook_secret:
        if webhook_signature and webhook_id and webhook_timestamp:
            raw_body = await request.body()
            is_valid = verify_signature(
                settings.gitlab_webhook_secret,
                webhook_id,
                webhook_timestamp,
                raw_body,
                webhook_signature
            )
            if not is_valid:
                logger.warning("Rejected webhook: invalid HMAC signature")
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        elif x_gitlab_token != settings.gitlab_webhook_secret:
            logger.warning("Rejected webhook: invalid x-gitlab-token")
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


async def run_agent_task(event: GitLabMergeRequestEvent):
    """
    Background task that actually invokes the ADK Agent.
    Must be async so that FastAPI runs it on the event loop,
    giving the ADK MCP toolsets the async context they require.
    """
    mr = event.object_attributes
    try:
        logger.info(f"Starting background agent evaluation for MR {mr.iid}...")
        
        mr_description = mr.description or "(No description provided — no issue linked.)"
        task_prompt = (
            f"Please evaluate Merge Request IID {mr.iid} in the project '{event.project.name}' "
            f"(Project ID: {event.project.id}).\n\n"
            f"MR Title: {mr.title}\n"
            f"MR Description: {mr_description}\n\n"
            "Ensure you do self-introspection first, check heuristics, perform the Ticket Validation Loop "
            "(checking if the code aligns with a linked issue in the description), and finally execute "
            "the payment and ledger logic."
        )
        message = Content(role="user", parts=[Part.from_text(text=task_prompt)])
        
        agent = get_arbitration_agent()
        runner = InMemoryRunner(agent=agent, app_name="mergemind")
        
        # Use a unique session ID per webhook invocation to prevent MCP session
        # collisions when concurrent webhooks fire before the previous one tears down.
        session_id = f"{mr.iid}-{uuid.uuid4().hex[:8]}"
        try:
            await runner.session_service.create_session(
                app_name="mergemind", user_id="webhook", session_id=session_id
            )
        except Exception:
            pass

        responses = []
        try:
            async for e in runner.run_async(user_id="webhook", session_id=session_id, new_message=message):
                responses.append(e)
        except ValueError as ve:
            # Gemini raises this when the model returns an empty response — typically
            # triggered by a completely blank/junk MR description with no issue linked.
            # The model's safety layer refuses to process it and returns nothing.
            if "model output must contain either output text or tool calls" in str(ve):
                logger.warning(
                    f"\n{'='*70}\n"
                    f" ❌ MR REJECTED — AUTOMATIC REJECTION\n"
                    f"{'='*70}\n"
                    f" Merge Request : #{mr.iid}\n"
                    f" Project       : {event.project.name}\n"
                    f" Reason        : No linked issue and/or no meaningful description.\n"
                    f"                 MergeMind requires every MR to reference a valid\n"
                    f"                 GitLab Issue (e.g. 'Closes #15').\n"
                    f" Payment       : $0.00\n"
                    f"{'='*70}\n"
                )
                return
            raise  # Re-raise unexpected ValueErrors

        if not responses:
            logger.warning(f"Agent finished evaluating MR {mr.iid} but returned no response.")
            return

        # Scan ALL responses for a JSON block — the last event is often just a
        # turn-complete signal with no text content, so we must not only check [-1].
        raw_str = ""
        for resp in reversed(responses):
            if hasattr(resp, "content") and hasattr(resp.content, "parts"):
                for part in resp.content.parts:
                    if hasattr(part, "text") and part.text:
                        raw_str += part.text
            if raw_str:
                break  # Stop at the first response that has text

        if not raw_str:
            # Final fallback: stringify the last response
            raw_str = str(responses[-1])

        # Check if the agent crashed with a malformed function call
        if "MALFORMED_FUNCTION_CALL" in raw_str:
            logger.error(f"Agent crashed due to MALFORMED_FUNCTION_CALL. MR: {mr.iid}")
            logger.error(f"Raw Crash Data: {raw_str}")
            return

        # Extract JSON — prefer a fenced ```json block, then fall back to bare {}
        json_match = re.search(r'```json\s*(.*?)\s*```', raw_str, re.DOTALL)
        if json_match:
            clean_json = json_match.group(1).strip()
        else:
            json_match = re.search(r'\{.*\}', raw_str, re.DOTALL)
            clean_json = json_match.group(0).strip() if json_match else raw_str

        # Unescape quotes that ADK repr may have mangled
        clean_json = clean_json.replace('\\"', '"')
        if clean_json.startswith("'{") and clean_json.endswith("}'"):
            clean_json = clean_json[1:-1]

        try:
            evaluation = CodeEvaluation.model_validate_json(clean_json)

            # --- Pretty Logging ---
            box_width = 70
            logger.info("\n" + "="*box_width)
            logger.info(f" 🤖 MERGEMIND EVALUATION COMPLETE ".center(box_width, "="))
            logger.info("="*box_width)
            logger.info(f" Merge Request : #{mr.iid}")
            logger.info(f" Project       : {event.project.name}")
            logger.info(f" Relevant      : {'✅ YES' if evaluation.is_relevant else '❌ NO'}")
            logger.info(f" Suspicious    : {'⚠️ YES' if evaluation.is_suspicious else '✅ NO'}")
            logger.info(f" Impact Score  : {evaluation.impact_score}/100")
            logger.info("-" * box_width)
            logger.info(" Metrics:")
            logger.info(f"   - Logic & Efficiency      : {evaluation.metrics.logic_and_efficiency}")
            logger.info(f"   - Architectural Soundness : {evaluation.metrics.architectural_soundness}")
            logger.info(f"   - Robustness & Security   : {evaluation.metrics.robustness_and_security}")
            logger.info(f"   - Test Coverage           : {evaluation.metrics.test_coverage_contribution}")
            logger.info("-" * box_width)
            logger.info(f" Verdict:\n   {evaluation.summary_verdict}")
            logger.info("="*box_width + "\n")

        except Exception as parse_err:
            raw_excerpt = raw_str[:300] + "..." if len(raw_str) > 300 else raw_str
            logger.error(f"Agent permanently failed to return valid schema for MR {mr.iid}. Error: {parse_err}")
            logger.error(f"Raw Output Excerpt: {raw_excerpt}")

    except Exception as e:
        logger.error(f"Agent evaluation failed for MR {mr.iid}: {e}", exc_info=True)
