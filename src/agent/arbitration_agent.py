"""
MergeMind — Arbitration Agent Definition

Defines the core ADK Agent that orchestrates code evaluation using
GitLab MCP, MongoDB MCP, and custom heuristics/scoring tools.
"""

import logging
import functools

from google.adk.agents import Agent
from google.adk.tools import McpToolset
from google.adk.models.google_llm import Gemini
from google.genai import Client
from mcp.client.stdio import StdioServerParameters

from config.settings import settings
from src.agent.prompts import ARBITRATION_SYSTEM_PROMPT
from src.tools.heuristics import analyze_diff, fetch_gitlab_mr_diff, post_gitlab_mr_comment
from src.tools.scoring import calculate_payment
from src.tools.elastic_writer import index_evaluation_to_elastic

logger = logging.getLogger("mergemind.agent")

class VertexGemini(Gemini):
    @functools.cached_property
    def api_client(self) -> Client:
        return Client(
            vertexai=True, 
            project=settings.google_cloud_project, 
            location="us-central1"
        )

@functools.lru_cache(maxsize=1)
def get_arbitration_agent() -> Agent:
    return create_arbitration_agent()

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
    # - get_issue / get_merge_request / search_issues
    gitlab_mcp = McpToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-gitlab"],
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
            command="mongodb-mcp-server",
            args=[],
            env={
                "MDB_MCP_CONNECTION_STRING": settings.mongodb_uri
            }
        )
    )

    # --- MCP Tool: Arize Phoenix ---
    # Disabled because phoenix-mcp is not installed in the Docker container.
    # arize_mcp = McpToolset(
    #     connection_params=StdioServerParameters(
    #         command="phoenix-mcp",
    #         args=[
    #             "--baseUrl", "https://app.phoenix.arize.com",
    #             "--apiKey", settings.arize_api_key,
    #         ],
    #         env={
    #             "OTEL_SDK_DISABLED": "true"
    #         }
    #     )
    # )

    # --- MCP Tool: Elastic ---
    # Provides the agent with capabilities to interact with Elasticsearch:
    # - It will index a summary of every evaluated Merge Request, creating a searchable knowledge base
    #   of past decisions, ensuring consistency across reviews over time.
    elastic_env = {"OTEL_SDK_DISABLED": "true"}
    if settings.elastic_id:
        elastic_env["ES_URL"] = settings.elastic_id
    if settings.elastic_cloud_id:
        elastic_env["ES_CLOUD_ID"] = settings.elastic_cloud_id
    if settings.elastic_api_key:
        elastic_env["ES_API_KEY"] = settings.elastic_api_key

    elastic_mcp = McpToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=["-y", "@elastic/mcp-server-elasticsearch"],
            env=elastic_env,
        )
    )

    # --- MCP Tool: Fivetran ---
    # Provides the agent with capabilities to interact with Fivetran:
    # - It will monitor or trigger the data sync from MongoDB to BigQuery after
    #   evaluations are completed.
    fivetran_mcp = McpToolset(
        connection_params=StdioServerParameters(
            command="python",
            args=["src/tools/fivetran_mcp/server.py"],
            env={
                "FIVETRAN_API_KEY": settings.fivetran_api_key,
                "FIVETRAN_API_SECRET": settings.fivetran_api_secret,
                "FIVETRAN_ALLOW_WRITES": settings.fivetran_allow_writes,
            },
        )
    )

    # --- MCP Tool: Dynatrace ---
    # Provides the agent with capabilities to interact with Dynatrace:
    # - It will check for active vulnerabilities or system health degradations in production
    #   before finalizing any payments, ensuring developers aren't breaking the system.
    dynatrace_mcp = None
    if settings.dt_platform_token:
        dynatrace_mcp = McpToolset(
            connection_params=StdioServerParameters(
                command="npx",
                args=["-y", "@dynatrace-oss/dynatrace-mcp-server"],
                env={
                    "DT_ENVIRONMENT": settings.dynatrace_environment,
                    "DT_PLATFORM_TOKEN": settings.dt_platform_token,
                    "DT_MCP_DISABLE_TELEMETRY": "true",
                },
            )
        )

    # --- Build the Agent ---
    tools = [
        gitlab_mcp,         # MCP: Official GitLab server
        mongo_mcp,          # MCP: MongoDB ledger operations
        # arize_mcp,        # DISABLED
        elastic_mcp,        # MCP: Elastic log search and query
        fivetran_mcp,       # MCP: Fivetran sync orchestration
        fetch_gitlab_mr_diff, # Custom: Direct GitLab API diff fetcher (workaround for broken MCP)
        post_gitlab_mr_comment, # Custom: Direct GitLab API comment poster (workaround for broken MCP)
        analyze_diff,       # Custom: Deterministic heuristics analysis
        calculate_payment,  # Custom: Score-to-payment conversion
        index_evaluation_to_elastic, # Custom: Write evaluation to Elastic
    ]
    if dynatrace_mcp:
        tools.append(dynatrace_mcp)

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

    logger.info("Arbitration Agent created successfully with GitLab, MongoDB, Arize, Elastic, Fivetran, and Dynatrace MCP tools")

    return agent
