import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()


class OpenAIWrapperFunction:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def create_completion(self, model, messages, functions=None, **kwargs):
        return await self.client.chat.completions.create(
            model=model, messages=messages, functions=functions, **kwargs
        )

    def model_dump_json(self, response, indent=2):
        return response.model_dump_json(indent=indent)
