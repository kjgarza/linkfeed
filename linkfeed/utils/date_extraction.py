"""LLM-based date extraction from plain text."""

import logging
from datetime import datetime
from typing import Optional

from dateutil import parser as date_parser
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
MAX_CONTENT_LENGTH = 1000

DATE_PROMPT = """Extract the publication date from this article text if present.

Look for:
- Explicit dates like "December 28, 2024" or "2024-12-28"
- Relative references like "Published yesterday" (today is {today})
- Bylines with dates like "By John Doe on March 15, 2024"

If you find a date, return it in ISO format: YYYY-MM-DD
If no publication date is found, return: NONE

Text:
{content}

Publication date:"""


async def extract_date_with_llm(
    plain_text: list[str] | list[dict],
    client: AsyncOpenAI,
    model: str = DEFAULT_MODEL,
) -> Optional[datetime]:
    """Extract publication date from plain text using LLM.

    Args:
        plain_text: List of text paragraphs or dicts with 'text' key from the article
        client: AsyncOpenAI client instance
        model: OpenAI model to use

    Returns:
        Parsed datetime or None if no date found
    """
    if not client:
        return None
    
    if not plain_text:
        return None

    # Handle both list of strings and list of dicts (from readabilipy)
    text_paragraphs = []
    for item in plain_text:
        if isinstance(item, dict):
            text_paragraphs.append(item.get('text', ''))
        elif isinstance(item, str):
            text_paragraphs.append(item)
    
    # Join first paragraphs where dates typically appear
    content = " ".join(text_paragraphs[:5]) if len(text_paragraphs) > 5 else " ".join(text_paragraphs)
    
    if not content or not content.strip():
        return None

    # Truncate content to save tokens
    truncated = content[:MAX_CONTENT_LENGTH]
    if len(content) > MAX_CONTENT_LENGTH:
        truncated += "..."

    today = datetime.now().strftime("%Y-%m-%d")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": DATE_PROMPT.format(content=truncated, today=today),
                }
            ],
            max_tokens=200,
            temperature=0,
        )

        raw_response = response.choices[0].message.content or ""
        date_str = raw_response.strip()

        if date_str.upper() == "NONE" or not date_str:
            logger.debug("LLM found no publication date in text")
            return None

        # Parse the date string
        parsed_date = date_parser.parse(date_str)
        logger.debug(f"LLM extracted date: {parsed_date}")
        return parsed_date

    except Exception as e:
        logger.warning(f"Failed to extract date with LLM: {e}")
        return None
