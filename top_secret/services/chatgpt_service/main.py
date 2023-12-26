import os
import httpx
import logging
from fastapi import FastAPI, HTTPException, Request, status
from openai import (
    AsyncOpenAI,
    APIConnectionError,
    RateLimitError,
    APIStatusError,
    APITimeoutError,
)
from pydantic import BaseModel
from dotenv import load_dotenv

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
    streaming: bool = False
    model: str = "gpt-3.5-turbo"
    custom_url: str = None


# Define the wrapper class for OpenAI SDK
class OpenAIWrapper:
    """
    A wrapper class for the OpenAI SDK.

    This class simplifies interactions with the OpenAI API using the provided SDK.

    Attributes:
    - client (AsyncOpenAI): An instance of the AsyncOpenAI client for API interactions.
    """

    def __init__(self, api_key: str, base_url: str = None):
        """
        Initializes the OpenAIWrapper with the provided API key and optional base URL.

        Args:
        - api_key (str): The API key for authenticating with the OpenAI service.
        - base_url (str, optional): The base URL for the OpenAI API. Defaults to None.
        """
        http_client = httpx.AsyncClient()
        if base_url:
            http_client.base_url = base_url
        self.client = AsyncOpenAI(
            api_key=api_key,
            max_retries=2,
            timeout=httpx.Timeout(10.0, read=5.0, write=10.0, connect=2.0),
            http_client=http_client,
        )

    async def get_completion(
        self, prompt: str, model: str = "gpt-3.5-turbo", streaming: bool = False
    ):
        """
        Asynchronously gets a text completion from the OpenAI API.

        This method sends a request to the OpenAI API and retrieves a text completion
        based on the provided prompt.

        Args:
        - prompt (str): The input text prompt for the GPT model.
        - model (str): The GPT model version to use. Defaults to 'gpt-3.5-turbo'.
        - streaming (bool): If set to True, enables streaming of responses. Defaults to
        False.

        Returns:
        - Response: The response from the OpenAI API. This is either a streaming
        response or a single completion.

        Raises:
        - HTTPException: Various HTTP exceptions based on the error encountered (503,
        429, specific API status errors, 504).
        """

        try:
            response = await self.client.chat.completions.with_raw_response.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=streaming,
            )
            # Log all headers
            for header, value in response.headers.items():
                logging.debug(f"{header}: {value}")

            if streaming:
                return response
            else:
                completion = response.parse()
                return completion
        except APIConnectionError as e:
            send_log(f"APIConnectionError: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The server could not be reached",
            ) from e
        except RateLimitError as e:
            send_log(f"RateLimitError: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="A 429 status code was received; we should back off a bit.",
            ) from e
        except APIStatusError as e:
            send_log(f"APIStatusError: {str(e)}")
            raise HTTPException(
                status_code=e.status_code,
                detail=f"Non-200-range status code received: {e.status_code}",
            ) from e
        except APITimeoutError as e:
            send_log(f"APITimeoutError: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="The request timed out.",
            ) from e


# Initialize FastAPI application
app = FastAPI()
send_log("ChatGPT service starting up")


# Define the endpoint for getting completions
@app.post("/completion")
async def completion(request_data: CompletionRequest, request: Request):
    """
    Generate text completions using the specified GPT model.

    This endpoint interfaces with the OpenAI API to provide text completions based on
    the given prompt and model.

    Args:
    - request_data (CompletionRequest): The request payload containing the prompt,
    model, and other parameters.
    - request (Request): The request context.

    Returns:
    - dict: A dictionary containing the 'stream' of responses if streaming is enabled,
    or the 'completion' text.

    Raises:
    - HTTPException: 401 Unauthorized if the OpenAI API key is missing.
    - HTTPException: 503 Service Unavailable if the server could not be reached.
    - HTTPException: 429 Too Many Requests if a rate limit error occurs.
    - HTTPException: 504 Gateway Timeout if the request times out.
    - HTTPException: 500 Internal Server Error for any other unexpected errors.
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
        if request_data.streaming:
            stream = await openai_wrapper.get_completion(
                request_data.prompt, request_data.model, request_data.streaming
            )
            response = []
            async for chunk in stream:
                response.append(chunk.choices[0].delta.content or "")
            return {"stream": response}
        else:
            completion = await openai_wrapper.get_completion(
                request_data.prompt, request_data.model, request_data.streaming
            )
            return {"completion": completion.choices[0].message.content}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred" + str(e),
        )
