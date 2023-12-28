import paramiko
import sys
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class SSHCredentials(BaseModel):
    hostname: str
    username: str
    key_filename: str


class SSHCommand(BaseModel):
    command: str


class SSHClient:
    def __init__(self, hostname, username, key_filename):
        self.hostname = hostname
        self.username = username
        self.key_filename = key_filename
        self.client = None
        self.shell = None

    def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                self.hostname, username=self.username, key_filename=self.key_filename
            )
            self.shell = self.client.invoke_shell()
            self._discard_initial_prompt()
        except Exception as e:
            print(f"Failed to connect to {self.hostname}: {e}")
            sys.exit(1)

    def _discard_initial_prompt(self):
        output = ""
        while not self.shell.recv_ready():
            time.sleep(0.1)
        while self.shell.recv_ready():
            data = self.shell.recv(1024)
            output += data.decode("utf-8")

    def execute_command(self, command):
        if self.shell:
            output = ""
            self.shell.send(command + "\n")
            while not self.shell.recv_ready():
                time.sleep(0.1)
            while self.shell.recv_ready():
                data = self.shell.recv(1024)
                output += data.decode("utf-8")
            return output.strip()
        else:
            print("Connection not established.")

    def close(self):
        if self.client:
            self.client.close()


ssh_client = None


@app.post("/connect")
async def connect(credentials: SSHCredentials):
    global ssh_client
    if ssh_client is None:
        ssh_client = SSHClient(
            credentials.hostname, credentials.username, credentials.key_filename
        )
        ssh_client.connect()
        return {"status": "connected"}
    else:
        raise HTTPException(
            status_code=400, detail="SSH connection already established"
        )


@app.post("/execute-command")
async def execute_command(command: SSHCommand):
    global ssh_client
    if ssh_client is not None:
        output = ssh_client.execute_command(command.command)
        if command.command.strip() == "exit":
            ssh_client.close()
            ssh_client = None
        return {"output": output}
    else:
        raise HTTPException(status_code=400, detail="SSH connection not established")
