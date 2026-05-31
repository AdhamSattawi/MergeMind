import logging
import json
from datetime import datetime
from elasticsearch import Elasticsearch
from config.settings import settings

logger = logging.getLogger(__name__)

import functools

@functools.lru_cache()
def get_es_client() -> Elasticsearch:
    if settings.elastic_cloud_id:
        return Elasticsearch(
            cloud_id=settings.elastic_cloud_id,
            api_key=settings.elastic_api_key
        )
    return Elasticsearch(
        settings.elastic_id,
        api_key=settings.elastic_api_key
    )

def index_evaluation_to_elastic(merge_request_iid: int, project_name: str, impact_score: int, summary_verdict: str) -> str:
    """
    Indexes the evaluation summary and impact score to Elasticsearch for future searchability.
    Use this tool to permanently record the AI's decision after evaluating a Merge Request.
    
    Args:
        merge_request_iid: The GitLab Merge Request IID.
        project_name: The name of the GitLab project.
        impact_score: The final calculated impact score (0-100).
        summary_verdict: A detailed text explanation of the AI's reasoning.
        
    Returns:
        A success message indicating the document was indexed.
    """
    try:
        es = get_es_client()
        
        doc = {
            "merge_request_iid": merge_request_iid,
            "project_name": project_name,
            "impact_score": impact_score,
            "summary_verdict": summary_verdict,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Write to the 'code_evaluations' index
        response = es.index(index="code_evaluations", document=doc)
        logger.info(f"Indexed evaluation to Elastic: {response['result']}")
        return f"Successfully indexed evaluation for MR {merge_request_iid} to Elasticsearch index 'code_evaluations'."
    except Exception as e:
        logger.error(f"Failed to index to Elasticsearch: {e}", exc_info=True)
        return f"Failed to index to Elasticsearch: {str(e)}"
