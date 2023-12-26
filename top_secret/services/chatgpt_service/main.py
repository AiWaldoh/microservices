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
# Set up logging


# Define the request model for FastAPI
class CompletionRequest(BaseModel):
    prompt: str
    streaming: bool = False
    model: str = "gpt-3.5-turbo"
    custom_url: str = None


# Define the wrapper class for OpenAI SDK
class OpenAIWrapper:
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

    async def get_completion(
        self, prompt: str, model: str = "gpt-3.5-turbo", streaming: bool = False
    ):
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
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The server could not be reached",
            ) from e
        except RateLimitError as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="A 429 status code was received; we should back off a bit.",
            ) from e
        except APIStatusError as e:
            raise HTTPException(
                status_code=e.status_code,
                detail=f"Non-200-range status code received: {e.status_code}",
            ) from e
        except APITimeoutError as e:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="The request timed out.",
            ) from e


# Initialize FastAPI application
app = FastAPI()


# Define the endpoint for getting completions
@app.post("/completion")
async def completion(request_data: CompletionRequest, request: Request):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
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


# # Run the application using Uvicorn
# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(app, host="0.0.0.0", port=5005)
