"""
MergeMind — Arbitration Agent Definition

Defines the core ADK Agent that orchestrates code evaluation using
GitLab MCP, Elastic MCP, Fivetran MCP, Dynatrace MCP, and custom native tools.
"""

import logging
import functools
import os

from google.adk.agents import Agent
from google.adk.tools import McpToolset
from google.adk.models.google_llm import Gemini
from google.genai import Client
from google.adk.tools.mcp_tool.mcp_toolset import StdioConnectionParams
from mcp import StdioServerParameters

from config.settings import settings
from src.agent.prompts import ARBITRATION_SYSTEM_PROMPT
from src.tools.heuristics import analyze_diff, fetch_gitlab_mr_diff, post_gitlab_mr_comment, fetch_gitlab_issue
from src.tools.scoring import calculate_payment
from src.tools.elastic_writer import index_evaluation_to_elastic
from src.tools.ledger import check_budget, record_evaluation_and_payment

logger = logging.getLogger("mergemind.agent")


class VertexGemini(Gemini):
    @functools.cached_property
    def api_client(self) -> Client:
        return Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location="us-central1"
        )


def get_arbitration_agent() -> Agent:
    return create_arbitration_agent()


def create_arbitration_agent() -> Agent:
    """
    Create and configure the MergeMind Arbitration Agent.

    Uses a combination of MCP toolsets (for hackathon partner track compliance)
    and native Python tools (for reliability and fallback).

    Returns:
        Agent: A configured ADK Agent ready for invocation.
    """

    # --- MCP Tool: GitLab (Partner Track) ---
    # Official GitLab MCP server for MR/issue/diff access.
    gitlab_mcp = None
    if settings.gitlab_personal_access_token:
        gitlab_mcp = McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="mcp-server-gitlab",
                    args=[],
                    env={
                        **os.environ,
                        "GITLAB_PERSONAL_ACCESS_TOKEN": settings.gitlab_personal_access_token,
                        "GITLAB_API_URL": settings.gitlab_api_url,
                    },
                ),
                timeout=60,
            )
        )

    # --- MCP Tool: Elastic (Partner Track) ---
    # Elasticsearch MCP server for indexing evaluations and querying history.
    elastic_mcp = None
    if settings.elastic_api_key and (settings.elastic_id or settings.elastic_cloud_id):
        elastic_env = {
            **os.environ, 
            "OTEL_SDK_DISABLED": "true",
        }
        elastic_env["ELASTIC_API_KEY"] = settings.elastic_api_key
        if settings.elastic_id:
            elastic_env["ES_URL"] = settings.elastic_id
        if settings.elastic_cloud_id:
            elastic_env["ES_CLOUD_ID"] = settings.elastic_cloud_id

        elastic_mcp = McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="mcp-server-elasticsearch",
                    args=[],
                    env=elastic_env,
                ),
                timeout=60,
            )
        )

    # --- MCP Tool: Fivetran (Partner Track) ---
    # Custom Python MCP server for triggering data syncs to BigQuery.
    fivetran_mcp = None
    if settings.fivetran_api_key and settings.fivetran_api_secret:
        fivetran_mcp = McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="python",
                    args=["src/tools/fivetran_mcp/server.py"],
                    env={
                        **os.environ,
                        "FIVETRAN_API_KEY": settings.fivetran_api_key,
                        "FIVETRAN_API_SECRET": settings.fivetran_api_secret,
                        "FIVETRAN_ALLOW_WRITES": str(settings.fivetran_allow_writes).lower(),
                    },
                ),
                timeout=60,
            )
        )

    # --- MCP Tool: Dynatrace (Partner Track) ---
    # Checks for active vulnerabilities before finalizing payments.
    dynatrace_mcp = None
    if settings.dt_platform_token and settings.dynatrace_environment:
        dynatrace_mcp = McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="mcp-server-dynatrace",
                    args=[],
                    env={
                        **os.environ,
                        "DT_ENVIRONMENT": settings.dynatrace_environment,
                        "DT_PLATFORM_TOKEN": settings.dt_platform_token,
                        "DT_MCP_DISABLE_TELEMETRY": "true",
                    },
                ),
                timeout=60,
            )
        )

    # --- Build tool list ---
    tools = [
        # Native GitLab tools (reliable fallback + direct API access)
        fetch_gitlab_mr_diff,
        post_gitlab_mr_comment,
        fetch_gitlab_issue,

        # Heuristics & scoring
        analyze_diff,
        calculate_payment,

        # Native MongoDB tools
        check_budget,
        record_evaluation_and_payment,

        # Native Elastic tool
        index_evaluation_to_elastic,
    ]

    for mcp_tool in [gitlab_mcp, elastic_mcp, fivetran_mcp, dynatrace_mcp]:
        if mcp_tool:
            tools.append(mcp_tool)

    agent = Agent(
        model=VertexGemini(model="gemini-2.5-flash"),
        name="mergemind_arbitration_engine",
        description=(
            "An AI-Assisted Arbitration Engine that evaluates code contributions "
            "from GitLab Merge Requests, scores them on multiple quality dimensions, "
            "and manages automated compensation through a streaming ledger."
        ),
        instruction=ARBITRATION_SYSTEM_PROMPT,
        tools=tools,
    )

    logger.info("Arbitration Agent created with MCP tools: GitLab, Elastic, Fivetran, Dynatrace + native tools")
    return agent
