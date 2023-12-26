from fastapi import FastAPI, status
from pydantic import BaseModel, Field
import threading
import os

app = FastAPI()
log_file_path = "./logs/services.log"  # Adjusted to use a relative path

# Ensure thread-safe file writing
log_file_lock = threading.Lock()


class LogMessage(BaseModel):
    """
    Represents a log message input.

    Attributes:
        message (str): The log message content. Must be at least 1 character long.
    """

    message: str = Field(..., min_length=1)


# LogStorage: Handles the storage of log messages.
class LogStorage:
    """
    Manages the storage of log messages in a file.
    """

    def store(self, message: str):
        """
        Stores a log message in the log file.

        Args:
            message (str): The log message to be stored.

        Note:
            This method uses a thread-safe approach to write to the log file.
        """
        with log_file_lock:
            with open(log_file_path, "a") as log_file:
                log_file.write(message + "\n")


# LogController: Interface for handling log messages.
class LogController:
    """
    Provides an interface for logging operations.

    Attributes:
        log_storage (LogStorage): The LogStorage instance used for storing log messages.
    """

    def __init__(self, log_storage: LogStorage):
        """
        Initializes the LogController with a LogStorage instance.

        Args:
            log_storage (LogStorage): An instance of LogStorage for
             handling log message storage.
        """
        self.log_storage = log_storage

    async def log_message(self, message: str):
        """
        Processes and stores a log message.

        Args:
            message (str): The log message to be processed and stored.

        Returns:
            bool: True if the log message was successfully stored.
        """
        self.log_storage.store(message)
        return True


# LogAPI: FastAPI route for the Logging Microservice.
@app.post("/log", status_code=status.HTTP_200_OK)
async def log_message(log_message: LogMessage):
    """
    Endpoint for logging a message.

    Receives a log message and stores it using the LogController.

    Args:
        log_message (LogMessage): The log message to be stored.

    Returns:
        dict: A dictionary with the status of the logging operation.
    """
    log_storage = LogStorage()
    log_controller = LogController(log_storage)
    await log_controller.log_message(log_message.message)
    return {"status": "success"}


# Ensure the log file exists
if not os.path.exists(log_file_path):
    """
    Ensures that the log file and its directory exist.

    Creates the log file and its directory if they do not already exist.
    """
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    open(log_file_path, "a").close()
