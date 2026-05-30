from src.agent.arbitration_agent import create_arbitration_agent
from google.adk.runners import InMemoryRunner
import asyncio

agent = create_arbitration_agent()
runner = InMemoryRunner(agent=agent)

async def run():
    async for e in runner.run(user_id=test, session_id=1, new_message=hello):
        print(e)

asyncio.run(run())
