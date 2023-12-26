import requests

# Configuration for the microservices endpoints
COMMAND_SERVICE_URL = "http://localhost:5000"


# ClientCommandExecutor: Sends requests to the Command Execution Service.
class ClientCommandExecutor:
    def __init__(self, service_url):
        self.service_url = service_url

    def start(self, command):
        """Send a request to start a command."""
        response = requests.post(
            f"{self.service_url}/commands/start", json={"command": command}
        )
        return response.json()

    def status(self, process_id):
        """Send a request to get the status of a command using its process_id."""
        response = requests.get(
            f"{self.service_url}/commands/status", params={"process_id": process_id}
        )
        return response.json()


# Main function to run the simple app.
def main():
    command_executor = ClientCommandExecutor(COMMAND_SERVICE_URL)

    # Start the 'ls' command
    start_response = command_executor.start("ls")
    process_id = start_response.get("process_id")
    print(f"'ls' command started with process_id: {process_id}")

    # Wait for the 'ls' command to complete and get its status
    while True:
        status_response = command_executor.status(process_id)
        if not status_response.get("running", True):
            # Display the final output
            print("Output of 'ls':")
            print(status_response["output"])
            break


if __name__ == "__main__":
    main()
