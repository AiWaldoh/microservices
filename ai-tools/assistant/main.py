import sys
import os
import json
import pyaudio
import struct
import pvporcupine
from vosk import Model, KaldiRecognizer, SetLogLevel
import requests
import time
from tts_client import TTSClient
import threading


class DigitalAssistantState:
    WAKE_WORD_DETECTION = 1
    SPEECH_RECOGNITION = 2
    FOLLOW_UP_LISTENING = 3


class Configuration:
    def __init__(self, model_path, access_key, wake_word):
        self.model_path = model_path
        self.access_key = access_key
        self.wake_word = wake_word


class WakeWordDetector:
    def __init__(self, config):
        self.config = config
        self.porcupine = pvporcupine.create(
            access_key=self.config.access_key,
            keyword_paths=[pvporcupine.KEYWORD_PATHS[self.config.wake_word]],
        )

    def detect_wake_word(self, audio_frame):
        keyword_index = self.porcupine.process(audio_frame)
        return keyword_index >= 0

    def delete(self):
        self.porcupine.delete()


class SpeechRecognizer:
    def __init__(self, config):
        self.config = config
        self._validate_model_path()
        self.model = Model(self.config.model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)

    def _validate_model_path(self):
        if not os.path.exists(self.config.model_path):
            print(
                f"Model path '{self.config.model_path}' does not exist. \
                Please check the path and try again."
            )
            sys.exit(1)

    def recognize_speech(self, data):
        return self.recognizer.AcceptWaveform(data)

    def get_recognized_text(self):
        result = self.recognizer.Result()
        result_json = json.loads(result)
        return result_json.get("text")


class TTSHandler:
    def __init__(self):
        self.tts_client = TTSClient()

    def synthesize_text(self, text):
        return self.tts_client.synthesize_text(text)

    def save_audio(self, audio_data, file_path):
        self.tts_client.save_audio(audio_data, file_path)

    def play_audio(self, file_path):
        self.tts_client.play_audio(file_path)


class APIHandler:
    def send_to_api(self, prompt, model, custom_url=None):
        api_url = "http://localhost:8001/completion"
        payload = {"prompt": prompt, "model": model, "custom_url": "custom_url"}
        response = requests.post(api_url, json=payload)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: API request failed with status code {response.status_code}")
            return None


class AudioStream:
    def __init__(self):
        self.stream = self._setup_audio_stream()

    def _setup_audio_stream(self):
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8192,
        )
        stream.start_stream()
        return stream

    def read(self, num_frames, exception_on_overflow=False):
        return self.stream.read(num_frames, exception_on_overflow=exception_on_overflow)

    def get_read_available(self):
        return self.stream.get_read_available()

    def stop(self):
        self.stream.stop_stream()
        self.stream.close()
        pyaudio.PyAudio().terminate()


