from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import requests
import logging

# Define the FastAPI app
app = FastAPI()

# URLs for the microservices
CONVERT_COMMAND_SERVICE_URL = "http://127.0.0.1:5005/convert-command"
COMMAND_SERVICE_URL = "http://127.0.0.1:5000/commands/start"

# Set up logging
logging.basicConfig(level=logging.INFO)


# Define the request model for FastAPI
class CommandRequest(BaseModel):
    verbose_command: str


# Define the endpoint for orchestrating the command
@app.post("/orchestrate-command")
async def orchestrate_command(command_request: CommandRequest):
    verbose_command = command_request.verbose_command

    try:
        # Log the URL being called
        logging.info(
            f"Calling convert_command service at {CONVERT_COMMAND_SERVICE_URL}"
        )

        # Step 1: Call the convert_command service to get the CLI command
        convert_response = requests.post(
            CONVERT_COMMAND_SERVICE_URL, json={"verbose_command": verbose_command}
        )
        convert_response.raise_for_status()

        cli_command = convert_response.json().get("command")

        # Log the URL being called
        logging.info(f"Calling command_service at {COMMAND_SERVICE_URL}")

        # Step 2: Call the command_service to execute the CLI command
        command_response = requests.post(
            COMMAND_SERVICE_URL, json={"command": cli_command}
        )
        command_response.raise_for_status()

        return command_response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to orchestrate command",
        )


# Run the application using Uvicorn if needed
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=5002)
