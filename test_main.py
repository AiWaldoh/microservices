from fastapi.testclient import TestClient
from unittest.mock import patch
from top_secret.command_service import (
    app,
)  # Correct import path based on your file structure

client = TestClient(app)


# Define your tests here, using the correct module path for patching
def test_start_command_ls():
    with patch(
        "top_secret.command_service.ProcessManager.create_process"
    ) as mock_create_process:
        mock_create_process.return_value = "fake-process-id"
        response = client.post("/commands/start", json={"command": "ls"})
        assert response.status_code == 200
        assert response.json() == {"process_id": "fake-process-id"}
        mock_create_process.assert_called_once_with("ls", None)


def test_start_command_ls_with_timeout():
    # Mock the ProcessManager's create_process method
    with patch("main.ProcessManager.create_process") as mock_create_process:
        # Configure the mock to return a fake process ID
        mock_create_process.return_value = "fake-process-id"

        # Make a request to the /commands/start endpoint with the 'ls' command and
        # a timeout
        response = client.post("/commands/start", json={"command": "ls", "timeout": 10})

        # Assert that the request was successful and returned the correct process ID
        assert response.status_code == 200
        assert response.json() == {"process_id": "fake-process-id"}

        # Assert that the mock was called with the 'ls' command and a timeout
        mock_create_process.assert_called_once_with("ls", 10)


def test_start_command_missing_command():
    # Make a request to the /commands/start endpoint without a command
    response = client.post("/commands/start", json={})

    # Assert that the request failed due to a missing command
    assert response.status_code == 400
    assert response.json() == {"detail": "Missing command"}
