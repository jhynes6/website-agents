from typing import AsyncGenerator, Dict, List

from fastapi import HTTPException
from openai import AsyncOpenAI

from ..config import get_settings


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.openai_api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY is required for the Python backend")
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    async def stream_answer(
        self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta


llm_client = LLMClient()

