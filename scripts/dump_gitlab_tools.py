import asyncio
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

async def run():
    p = StdioServerParameters(
        command='npx',
        args=['-y', '@zereight/mcp-gitlab'],
        env={'GITLAB_PERSONAL_ACCESS_TOKEN': 'dummy', 'GITLAB_API_URL': 'https://gitlab.com/api/v4'}
    )
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            for t in tools.tools:
                print(f"- {t.name}")

if __name__ == "__main__":
    asyncio.run(run())
