"""
MergeMind — Webhook Simulation Script

Sends a dummy GitLab Merge Request payload to the local FastAPI server
for end-to-end testing of the webhooks and agent trigger pipeline.
"""

import datetime
import httpx
import asyncio


async def simulate_webhook():
    """Sends a mock GitLab webhook to the local server."""
    
    url = "http://localhost:8000/api/v1/webhooks/gitlab"
    
    # Mock payload matching the GitLab webhook schema
    payload = {
        "object_kind": "merge_request",
        "user": {
            "id": 12345,
            "username": "adham",
            "name": "Adham Sattawi",
            "email": "adham.sattawi@example.com"
        },
        "project": {
            "id": 67890,
            "name": "liquidhub-demo",
            "web_url": "https://gitlab.com/adham/liquidhub-demo",
            "namespace": "adham"
        },
        "object_attributes": {
            "id": 9999,
            "iid": 42,
            "title": "feat: Optimize database queries",
            "description": "Refactored the main loop to use async DB drivers.",
            "state": "opened",
            "source_branch": "feature/async-db",
            "target_branch": "main",
            "author_id": 12345,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "url": "https://gitlab.com/adham/liquidhub-demo/-/merge_requests/42",
            "action": "open"
        }
    }

    print(f"Sending mock webhook to {url}...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
    except httpx.ConnectError:
        print("Error: Could not connect to the server. Is it running on port 8000?")


if __name__ == "__main__":
    asyncio.run(simulate_webhook())
