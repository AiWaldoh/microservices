from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# URLs for the microservices
CONVERT_COMMAND_SERVICE_URL = "http://127.0.0.1:5005/convert-command"
COMMAND_SERVICE_URL = "http://127.0.0.1:5000/commands/start"


@app.route("/orchestrate-command", methods=["POST"])
def orchestrate_command():
    data = request.get_json()
    verbose_command = data.get("verbose_command")

    try:
        # Log the URL being called
        app.logger.info(
            f"Calling convert_command service at {CONVERT_COMMAND_SERVICE_URL}"
        )

        # Step 1: Call the convert_command service to get the CLI command
        convert_response = requests.post(
            CONVERT_COMMAND_SERVICE_URL, json={"verbose_command": verbose_command}
        )
        convert_response.raise_for_status()

        cli_command = convert_response.json().get("command")

        # Log the URL being called
        app.logger.info(f"Calling command_service at {COMMAND_SERVICE_URL}")

        # Step 2: Call the command_service to execute the CLI command
        command_response = requests.post(
            COMMAND_SERVICE_URL, json={"command": cli_command}
        )
        command_response.raise_for_status()

        return jsonify(command_response.json())
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Request failed: {e}")
        return jsonify({"error": "Failed to orchestrate command"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5002)
