"""
MergeMind — Scoring Tool

Converts the AI's subjective impact score into an objective payment amount.
This enforces business rules and budgets outside of the LLM's control.
"""

from typing import Any, Dict


def calculate_payment(
    impact_score: int,
    budget_remaining: float,
    max_per_mr: float,
    threshold: int
) -> Dict[str, Any]:
    """
    Calculates the automated payment amount based on the impact score.

    This acts as a tool for the ADK Agent to determine compensation. It
    ensures the LLM cannot arbitrarily assign money; it must provide a
    score, which deterministic logic converts to dollars.

    Args:
        impact_score: The 0-100 score assigned by the agent.
        budget_remaining: Current balance in the project's budget pool.
        max_per_mr: Maximum allowable payment for a single MR.
        threshold: Minimum score required to trigger a payment.

    Returns:
        Dict with payment details.
    """
    if impact_score < 0 or impact_score > 100:
        return {
            "payment_amount": 0.0,
            "approved": False,
            "reason": "Invalid impact score. Must be between 0 and 100.",
        }

    if impact_score < threshold:
        return {
            "payment_amount": 0.0,
            "approved": False,
            "reason": f"Impact score ({impact_score}) is below the threshold ({threshold}).",
        }

    if budget_remaining <= 0:
        return {
            "payment_amount": 0.0,
            "approved": False,
            "reason": "Budget pool is exhausted.",
        }

    # Calculation: Proportional payment based on score, capped at max_per_mr
    calculated_payment = (impact_score / 100.0) * max_per_mr

    # Cap at remaining budget
    actual_payment = min(calculated_payment, budget_remaining)

    return {
        "payment_amount": round(actual_payment, 2),
        "approved": True,
        "reason": f"Payment approved based on score of {impact_score}.",
    }
