import requests


# The URL where the FastAPI server is running
url = "http://localhost:5005/completion"

# The data to send in the POST request
data = {"prompt": "Tell me a joke", "streaming": False, "model": "gpt-3.5-turbo"}

# Send the POST request
response = requests.post(url, json=data)

# Check if the request was successful
if response.status_code == 200:
    print("Response from OpenAI:", response.json())
else:
    print("Error:", response.status_code, response.text)
