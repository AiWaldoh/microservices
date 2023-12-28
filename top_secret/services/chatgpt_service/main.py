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
    """
    Sends a log message to a predefined logging service.

    Args:
        message (str): The message to be logged.

    Returns:
        The response from the logging service as JSON, or None if an error occurs.
    """
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
    Pydantic model for handling completion requests.
    """

    prompt: str
    model: str = "gpt-3.5-turbo"
    custom_url: str = None


app = FastAPI()
send_log("ChatGPT service starting up")


@app.post("/completion")
async def generic_chatgpt_endpoint(request_data: CompletionRequest, request: Request):
    """
    Endpoint for processing generic ChatGPT completion requests.

    Args:
        request_data (CompletionRequest): The completion request data.
        request (Request): The request object.

    Returns:
        A JSON response containing the completion result.

    Raises:
        HTTPException: If the API key is missing or an unexpected error occurs.
    """
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
async def websocket_chatgpt_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming ChatGPT responses.

    Args:
        websocket (WebSocket): The WebSocket connection object.

    Raises:
        WebSocketDisconnect: If the WebSocket connection is closed unexpectedly.
    """
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
    """
    Pydantic model for handling messages.
    """

    role: str
    content: str


class MessageHistory:
    """
    Class for storing and retrieving message history.
    """

    def __init__(self):
        """
        Initializes a new instance of MessageHistory.
        """
        self.messages = []

    def add_message(self, role: str, content: str):
        """
        Adds a message to the history.

        Args:
            role (str): The role of the message sender.
            content (str): The message content.
        """
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> List[dict]:
        """
        Retrieves all messages from the history.

        Returns:
            List[dict]: A list of message dictionaries.
        """
        return self.messages


@app.post("/json")
async def json_chatgpt_endpoint(messages: List[Message]):
    """
    Endpoint for processing ChatGPT completion requests with JSON input.

    Args:
        messages (List[Message]): A list of message objects.

    Returns:
        A JSON response containing the completion result.

    Raises:
        HTTPException: If an unexpected error occurs.
    """
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
    """
    Pydantic model for handling function input.
    """

    role: str
    content: str


class FunctionData(BaseModel):
    """
    Pydantic model for handling function data.
    """

    input_data: FunctionInput
    functions: list


@app.post("/function")
async def function_chatgpt_endpoint(data: FunctionData):
    """
    Endpoint for processing ChatGPT completion requests with additional functions.

    Args:
        data (FunctionData): The function data for the request.

    Returns:
        A JSON response containing the completion result.

    Raises:
        HTTPException: If an unexpected error occurs.
    """
    async_wrapper = OpenAIWrapperFunction()

    completion = await async_wrapper.create_completion(
        model="gpt-3.5-turbo",
        messages=[data.input_data.dict()],
        functions=data.functions,
    )

    completion_json = async_wrapper.model_dump_json(completion)

    return json.loads(completion_json)
