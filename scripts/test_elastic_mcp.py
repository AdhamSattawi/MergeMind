import asyncio
import traceback
import os
from mcp import ClientSession
from mcp.client.sse import sse_client

async def test_elastic():
    print("🔌 Connecting to Elastic MCP server via SSE...")
    try:
        # Connect via the exposed port on the docker network
        async with sse_client(url="http://elastic-mcp:8080/sse") as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Successfully connected and initialized session!\n")
                
                tools = await session.list_tools()
                print("🛠️  Available Elasticsearch Tools:")
                for tool in tools.tools:
                    print(f"  - {tool.name}: {tool.description}")
                    
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_elastic())
