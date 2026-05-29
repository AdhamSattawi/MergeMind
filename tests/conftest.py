"""
MergeMind — Pytest Fixtures

Common fixtures for the pytest suite, including a FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient

# We'll import the app once it's created in main.py
# from main import app

@pytest.fixture
def test_client():
    """Returns a TestClient instance for the FastAPI application."""
    # return TestClient(app)
    pass
