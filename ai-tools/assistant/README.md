# Digital Assistant

## Description

This Python-based digital assistant integrates wake word detection, speech recognition, text-to-speech (TTS), and API handling. It listens for a specific wake word, recognizes spoken commands, processes them using an external API, and responds with synthesized speech. Note that the startup can be slow due to loading of models and dependencies.

## Getting Started

### Dependencies

- Python 3.10
- Libraries: `sys`, `os`, `json`, `pyaudio`, `struct`, `pvporcupine`, `vosk`, `requests`, `time`, `threading`
- External tools or models for `vosk` and `pvporcupine`

### Installing

- Clone the repository to your local machine.
- Ensure Python 3.10 is installed.
- This project uses Poetry for dependency management. Install Poetry if not already installed.
- Run `poetry install` to install dependencies from `pyproject.toml`.
- Download the Vosk model and place it in a known directory.
- Create a folder named `/out` in the project root to store output `.wav` files, ensuring to specify the path to the Vosk model directory as well.

### Executing program

- Activate the Poetry environment with `poetry shell`.
- Run the program using `python digital_assistant.py`.
- The digital assistant will start and wait for the wake word.
- Once the wake word is detected, it will listen for a command, process it, and respond.
