from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
import requests
import io
from pydub import AudioSegment
from pydantic import BaseModel

app = FastAPI()


class TTSClient:
    def __init__(self, server_url="http://localhost:5002/api/tts"):
        self.server_url = server_url

    def synthesize_text(self, text, speaker_id="p273", style_wav="", language_id=""):
        params = {
            "text": text,
            "speaker_id": speaker_id,
            "style_wav": style_wav,
            "language_id": language_id,
        }
        response = requests.get(self.server_url, params=params)
        if response.status_code == 200:
            return response.content
        else:
            raise Exception("Error with TTS request: " + response.text)

    @staticmethod
    def convert_audio(audio_data):
        audio = AudioSegment.from_file(io.BytesIO(audio_data), format="wav")
        buffer = io.BytesIO()
        audio.export(buffer, format="wav")
        buffer.seek(0)
        return buffer


class SynthesizeRequest(BaseModel):
    text: str
    speaker_id: str = "p273"
    style_wav: str = ""
    language_id: str = ""


@app.get("/synthesize/")
async def synthesize(request: SynthesizeRequest = Depends()):
    tts_client = TTSClient()
    try:
        audio_data = tts_client.synthesize_text(
            request.text, request.speaker_id, request.style_wav, request.language_id
        )
        audio_buffer = TTSClient.convert_audio(audio_data)
        return StreamingResponse(audio_buffer, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
