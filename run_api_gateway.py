import requests
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# URL of the FastAPI gateway
GATEWAY_URL = "http://localhost:8004"


def execute_command(verbal_command):
    """Send a verbal command to the FastAPI gateway."""
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(
            f"{GATEWAY_URL}/execute_command/",
            json={"verbal_command": verbal_command},
            headers=headers,
        )
        response.raise_for_status()  # This will raise an exception for HTTP errors
        result = response.json()
        logger.debug("Response from Gateway: %s", result)
        return result
    except requests.RequestException as e:
        logger.error("An error occurred: %s", e)
        return None


def main():
    verbal_command = "create a folder called fdsfdsfds"
    result = execute_command(verbal_command)
    if result:
        print("Response from Gateway:", result)


if __name__ == "__main__":
    main()
