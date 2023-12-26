from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

app = Flask(__name__)

# Initialize the AsyncOpenAI client
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


async def get_linux_command(verbose_command: str) -> str:
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": verbose_command}],
        stream=False,  # Assuming we don't need streaming for this endpoint
    )
    linux_command = response.choices[0].message.content
    return linux_command


@app.route("/convert-command", methods=["POST"])
async def convert_command():
    """
    API endpoint that takes a verbose command in natural language as input
    and returns the equivalent Linux CLI command.
    """
    # Extract the verbose command from the POST request's JSON body
    data = request.get_json()
    verbose_command = data.get("verbose_command")

    # Get the Linux CLI command using the OpenAI API
    linux_command = await get_linux_command(verbose_command)

    # Return the Linux CLI command in JSON format
    return jsonify({"command": linux_command})


if __name__ == "__main__":
    # Run the Flask app with the ASGI server Hypercorn to support async
    app.run(debug=True, host="0.0.0.0", port=5005, use_reloader=False)
