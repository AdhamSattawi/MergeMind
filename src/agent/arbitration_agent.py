"""
MergeMind — Arbitration Agent Definition

Defines the core ADK Agent that orchestrates code evaluation using
GitLab MCP, MongoDB MCP, and custom heuristics/scoring tools.
"""

import logging

from google.adk.agents import Agent
from google.adk.tools import McpToolset
from mcp.client.stdio import StdioServerParameters

from config.settings import settings
from src.agent.prompts import ARBITRATION_SYSTEM_PROMPT
from src.tools.heuristics import analyze_diff
from src.tools.scoring import calculate_payment

logger = logging.getLogger("mergemind.agent")


def create_arbitration_agent() -> Agent:
    """
    Create and configure the MergeMind Arbitration Agent.

    The agent uses:
    - GitLab MCP Server: For fetching MR diffs, file contents, and posting comments.
    - MongoDB MCP Server: For reading budget pools and writing to the streaming ledger.
    - Custom tools: Heuristics analysis and payment calculation.

    Returns:
        Agent: A configured ADK Agent ready for invocation.
    """

    # --- MCP Tool: GitLab ---
    # Provides the agent with capabilities to interact with GitLab:
    # - get_merge_request / get_merge_request_diffs: Fetch MR details and code changes
    # - get_file_contents: Fetch full file context for deeper analysis
    # - create_note: Post evaluation results as comments on the MR
    gitlab_mcp = McpToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=["-y", "@zereight/mcp-gitlab"],
            env={
                "GITLAB_PERSONAL_ACCESS_TOKEN": settings.gitlab_personal_access_token,
                "GITLAB_API_URL": settings.gitlab_api_url,
            },
        )
    )

    # --- MCP Tool: MongoDB ---
    # Provides the agent with capabilities to interact with the database:
    # - find: Query budget_pools to check remaining escrow
    # - insertOne: Write evaluation records to streaming_ledger
    # - updateOne: Deduct payment amounts from budget_pools
    # - aggregate: Run analytical queries on historical evaluations
    mongo_mcp = McpToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "mongodb-mcp-server",
                "--connectionString",
                settings.mongodb_uri,
            ],
        )
    )

    # --- MCP Tool: Arize Phoenix ---
    # Provides the agent with self-introspection capabilities to hit the "Bonus Points" track.
    # The agent can query its own past traces and evaluations to calibrate its scoring
    # and improve its decision-making loop over time.
    arize_mcp = McpToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@arizeai/phoenix-mcp@latest",
                "--baseUrl", "https://app.phoenix.arize.com",
                "--apiKey", settings.arize_api_key,
            ],
        )
    )

    # --- Build the Agent ---
    agent = Agent(
        model="gemini-2.0-flash",
        name="mergemind_arbitration_engine",
        description=(
            "An AI-Assisted Arbitration Engine that evaluates code contributions "
            "from GitLab Merge Requests, scores them on multiple quality dimensions, "
            "and manages automated compensation through a streaming ledger."
        ),
        instruction=ARBITRATION_SYSTEM_PROMPT,
        tools=[
            gitlab_mcp,         # MCP: GitLab operations
            mongo_mcp,          # MCP: MongoDB ledger operations
            arize_mcp,          # MCP: Arize self-introspection (Bonus points)
            analyze_diff,       # Custom: Deterministic heuristics analysis
            calculate_payment,  # Custom: Score-to-payment conversion
        ],
    )

    logger.info("Arbitration Agent created successfully with GitLab, MongoDB, and Arize MCP tools")

    # TODO: Initialize Arize tracing for this agent
    # from src.observability.tracer import setup_tracing
    # setup_tracing()

    return agent
