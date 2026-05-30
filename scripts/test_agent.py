import asyncio
from src.agent.arbitration_agent import create_arbitration_agent
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part

async def test_agent():
    print("🤖 Initializing MergeMind Arbitration Agent...")
    try:
        agent = create_arbitration_agent()
        runner = InMemoryRunner(agent=agent, app_name="mergemind")
        print("✅ Agent successfully initialized with all MCP tools!")
        
        print("\nSending a test prompt to the agent...")
        task_prompt = "List all the MCP tools you currently have access to from Elasticsearch and Dynatrace. Just list their names."
        message = Content(role="user", parts=[Part.from_text(text=task_prompt)])
        
        try:
            runner.session_service.create_session_sync(app_name="mergemind", user_id="test", session_id="test_run")
        except Exception:
            pass
            
        print("\n📝 Agent Response:")
        for response in runner.run(user_id="test", session_id="test_run", new_message=message):
            # Print the final text content of the response
            if getattr(response, "text", None):
                print(response.text)
            elif getattr(response, "content", None):
                print(response.content)
            else:
                print(response)
        
    except Exception as e:
        print(f"❌ Agent initialization or execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent())
