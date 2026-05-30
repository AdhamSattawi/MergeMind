import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

async def run():
    p = StdioServerParameters(
        command='npx',
        args=['-y', '@elastic/mcp-server-elasticsearch'],
        env={'ES_CLOUD_ID': 'test_cloud_id', 'ES_API_KEY': 'test', 'OTEL_SDK_DISABLED': 'true'}
    )
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            print('Success')

if __name__ == '__main__':
    asyncio.run(run())
