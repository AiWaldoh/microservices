from typing import List, Optional
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()


class OpenAIWrapperJson:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def create_completion(
        self,
        model: str,
        messages: List[dict],
        functions: Optional[dict] = None,
        **kwargs,
    ):
        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            functions=functions,
            **kwargs,
        )

    def model_dump_json(self, response, indent: int = 2):
        return response.model_dump_json(indent=indent)
