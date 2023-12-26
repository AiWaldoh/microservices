from fastapi import FastAPI, status
from pydantic import BaseModel, Field
import threading
import os

app = FastAPI()
log_file_path = "./logs/services.log"  # Adjusted to use a relative path

# Ensure thread-safe file writing
log_file_lock = threading.Lock()


class LogMessage(BaseModel):
    message: str = Field(..., min_length=1)


# LogStorage: Handles the storage of log messages.
class LogStorage:
    def store(self, message: str):
        """Store the log message in a file."""
        with log_file_lock:
            with open(log_file_path, "a") as log_file:
                log_file.write(message + "\n")


# LogController: Interface for handling log messages.
class LogController:
    def __init__(self, log_storage: LogStorage):
        self.log_storage = log_storage

    async def log_message(self, message: str):
        """Receive a log message and store it."""
        self.log_storage.store(message)
        return True


# LogAPI: FastAPI route for the Logging Microservice.
@app.post("/log", status_code=status.HTTP_200_OK)
async def log_message(log_message: LogMessage):
    log_storage = LogStorage()
    log_controller = LogController(log_storage)
    await log_controller.log_message(log_message.message)
    return {"status": "success"}


# Ensure the log file exists
if not os.path.exists(log_file_path):
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    open(log_file_path, "a").close()

# Note: FastAPI's development server can be run using `uvicorn` from the command line:
# uvicorn your_module_name:app --reload --host 0.0.0.0 --port 5001
