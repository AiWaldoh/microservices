from fastapi import FastAPI, HTTPException
import requests
import json
from pydantic import BaseModel


app = FastAPI()

# Configuration for the microservices endpoints
COMMAND_SERVICE_URL = "http://localhost:8003"
OPENAI_SERVICE_URL = "http://localhost:8001/completion"


class ClientCommandExecutor:
    @staticmethod
    def start_command(command):
        """Send a request to start a command."""
        try:
            response = requests.post(
                f"{COMMAND_SERVICE_URL}/commands/start", json={"command": command}
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    def get_command_status(process_id):
        """Send a request to get the status of a command."""
        try:
            response = requests.get(
                f"{COMMAND_SERVICE_URL}/commands/status",
                params={"process_id": process_id},
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise HTTPException(status_code=400, detail=str(e))


class CommandRequest(BaseModel):
    verbal_command: str


@app.post("/execute_command/")
async def execute_command(request: CommandRequest):
    verbal_command = request.verbal_command
    print("Received verbal command:", verbal_command)
    try:
        # The data to send in the POST request
        data = {
            "prompt": f"""
                convert the following verbal command to a linux command
                and return the answer in valid json:
                "{verbal_command}"

                You must return valid json. The json must contain a key called "command"
                and the value must be a valid linux command.
                Example verbal command: "show me the files in the folder"
                Example response: {{"command": "ls"}}
                """,
            "streaming": False,
            "model": "gpt-3.5-turbo",
        }

        response = requests.post(OPENAI_SERVICE_URL, json=data)

        # Check if the request was successful
        if response.status_code == 200:
            json_resp = response.json()["completion"]
            command = json.loads(json_resp)["command"]
            print(command)

            # Start the command
            start_response = ClientCommandExecutor.start_command(command)
            process_id = start_response.get("process_id")

            # Get command status
            status_response = ClientCommandExecutor.get_command_status(process_id)
            if not status_response.get("running", True):
                return {"output": status_response["output"]}
            else:
                return {"status": "Command is still running"}
        else:
            print("Error:", response.status_code, response.text)
            raise HTTPException(status_code=response.status_code, detail=response.text)

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
