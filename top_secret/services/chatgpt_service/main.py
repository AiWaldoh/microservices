import os
from typing import List
import httpx
from fastapi import FastAPI, HTTPException, Request, status, WebSocket
from libraries.openai_wrapper_simple import (
    OpenAIWrapper,
)
from libraries.openai_wrapper_stream import (
    OpenAIWrapperStream,
)
from libraries.openai_wrapper_json import (
    OpenAIWrapperJson,
)
from libraries.openai_wrapper_function import (
    OpenAIWrapperFunction,
)

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
            # deepcode ignore single~iteration~loop: no reason
            message_json = await websocket.receive_text()
            messages = json.loads(message_json)

            async for text in wrapper.create_chat_completion_stream(messages):
                await websocket.send_text(text)

            await websocket.close()
            break

    except Exception as e:
        print(f"An error occurred: {e}")
        await websocket.close(code=1011)


class Message(BaseModel):
    role: str
    content: str


class MessageHistory:
    def __init__(self):
        self.messages = []

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> List[dict]:
        return self.messages


@app.post("/json/")
async def chat_endpoint(messages: List[Message]):
    message_history = MessageHistory()
    for message in messages:
        message_history.add_message(message.role, message.content)

    wrapper = OpenAIWrapperJson()
    try:
        completion = await wrapper.create_completion(
            model="gpt-3.5-turbo-1106", messages=message_history.get_messages()
        )
        return wrapper.model_dump_json(completion)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FunctionInput(BaseModel):
    role: str
    content: str


class FunctionData(BaseModel):
    input_data: FunctionInput
    functions: list


@app.post("/function")
async def function_endpoint(data: FunctionData):
    async_wrapper = OpenAIWrapperFunction()

    completion = await async_wrapper.create_completion(
        model="gpt-3.5-turbo",
        messages=[data.input_data.dict()],
        functions=data.functions,
    )

    completion_json = async_wrapper.model_dump_json(completion)

    # You can handle the result type (command or question) elsewhere based on the
    # completion result.
    # For example, you can use the completion_json to determine the result type and
    # take appropriate actions.

    return json.loads(completion_json)
