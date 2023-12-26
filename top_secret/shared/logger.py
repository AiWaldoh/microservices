import httpx
from pydantic import BaseModel
from config import LOGGING_SERVICE_URL  # Import the configuration


class LogMessage(BaseModel):
    message: str


def send_log(message: str):
    log_message = LogMessage(message=message)
    try:
        with httpx.Client() as client:
            client.post(f"{LOGGING_SERVICE_URL}/log", json=log_message.dict())
    except httpx.RequestError as e:
        print(f"An error occurred while sending log message: {str(e)}")
