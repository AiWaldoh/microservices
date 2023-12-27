import os

from openai import AsyncOpenAI
from typing import List, Dict, Union, AsyncGenerator
from dotenv import load_dotenv

load_dotenv()


class OpenAIWrapperStream:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def create_chat_completion_stream(
        self, messages: List[Dict[str, Union[str, int]]], model: str = "gpt-3.5-turbo"
    ) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        all_content = ""
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                all_content += content
                yield all_content
