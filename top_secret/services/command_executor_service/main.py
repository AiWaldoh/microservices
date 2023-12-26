import pexpect
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from uuid import uuid4
import threading

app = FastAPI()

# ProcessManager: Manages the lifecycle of command executions.


class ProcessManager:
    """
    Manages the lifecycle and operations of command executions.

    Attributes:
        processes (dict): A dictionary mapping process IDs to CommandExecutor instances.
    """

    def __init__(self):
        """
        Initializes the ProcessManager with an empty dictionary for tracking processes.
        """
        self.processes = {}  # Maps process_id to CommandExecutor instances.

    def create_process(self, command, timeout=None):
        """
        Creates a new CommandExecutor instance and returns a unique process ID.

        Args:
            command (str): The command to be executed.
            timeout (int, optional): The maximum time in seconds for the command to run.

        Returns:
            str: A unique process ID for the created command execution.
        """

        process_id = str(uuid4())
        executor = CommandExecutor(command, timeout)
        self.processes[process_id] = executor
        executor.execute()
        return process_id

    def terminate_process(self, process_id):
        """
        Terminates the process associated with the given process ID.

        Args:
            process_id (str): The ID of the process to terminate.

        Returns:
            bool: True if the process was successfully terminated, False otherwise.
        """
        if process_id in self.processes:
            self.processes[process_id].interrupt()
            return True
        return False

    def get_process_status(self, process_id):
        """
        Retrieves the status of the process associated with the given process ID.

        Args:
            process_id (str): The ID of the process whose status is being queried.

        Returns:
            dict or None: A dictionary containing 'running' status and 'output' of the
            process, or None if process ID is not found.
        """
        if process_id in self.processes:
            return {
                "running": self.processes[process_id].is_running(),
                "output": self.processes[process_id].get_output(),
            }
        return None


# CommandExecutor: Handles the execution and interaction with a shell command.


class CommandExecutor:
    """
    Executes and manages a shell command process.

    Attributes:
        command (str): The command to be executed.
        timeout (int, optional): The maximum time in seconds for the command to run.
        process (pexpect.spawn or None): The pexpect process instance.
        output (str): Accumulated output of the command.
        working_dir (str): The working directory for the command execution.
    """

    def __init__(self, command, timeout=None):
        """
        Initializes the CommandExecutor with the given command and optional timeout.
        """
        self.command = command
        self.timeout = timeout
        self.process = None  # pexpect.spawn instance.
        self.output = ""  # Store the output of the command.
        self.working_dir = "/app/data"  # Set the working directory to /app/data

    def execute(self):
        """
        Executes the command using pexpect with the specified timeout and working
        directory.
        """
        self.process = pexpect.spawn(
            self.command, timeout=self.timeout, cwd=self.working_dir
        )
        self._capture_output()

    def _capture_output(self):
        """
        Internal method to read and store the output of the command in a separate
        thread.
        """

        def read_output():
            while True:
                try:
                    line = self.process.readline()
                    if not line:
                        break
                    self.output += line.decode("utf-8")
                except pexpect.EOF:
                    break
                except pexpect.TIMEOUT:
                    continue

        # Start a thread to read the process output
        output_thread = threading.Thread(target=read_output)
        output_thread.start()

    def interrupt(self):
        """
        Sends an interrupt signal to the running process and terminates it.
        """
        if self.process is not None:
            self.process.sendcontrol("c")
            self.process.terminate(force=True)

    def is_running(self):
        """
        Checks if the process is still running.

        Returns:
            bool: True if the process is alive, False otherwise.
        """
        return self.process is not None and self.process.isalive()

    def get_output(self):
        """
        Retrieves the current output of the command.

        Returns:
            str: The output of the command up to the current point.
        """
        if self.process is not None:
            return self.process.before.decode("utf-8")
        return ""


# CommandController: Interface for managing commands.


class CommandController:
    """
    Provides an interface for managing command executions using a ProcessManager.

    Attributes:
        process_manager (ProcessManager): The ProcessManager instance used for command
        execution and management.
    """

    def __init__(self, process_manager):
        """
        Initializes the CommandController with a given ProcessManager.
        """
        self.process_manager = process_manager

    def start_command(self, command, timeout=None):
        """
        Starts a new command execution and returns a process ID.

        Args:
            command (str): The command to be executed.
            timeout (int, optional): The maximum time in seconds for the command to run.

        Returns:
            str: A unique process ID for the started command execution.
        """
        return self.process_manager.create_process(command, timeout)

    def stop_command(self, process_id):
        """
        Stops the command execution associated with the given process ID.

        Args:
            process_id (str): The ID of the process to stop.

        Returns:
            bool: True if the command was successfully stopped, False otherwise.
        """
        return self.process_manager.terminate_process(process_id)

    def get_status(self, process_id):
        """
        Returns the status of the command execution associated with the
          given process ID.

        Args:
            process_id (str): The ID of the process whose status is being queried.

        Returns:
            dict or None: A dictionary containing the status and output of the command,
              or None if the process ID is invalid.
        """
        status = self.process_manager.get_process_status(process_id)
        if status:
            status["output"] = self.process_manager.processes[process_id].output
        return status


# Define the request models for FastAPI
class StartCommandRequest(BaseModel):
    command: str
    timeout: int = None


class StopCommandRequest(BaseModel):
    process_id: str


# Initialize your controllers
process_manager = ProcessManager()
command_controller = CommandController(process_manager)


@app.post("/commands/start")
async def start_command(command_request: StartCommandRequest):
    """
    Endpoint to start a new command execution.

    Args:
        command_request (StartCommandRequest): The request body containing the command
          and optional timeout.

    Returns:
        dict: A dictionary containing the 'process_id' of the started command.

    Raises:
        HTTPException: 400 Bad Request if the command is missing.
    """

    if command_request.command:
        process_id = command_controller.start_command(
            command_request.command, command_request.timeout
        )
        return {"process_id": process_id}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing command"
        )


@app.post("/commands/stop")
async def stop_command(stop_request: StopCommandRequest):
    """
    Endpoint to stop an ongoing command execution.

    Args:
        stop_request (StopCommandRequest): The request body containing the
          'process_id' of the command to stop.

    Returns:
        dict: A dictionary indicating whether the command was successfully stopped.

    Raises:
        HTTPException: 400 Bad Request if the 'process_id' is missing.
    """
    if stop_request.process_id:
        success = command_controller.stop_command(stop_request.process_id)
        return {"stopped": success}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing process_id"
        )


@app.get("/commands/status")
async def get_status(process_id: str):
    """
    Endpoint to get the status of an ongoing or completed command execution.

    Args:
        process_id (str): The 'process_id' of the command whose status is being queried.

    Returns:
        dict: A dictionary containing the status and output of the command.

    Raises:
        HTTPException: 400 Bad Request if the 'process_id' is missing.
        HTTPException: 404 Not Found if the 'process_id' is invalid.
    """
    if process_id:
        status = command_controller.get_status(process_id)
        if status is not None:
            return status
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invalid process_id"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing process_id"
        )
