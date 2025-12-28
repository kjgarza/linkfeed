"""LLM-based tag generation using OpenAI."""

import logging
import re
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
MAX_CONTENT_LENGTH = 2000

TAG_PROMPT = """Extract 3-5 topic tags from this article content. 
Tags should be single lowercase words or dash-separated word pairs that describe the main topics.

Examples:
- An article about "Machine Learning in Healthcare" might have tags: machine-learning, healthcare, medical, ai, data-science
- An article about "Cooking Pasta Recipes" might have tags: cooking, pasta, recipe, italian, 

Output format:
Return only the tags, one per line, no numbering, no bullets, or punctuation.

Content:
{content}

Tags:"""



async def generate_tags(
    content: str,
    client: AsyncOpenAI,
    model: str = DEFAULT_MODEL,
) -> list[str]:
    """Generate topic tags from content using OpenAI.

    Args:
        content: Article content (plain text or HTML)
        client: AsyncOpenAI client instance
        model: OpenAI model to use

    Returns:
        List of lowercase single-word tags
    """
    if not content or not content.strip():
        return []

    # Truncate content to save tokens
    truncated = content[:MAX_CONTENT_LENGTH]
    if len(content) > MAX_CONTENT_LENGTH:
        truncated += "..."

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": TAG_PROMPT.format(content=truncated),
                }
            ],
            max_tokens=100,
            temperature=0.3,
        )

        # Parse response
        raw_tags = response.choices[0].message.content or ""
        tags = parse_tags(raw_tags)

        logger.debug(f"Generated tags: {tags}")
        return tags

    except Exception as e:
        logger.warning(f"Failed to generate tags: {e}")
        return []


def parse_tags(raw: str) -> list[str]:
    """Parse LLM response into clean tag list."""
    tags = []

    for line in raw.strip().split("\n"):
        # Clean up the line
        tag = line.strip().lower()

        # Remove common prefixes like "1.", "-", "*"
        tag = re.sub(r"^[\d\.\-\*\•]+\s*", "", tag)

        # Remove any remaining punctuation
        tag = re.sub(r"[^\w\s-]", "", tag)

        # Take only the first word if multiple words
        words = tag.split()
        if words:
            tag = words[0]

        # Validate tag
        if tag and len(tag) >= 2 and len(tag) <= 30:
            tags.append(tag)

    # Deduplicate while preserving order
    seen = set()
    unique_tags = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)

    return unique_tags[:5]  # Limit to 5 tags


def create_openai_client() -> Optional[AsyncOpenAI]:
    """Create an AsyncOpenAI client using environment variable."""
    try:
        return AsyncOpenAI()
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {e}")
        return None
