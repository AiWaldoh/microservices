import httpx
import logging
from fastapi import HTTPException, status
from openai import (
    AsyncOpenAI,
    APIConnectionError,
    RateLimitError,
    APIStatusError,
)


def send_log(message: str):
    url = "http://localhost:8000/log"
    data = {"message": message}
    try:
        with httpx.Client() as client:
            response = client.post(url, json=data)
            return response.json()
    except httpx.RequestError as e:
        print(f"An error occurred: {e}")


# Define the wrapper class for OpenAI SDK
class OpenAIWrapper:
    """
    A wrapper class for the OpenAI SDK.

    This class simplifies interactions with the OpenAI API using the provided SDK.

    Attributes:
    - client (AsyncOpenAI): An instance of the AsyncOpenAI client for API interactions.
    """

    def __init__(self, api_key: str, base_url: str = None):
        http_client = httpx.AsyncClient()
        if base_url:
            http_client.base_url = base_url
        self.client = AsyncOpenAI(
            api_key=api_key,
            max_retries=2,
            timeout=httpx.Timeout(10.0, read=5.0, write=10.0, connect=2.0),
            http_client=http_client,
        )

    async def get_completion(self, prompt: str, model: str = "gpt-3.5-turbo"):
        try:
            response = await self.client.chat.completions.with_raw_response.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            # Log all headers
            for header, value in response.headers.items():
                logging.debug(f"{header}: {value}")

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
