import pytest
from src.tools.scoring import calculate_payment
from config.settings import settings

# We will mock the threshold in settings for the tests to ensure predictability
@pytest.fixture(autouse=True)
def mock_threshold(monkeypatch):
    monkeypatch.setattr(settings, "payment_threshold_score", 30)

@pytest.mark.parametrize(
    "impact_score, budget_remaining, max_per_mr, expected_amount, expected_approved",
    [
        # Edge case: Score below threshold
        (20, 1000.0, 500.0, 0.0, False),
        
        # Edge case: Score exactly at threshold
        (30, 1000.0, 500.0, 150.0, True),
        
        # Normal case: Score above threshold
        (80, 1000.0, 500.0, 400.0, True),
        
        # Edge case: Score of 100 (Max payment)
        (100, 1000.0, 500.0, 500.0, True),
        
        # Edge case: Exhausted budget (0 remaining)
        (90, 0.0, 500.0, 0.0, False),
        
        # Edge case: Budget remaining is less than calculated payment (capped at budget)
        (100, 200.0, 500.0, 200.0, True),
        
        # Edge case: Invalid negative score
        (-10, 1000.0, 500.0, 0.0, False),
        
        # Edge case: Invalid score > 100
        (110, 1000.0, 500.0, 0.0, False),
    ]
)
def test_calculate_payment(impact_score, budget_remaining, max_per_mr, expected_amount, expected_approved):
    result = calculate_payment(impact_score, budget_remaining, max_per_mr)
    
    assert result["payment_amount"] == expected_amount
    assert result["approved"] == expected_approved
    
    if not expected_approved:
        assert "reason" in result
        assert len(result["reason"]) > 0
