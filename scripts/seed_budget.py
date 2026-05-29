"""
MergeMind — Budget Seeding Script

Connects to MongoDB and seeds an initial Budget Pool for testing the 
payment evaluation logic.
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


def seed_database():
    """Seeds the MongoDB database with a starting budget."""
    
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/mergemind")
    
    print(f"Connecting to MongoDB at: {uri}")
    client = MongoClient(uri)
    db = client.get_database()
    
    # Define a starting budget
    budget_pool = {
        "pool_id": "demo_pool_1",
        "project_id": 67890,  # Matches the simulate_webhook project ID
        "total_budget": 10000.0,
        "remaining_budget": 10000.0,
        "currency": "USD"
    }
    
    # Insert or update
    result = db.budget_pools.update_one(
        {"pool_id": budget_pool["pool_id"]},
        {"$set": budget_pool},
        upsert=True
    )
    
    if result.upserted_id:
        print("Successfully created new budget pool.")
    else:
        print("Successfully reset existing budget pool.")
        
    # Show current state
    current = db.budget_pools.find_one({"pool_id": "demo_pool_1"})
    print(f"Current pool state: {current}")


if __name__ == "__main__":
    seed_database()
