from flask import Flask, request, jsonify
import openai
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Replace 'your_openai_api_key' with your actual OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/convert-command', methods=['POST'])
def convert_command():
    """
    API endpoint that takes a verbose command in natural language as input
    and returns the equivalent Linux CLI command.
    """
    # Extract the verbose command from the POST request's JSON body
    data = request.get_json()
    verbose_command = data.get('verbose_command')

    # Placeholder for the actual implementation that calls OpenAI's API
    # and converts the verbose command to a Linux CLI command.
    # The implementation should use the OpenAI Python SDK to send the prompt
    # to the GPT model and process the response to extract the Linux command.
    # For example:
    # response = openai.Completion.create(
    #     engine="davinci",
    #     prompt=f"Convert the following verbose command to a Linux CLI command: '{verbose_command}'",
    #     max_tokens=50
    # )
    # linux_command = process_response(response)

    # For now, we'll return a placeholder response
    linux_command = "ls"  # This should be replaced with the actual command from the GPT response

    # Return the Linux CLI command in JSON format
    return jsonify({"command": linux_command})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)
