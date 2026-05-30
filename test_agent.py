import asyncio
from src.agent.arbitration_agent import create_arbitration_agent
from google.adk import Context

agent = create_arbitration_agent()

async def run():
    async for e in agent.run(node_input=test, ctx=Context()):
        print(e)

asyncio.run(run())
