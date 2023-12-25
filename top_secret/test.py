import requests

# The URL of the API Gateway's orchestration endpoint
API_GATEWAY_URL = "http://127.0.0.1:5002/orchestrate-command"


def test_orchestrate_command(verbose_command):
    # Prepare the payload with the verbose command
    payload = {"verbose_command": verbose_command}

    # Send a POST request to the API Gateway
    response = requests.post(API_GATEWAY_URL, json=payload)

    # Check if the response status code is 200 (OK)
    if response.status_code == 200:
        print("Test passed. Command orchestrated successfully.")
        print("Response:", response.json())
    else:
        print("Test failed. Status code:", response.status_code)
        print("Response:", response.json())


# Example usage of the test function with a sample verbose command
if __name__ == "__main__":
    test_verbose_command = "Please list all files in the current directory."
    test_orchestrate_command(test_verbose_command)