class DigitalAssistant:
    def __init__(
        self,
        config,
        wake_word_detector,
        speech_recognizer,
        tts_handler,
        api_handler,
        audio_stream,
    ):
        self.config = config
        self.wake_word_detector = wake_word_detector
        self.speech_recognizer = speech_recognizer
        self.tts_handler = tts_handler
        self.api_handler = api_handler
        self.audio_stream = audio_stream
        self.wake_word_detection_paused = False
        self.state = DigitalAssistantState.WAKE_WORD_DETECTION

    def run(self):
        try:
            while True:
                if self.state == DigitalAssistantState.WAKE_WORD_DETECTION:
                    self.listen_for_wake_word()
                elif self.state == DigitalAssistantState.SPEECH_RECOGNITION:
                    self.state = self.listen_for_instructions()
                elif self.state == DigitalAssistantState.FOLLOW_UP_LISTENING:
                    self.state = self.listen_for_follow_up()

        except KeyboardInterrupt:
            self.stop()
            print("Stopped listening.")

    def process_recognized_command(self, recognized_text):
        print(f"Processing command: {recognized_text}")
        response = self.api_handler.send_to_api(recognized_text, "gpt-3.5-turbo")
        if response and "completion" in response:
            try:
                audio_data = self.tts_handler.synthesize_text(response["completion"])
                file_path = "out/output.wav"
                self.tts_handler.save_audio(audio_data, file_path)
                playback_thread = threading.Thread(
                    target=self.play_audio, args=(file_path,)
                )
                playback_thread.start()
                playback_thread.join()
            except Exception as e:
                print("An error occurred in TTS:", e)

    def listen_for_wake_word(self):
        print(f"Listening for wake word '{self.config.wake_word}'...")
        wake_word_detected = False
        while not wake_word_detected:
            if self.wake_word_detection_paused:
                time.sleep(0.1)  # Sleep for a short duration if paused
                continue

            audio_frame = self.audio_stream.read(
                self.wake_word_detector.porcupine.frame_length,
                exception_on_overflow=False,
            )
            audio_frame = struct.unpack_from(
                "h" * self.wake_word_detector.porcupine.frame_length, audio_frame
            )
            if self.wake_word_detector.detect_wake_word(audio_frame):
                print(f"Wake word '{self.config.wake_word}' detected!")
                wake_word_detected = True
                self.state = DigitalAssistantState.SPEECH_RECOGNITION

    def clear_audio_buffer(self):
        buffer_size = 4096
        while self.audio_stream.get_read_available() > buffer_size:
            self.audio_stream.read(buffer_size, exception_on_overflow=False)

    def listen_for_follow_up(self):
        print("Listening for follow-up command...")
        start_time = time.time()
        follow_up_duration = 10  # 10 seconds for follow-up
        recognized_text = ""

        while time.time() - start_time < follow_up_duration:
            data = self.audio_stream.read(4096, exception_on_overflow=False)
            if self.speech_recognizer.recognize_speech(data):
                text = self.speech_recognizer.get_recognized_text()
                if text:
                    recognized_text += text + " "

        recognized_text = recognized_text.strip()
        if recognized_text:
            self.process_recognized_command(recognized_text)
            return DigitalAssistantState.FOLLOW_UP_LISTENING

        return DigitalAssistantState.WAKE_WORD_DETECTION

    def listen_for_instructions(self):
        print("Listening for instructions...")
        recognized_text = ""
        silence_threshold = 2
        last_speech_time = time.time()
        is_speech_detected = False

        while True:
            data = self.audio_stream.read(4096, exception_on_overflow=False)
            if self.speech_recognizer.recognize_speech(data):
                is_speech_detected = True
                text = self.speech_recognizer.get_recognized_text()
                if text:
                    recognized_text += text + " "
                    last_speech_time = time.time()  # Update the last speech time
            elif (
                is_speech_detected
                and time.time() - last_speech_time > silence_threshold
            ):
                break

        recognized_text = recognized_text.strip()
        if recognized_text:
            self.process_recognized_command(recognized_text)

        return DigitalAssistantState.FOLLOW_UP_LISTENING

    def play_audio(self, file_path):
        self.wake_word_detection_paused = True  # Pause wake word detection
        self.tts_handler.play_audio(file_path)
        self.clear_audio_buffer()  # Clear the audio buffer
        self.wake_word_detection_paused = False  # Resume wake word detection

    def stop(self):
        self.audio_stream.stop()
        self.wake_word_detector.delete()
        self.audio_stream.close()
        pyaudio.PyAudio().terminate()
        self.wake_word_detection_paused = True  # Stop the wake word detection thread


def main():
    SetLogLevel(-1)
    VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH")
    ACCESS_KEY = os.getenv("PICO_ACCESS_KEY")
    WAKE_WORD = "porcupine"

    config = Configuration(VOSK_MODEL_PATH, ACCESS_KEY, WAKE_WORD)
    wake_word_detector = WakeWordDetector(config)
    speech_recognizer = SpeechRecognizer(config)
    tts_handler = TTSHandler()
    api_handler = APIHandler()
    audio_stream = AudioStream()

    digital_assistant = DigitalAssistant(
        config,
        wake_word_detector,
        speech_recognizer,
        tts_handler,
        api_handler,
        audio_stream,
    )

    try:
        digital_assistant.run()
    except KeyboardInterrupt:
        digital_assistant.stop()
        print("Stopped listening.")


if __name__ == "__main__":
    main()
