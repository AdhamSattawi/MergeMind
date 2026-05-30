from src.agent.arbitration_agent import create_arbitration_agent
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
import asyncio

agent = create_arbitration_agent()
runner = InMemoryRunner(agent=agent, app_name=mergemind)

runner.session_service.create_session_sync(app_name=mergemind, user_id=webhook, session_id=42)
message = Content(role=user, parts=[Part.from_text(text=hello)])

for e in runner.run(user_id=webhook, session_id=42, new_message=message):
    print(Event:, type(e))
