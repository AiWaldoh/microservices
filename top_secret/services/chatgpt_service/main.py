import os
import httpx
from fastapi import FastAPI, HTTPException, Request, status, WebSocket
from libraries.openai_wrapper import OpenAIWrapper
from libraries.openai_wrapper_stream import OpenAIWrapperStream
from pydantic import BaseModel
from dotenv import load_dotenv
import json

load_dotenv()


def send_log(message: str):
    url = "http://localhost:8000/log"
    data = {"message": message}
    try:
        with httpx.Client() as client:
            response = client.post(url, json=data)
            return response.json()
    except httpx.RequestError as e:
        print(f"An error occurred: {e}")


class CompletionRequest(BaseModel):
    """
    Request model for generating text completions.

    Attributes:
    - prompt (str): The input text prompt for the GPT model.
    - streaming (bool): If set to True, enables streaming of responses.
    Defaults to False.
    - model (str): Specifies the GPT model version to use. Defaults to 'gpt-3.5-turbo'.
    - custom_url (str, optional): Custom URL for the OpenAI API, if different
    from the default.
    """

    prompt: str
    model: str = "gpt-3.5-turbo"
    custom_url: str = None


app = FastAPI()
send_log("ChatGPT service starting up")


@app.post("/completion")
async def completion(request_data: CompletionRequest, request: Request):
    send_log(f"Received completion request: {request_data}")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        send_log("API key is missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key is missing"
        )

    openai_wrapper = OpenAIWrapper(api_key=api_key, base_url=request_data.custom_url)

    try:
        completion = await openai_wrapper.get_completion(
            request_data.prompt, request_data.model
        )
        return {"completion": completion.choices[0].message.content}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred" + str(e),
        )


@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    wrapper = OpenAIWrapperStream()
    await websocket.accept()
    try:
        while True:
            # file deepcode ignore single~iteration~loop: <please specify a reason of
            # ignoring this>
            message_json = await websocket.receive_text()
            messages = json.loads(message_json)

            # Assuming create_chat_completion_stream yields messages until completion
            async for text in wrapper.create_chat_completion_stream(messages):
                await websocket.send_text(text)

            # If create_chat_completion_stream has completed sending all messages,
            # you can close the WebSocket connection here.
            await websocket.close()
            break  # Exit the while loop after closing the connection

    except Exception as e:
        # Handle any other exceptions that may occur
        print(f"An error occurred: {e}")
        await websocket.close(
            code=1011
        )  # Close the connection with an unexpected error code
