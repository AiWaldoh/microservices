import pexpect
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from uuid import uuid4
import threading

app = FastAPI()

# ProcessManager: Manages the lifecycle of command executions.


class ProcessManager:
    def __init__(self):
        self.processes = {}  # Maps process_id to CommandExecutor instances.

    def create_process(self, command, timeout=None):
        """Create a new CommandExecutor instance and return a process_id."""
        process_id = str(uuid4())
        executor = CommandExecutor(command, timeout)
        self.processes[process_id] = executor
        executor.execute()
        return process_id

    def terminate_process(self, process_id):
        """Terminate the process associated with the process_id."""
        if process_id in self.processes:
            self.processes[process_id].interrupt()
            return True
        return False

    def get_process_status(self, process_id):
        """Get the status of the process associated with the process_id."""
        if process_id in self.processes:
            return {
                "running": self.processes[process_id].is_running(),
                "output": self.processes[process_id].get_output(),
            }
        return None


# CommandExecutor: Handles the execution and interaction with a shell command.


class CommandExecutor:
    def __init__(self, command, timeout=None):
        self.command = command
        self.timeout = timeout
        self.process = None  # pexpect.spawn instance.
        self.output = ""  # Store the output of the command.

    def execute(self):
        """Execute the command with optional timeout using pexpect."""
        self.process = pexpect.spawn(self.command, timeout=self.timeout)
        self._capture_output()

    def _capture_output(self):
        """Read the output of the command and store it."""

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
        """Send an interrupt signal (Ctrl+C) to the running process."""
        if self.process is not None:
            self.process.sendcontrol("c")
            self.process.terminate(force=True)

    def is_running(self):
        """Check if the process is still running."""
        return self.process is not None and self.process.isalive()

    def get_output(self):
        """Retrieve the output of the command."""
        if self.process is not None:
            return self.process.before.decode("utf-8")
        return ""


# CommandController: Interface for managing commands.


class CommandController:
    def __init__(self, process_manager):
        self.process_manager = process_manager

    def start_command(self, command, timeout=None):
        """Start a new command and return a process_id."""
        return self.process_manager.create_process(command, timeout)

    def stop_command(self, process_id):
        """Stop the command associated with the given process_id."""
        return self.process_manager.terminate_process(process_id)

    def get_status(self, process_id):
        """Return the status of the command associated with the process_id."""
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
    if stop_request.process_id:
        success = command_controller.stop_command(stop_request.process_id)
        return {"stopped": success}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing process_id"
        )


@app.get("/commands/status")
async def get_status(process_id: str):
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


# The CommandAPI class and setup_routes method are no longer needed
# since FastAPI handles route setup directly with decorators

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=5000)
