"""
MergeMind — Ledger and Budget Models

Pydantic V2 definitions for the MongoDB Streaming Ledger and Budget Pools.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class BudgetPool(BaseModel):
    """Represents an escrow budget allocated for a specific project."""
    pool_id: str
    project_id: int
    total_budget: float
    remaining_budget: float
    currency: str = "USD"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LedgerEntry(BaseModel):
    """Represents a single automated payment transaction in the streaming ledger."""
    entry_id: str
    pool_id: str
    merge_request_id: int
    author_username: str
    impact_score: int
    payment_amount: float
    evaluation_summary: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: Optional[str] = Field(
        default=None,
        description="The Arize OpenTelemetry trace ID for auditability.",
    )
