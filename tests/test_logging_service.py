# test_logging_service.py

from fastapi.testclient import TestClient
from unittest.mock import patch
import pytest
from top_secret.logging_service import (
    app,
)  # Adjust the import according to your actual file structure
from pydantic import BaseModel, Field


class LogMessage(BaseModel):
    message: str = Field(..., min_length=1)


client = TestClient(app)


@pytest.fixture
def mock_log_storage():
    with patch(
        "top_secret.logging_service.LogStorage.store", return_value=None
    ) as mock_method:
        yield mock_method


def test_log_message_success(mock_log_storage):
    response = client.post("/log", json={"message": "Test log message"})
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    mock_log_storage.assert_called_once_with("Test log message")


def test_log_message_failure():
    response = client.post("/log", json={})
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Field required"


def test_log_message_empty():
    response = client.post("/log", json={"message": ""})
    assert response.status_code == 422
    assert (
        "String should have at least 1 character" in response.json()["detail"][0]["msg"]
    )
