import os
from typing import Dict, Any, List
import datetime
from pymongo import MongoClient

from config.settings import settings

client = MongoClient(settings.mongodb_uri)
db = client.get_database("mergemind")

def check_budget(project_id: int) -> Dict[str, Any]:
    """
    Checks the remaining budget for a project in MongoDB.
    
    Args:
        project_id: The GitLab project ID.
        
    Returns:
        A dictionary containing the budget status.
    """
    pool = db.budget_pools.find_one({"project_id": project_id})
    if not pool:
        return {"error": "Budget pool not found"}
        
    return {
        "project_id": project_id,
        "remaining_budget": pool.get("remaining_budget", 0),
        "total_budget": pool.get("total_budget", 0)
    }

def record_evaluation_and_payment(
    merge_request_iid: int,
    project_id: int,
    author_username: str,
    impact_score: int,
    payment_amount: float,
    evaluation_summary: str
) -> Dict[str, Any]:
    """
    Records an evaluation to the ledger and deducts the payment from the budget.
    
    Args:
        merge_request_iid: The GitLab MR IID.
        project_id: The GitLab project ID.
        author_username: The MR author username.
        impact_score: The calculated score (0-100).
        payment_amount: The calculated bounty amount.
        evaluation_summary: A brief string summarizing the reason for the score.
        
    Returns:
        Status dictionary.
    """
    # 1. Update budget
    db.budget_pools.update_one(
        {"project_id": project_id},
        {"$inc": {"remaining_budget": -payment_amount}}
    )
    
    # 2. Insert to ledger
    entry = {
        "merge_request_iid": merge_request_iid,
        "project_id": project_id,
        "author_username": author_username,
        "impact_score": impact_score,
        "payment_amount": payment_amount,
        "evaluation_summary": evaluation_summary,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    result = db.streaming_ledger.insert_one(entry)
    
    return {"status": "success", "inserted_id": str(result.inserted_id)}
