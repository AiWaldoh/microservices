from flask import Flask, request, jsonify
import threading
import os

app = Flask(__name__)
log_file_path = "service.log"

# Ensure thread-safe file writing
log_file_lock = threading.Lock()

# LogStorage: Handles the storage of log messages.
class LogStorage:
    def store(self, message):
        """Store the log message in a file."""
        with log_file_lock:
            with open(log_file_path, "a") as log_file:
                log_file.write(message + "\n")

# LogController: Interface for handling log messages.
class LogController:
    def __init__(self, log_storage):
        self.log_storage = log_storage

    def log_message(self, message):
        """Receive a log message and store it."""
        self.log_storage.store(message)
        return True

# LogAPI: Flask route for the Logging Microservice.
class LogAPI:
    def __init__(self, log_controller):
        self.log_controller = log_controller

    def setup_routes(self):
        """Setup Flask route for the Logging Microservice."""
        @app.route('/log', methods=['POST'])
        def log_message():
            data = request.json
            message = data.get('message')
            if message:
                self.log_controller.log_message(message)
                return jsonify({'status': 'success'}), 200
            else:
                return jsonify({'error': 'Missing log message'}), 400

log_storage = LogStorage()
log_controller = LogController(log_storage)
log_api = LogAPI(log_controller)
log_api.setup_routes()

if __name__ == "__main__":
    # Ensure the log file exists
    if not os.path.exists(log_file_path):
        open(log_file_path, 'a').close()
    
    app.run(debug=True, host='0.0.0.0', port=5001)
