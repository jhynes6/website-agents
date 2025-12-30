from typing import AsyncGenerator, Dict, List, Tuple
import json

from fastapi import HTTPException
from openai import AsyncOpenAI

from ..config import get_settings
from ..logging import logger


CATEGORIZATION_SYSTEM_PROMPT = """
Your task is to categorize website URLs based on the type of content likely found on each page.

Begin with a concise checklist (3-7 bullets) of what you will do; keep items conceptual, not implementation-level.

## Category Definitions

- **homepage**: The company's main or landing page.

- **services_products**: Pages describing specific services or products the company offers for sale.

- **industry_markets**: Pages detailing the industries or markets served by the company.

- **pricing**: Pages providing information about the cost or pricing of products or services.

- **case_studies**: Pages containing case studies or detailed success stories.

- **testimonials**: Pages devoted exclusively to customer testimonials.

- **blogs_resources**: Pages featuring blogs, resources, guides, or other thought leadership materials.

- **about**: Pages with background or general information about the company.

- **careers**: Pages related to employment, job openings, or hiring.

- **other**: Use this for URLs that cannot be confidently categorized using the options above.

## Categorization Rules

- Assign each URL to only one category from the list above.

- If a URL could fit into multiple categories, select the most specific and relevant category.

- If the input is invalid, empty, or not a well-formed URL, categorize it as "other".

- Set reasoning_effort = minimal; ensure decisions are efficient and only escalate if ambiguous cases arise.

## Input Handling

- Input is a list of URLs. If a single URL is provided, respond with a list containing one item.

- Maintain the original order of URLs in your output.

- Each category value must exactly match one of the defined category names listed above (spelling and case sensitive).

## Output Format

Return ONLY the category name as a single word from the list above. Do not return JSON, explanations, or any other text.

Example outputs: "homepage", "services_products", "blogs_resources", "other"
"""

VALID_CATEGORIES = [
    'homepage', 'services_products', 'industry_markets', 'pricing', 
    'case_studies', 'testimonials', 'blogs_resources', 'about', 'careers', 'other'
]


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

    async def categorize_url(self, url: str) -> str:
        """Categorize a single URL using LLM"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": CATEGORIZATION_SYSTEM_PROMPT},
                    {"role": "user", "content": f"categorize the url: {url}"}
                ],
                temperature=0.1,  # Lower temperature for more consistent categorization
                max_tokens=50,
                top_p=1
            )
            
            category = response.choices[0].message.content.strip()
            
            # Try to parse as JSON first (in case LLM returns JSON despite instructions)
            try:
                parsed = json.loads(category)
                if isinstance(parsed, dict):
                    # Handle {"categories": ["blogs_resources"]} format
                    if 'categories' in parsed and isinstance(parsed['categories'], list) and len(parsed['categories']) > 0:
                        category = parsed['categories'][0]
                    # Handle {"category": "blogs_resources"} format
                    elif 'category' in parsed:
                        category = parsed['category']
            except (json.JSONDecodeError, KeyError, IndexError):
                # Not JSON, use as-is
                pass
            
            category = category.strip().lower()
            
            if category not in VALID_CATEGORIES:
                logger.warning(f"⚠️  Invalid category '{category}' for {url}, defaulting to 'other'")
                category = 'other'
                
            return category
            
        except Exception as e:
            logger.error(f"❌ Error categorizing {url}: {e}")
            return 'other'

    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 1000,
        model: str = "gpt-4o-mini"
    ) -> Dict:
        """Generic chat completion method"""
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return {
            "choices": [{
                "message": {
                    "content": response.choices[0].message.content
                }
            }]
        }


llm_client = LLMClient()
