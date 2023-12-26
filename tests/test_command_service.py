# test_command_service.py

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pytest
from top_secret.services.command_executor_service.main import (
    app,
    ProcessManager,
    CommandExecutor,
)

client = TestClient(app)


@pytest.fixture
def mock_process_manager():
    with patch.object(
        ProcessManager, "create_process", return_value="fake-process-id"
    ) as mock_method:
        yield mock_method


@pytest.fixture
def mock_command_executor():
    executor = MagicMock(spec=CommandExecutor)
    executor.is_running.return_value = False
    executor.get_output.return_value = "fake output"
    with patch(
        "top_secret.services.command_executor_service.main",
        return_value=executor,
    ):
        yield executor


def test_start_command_ls(mock_process_manager, mock_command_executor):
    response = client.post("/commands/start", json={"command": "ls"})
    assert response.status_code == 200
    assert response.json() == {"process_id": "fake-process-id"}
    mock_process_manager.assert_called_once_with("ls", None)


def test_start_command_ls_with_timeout(mock_process_manager, mock_command_executor):
    response = client.post("/commands/start", json={"command": "ls", "timeout": 10})
    assert response.status_code == 200
    assert response.json() == {"process_id": "fake-process-id"}
    mock_process_manager.assert_called_once_with("ls", 10)


def test_start_command_missing_command():
    response = client.post("/commands/start", json={})
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Field required"
    assert response.json()["detail"][0]["loc"] == ["body", "command"]
