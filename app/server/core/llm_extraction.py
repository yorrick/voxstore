import asyncio
import logging
import os

import instructor
from litellm import completion

from .models import VoiceSearchExtraction

logger = logging.getLogger(__name__)

EXTRACTION_MODELS = [
    "openrouter/google/gemini-2.5-flash",
    "openrouter/anthropic/claude-haiku-4.5",
]

SYSTEM_PROMPT = """\
You are a voice search assistant for VoxStore, an online product catalog.
Extract structured search parameters from the user's voice transcript.

Available categories: Electronics, Clothing, Home, Books, Sports
Available sort options: price_asc, price_desc, rating
Rating filter: a minimum star rating (1.0-5.0), e.g. "4 stars" → 4.0

Rules:
- query: the core product search terms (e.g. "wireless headphones", "books")
- min_rating: only set if the user explicitly mentions a rating threshold
- sort: only set if the user mentions price ordering or "top rated"/"best rated"
- category: only set if the user mentions a specific category
- If the transcript is just a product name with no filters, return only the query
- Keep the query concise — extract just the product search terms\
"""


class LLMExtractionError(Exception):
    """Raised when LLM extraction fails."""


_client: instructor.Instructor | None = None


def _get_client() -> instructor.Instructor:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise LLMExtractionError("OPENROUTER_API_KEY not set")
        _client = instructor.from_litellm(completion)
    return _client


async def extract_voice_search(
    transcript: str,
) -> VoiceSearchExtraction:
    """Extract structured search parameters from a voice transcript.

    Uses Gemini 2.5 Flash via OpenRouter/LiteLLM with instructor
    for structured Pydantic output.

    Args:
        transcript: The raw voice transcript text.

    Returns:
        VoiceSearchExtraction with query, optional filters and sort.

    Raises:
        LLMExtractionError: If all LLM models fail.
    """
    client = _get_client()
    last_error: Exception | None = None

    for model_name in EXTRACTION_MODELS:
        try:
            logger.info("[EXTRACT] Trying model %s", model_name)

            def make_completion(
                current_model: str = model_name,
            ) -> VoiceSearchExtraction:
                return client.completions.create(  # type: ignore[return-value]
                    model=current_model,
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": transcript,
                        },
                    ],
                    response_model=VoiceSearchExtraction,
                    temperature=0.1,
                    max_retries=2,
                    timeout=10.0,
                )

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, make_completion)

            logger.info(
                "[EXTRACT] Success with %s: %s",
                model_name,
                result,
            )
            return result

        except Exception as e:
            logger.warning(
                "[EXTRACT] Model %s failed: %s",
                model_name,
                str(e)[:200],
            )
            last_error = e
            continue

    raise LLMExtractionError(f"All extraction models failed: {last_error}")
