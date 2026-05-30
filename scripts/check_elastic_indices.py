import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession
from config.settings import settings

async def run():
    p = StdioServerParameters(
        command='npx',
        args=['-y', '@elastic/mcp-server-elasticsearch'],
        env={
            "ES_URL": settings.elastic_id,
            "ES_API_KEY": settings.elastic_api_key,
            "OTEL_SDK_DISABLED": "true",
        }
    )
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            print("Listing indices...")
            try:
                response = await s.call_tool("elasticsearch_raw_api", {
                    "method": "GET",
                    "path": "/_cat/indices?format=json"
                })
                print(response)
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
