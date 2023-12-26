import httpx
from pydantic import BaseModel


class LogMessage(BaseModel):
    message: str


def send_log(message: str, log_service_url: str):
    log_message = LogMessage(message=message)
    try:
        with httpx.Client() as client:
            client.post(f"{log_service_url}/log", json=log_message.dict())
    except httpx.RequestError as e:
        print(f"An error occurred while sending log message: {str(e)}")
