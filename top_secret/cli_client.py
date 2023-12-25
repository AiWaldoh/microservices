from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import confirm
import requests
import json
import time
# Configuration for the microservices endpoints
COMMAND_SERVICE_URL = "http://localhost:5000"
LOGGING_SERVICE_URL = "http://localhost:5001"

# ClientCommandExecutor: Sends requests to the Command Execution Service.
class ClientCommandExecutor:
    def __init__(self, service_url):
        self.service_url = service_url

    def start(self, command):
        """Send a request to start a command."""
        response = requests.post(f"{self.service_url}/commands/start", json={"command": command})
        return response.json()

    def stop(self, process_id):
        """Send a request to stop a command using its process_id."""
        response = requests.post(f"{self.service_url}/commands/stop", json={"process_id": process_id})
        return response.json()

    def status(self, process_id):
        """Send a request to get the status of a command using its process_id."""
        try:
            response = requests.get(f"{self.service_url}/commands/status", params={"process_id": process_id})
            response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
            json_response = response.json()
            print(f"Status response: {json_response}")  # Debug print to show the status response
            return json_response
        except requests.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}. Response: {response.text}")
        except Exception as err:
            print(f"An error occurred: {err}")
        return None

# LogClient: Sends log messages to the Logging Microservice.
class LogClient:
    def __init__(self, service_url):
        self.service_url = service_url

    def log(self, message):
        """Send a log message to the Logging Microservice."""
        response = requests.post(f"{self.service_url}/log", json={"message": message})
        return response.json()

# CLIInterface: Handles user interaction in the command line.
class CLIInterface:
    def __init__(self, command_executor, log_client):
        self.session = PromptSession()
        self.command_executor = command_executor
        self.log_client = log_client

    def start(self):
        """Start the CLI interface to interact with the user."""
        while True:
            try:
                # Main command prompt
                user_input = self.session.prompt('cli> ')
                if user_input.strip().lower() == 'exit':
                    break

                # Handle start command
                if user_input.startswith('start '):
                    command = user_input[len('start '):].strip()
                    response = self.command_executor.start(command)
                    process_id = response.get('process_id')
                    print(f"Command started with process_id: {process_id}")

                    # Poll for the command's status and output until it's no longer running
                    while True:
                        status_response = self.command_executor.status(process_id)
                        if status_response is None:
                            print("Failed to retrieve command status.")
                            break
                        if status_response.get('running', False):
                            time.sleep(1)
                            continue
                        elif 'output' in status_response:
                            # Display the final output
                            print(status_response['output'])
                            break
                        else:
                            print("Unexpected response format.")
                            break

                    # Attempt to log the command execution
                    try:
                        log_response = self.log_client.log(f"Command executed: {command} (process_id: {process_id})")
                        if log_response is None or log_response.get('status') != 'success':
                            print("Failed to log command execution.")
                    except Exception as e:
                        print(f"An error occurred while logging: {e}")
                   
                # ... (handle other commands like 'stop' and 'status')

            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully
                if confirm('Are you sure you want to exit?'):
                    break

            except Exception as e:
                print(f"An error occurred: {e}")

# Main function to run the CLI client.
def main():
    command_executor = ClientCommandExecutor(COMMAND_SERVICE_URL)
    log_client = LogClient(LOGGING_SERVICE_URL)
    cli_interface = CLIInterface(command_executor, log_client)
    cli_interface.start()

if __name__ == "__main__":
    main()
