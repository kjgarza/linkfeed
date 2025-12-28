"""Test script for LLM-based date extraction."""

import asyncio
import os
from datetime import datetime

import aiohttp
from openai import AsyncOpenAI

from linkfeed.parsers.base import get_parser
from linkfeed.utils.network import fetch_url


async def test_date_extraction():
    """Test date extraction for a specific URL."""
    url = "https://www.anthropic.com/engineering/multi-agent-research-system"
    
    # Check if OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not found in environment")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        openai_client = None
    else:
        print(f"✓ OPENAI_API_KEY found: {api_key[:8]}...")
        openai_client = AsyncOpenAI(api_key=api_key)
    
    # Fetch the URL
    print(f"\nFetching: {url}")
    async with aiohttp.ClientSession() as session:
        result = await fetch_url(url, session=session)
        
        if not result:
            print("❌ Failed to fetch URL")
            return
        
        print(f"✓ Fetched {len(result.content)} bytes")
        
        # Get parser
        parser = get_parser(url)
        if not parser:
            print("❌ No parser found for URL")
            return
        
        print(f"✓ Using parser: {parser.__class__.__name__}")
        
        # Parse WITHOUT OpenAI client
        print("\n--- Test 1: Without OpenAI client ---")
        item1 = await parser.parse(
            result.url,
            result.content,
            result.content_type,
            result.content_length,
            session,
            openai_client=None,
        )
        
        if item1:
            print(f"Title: {item1.title}")
            print(f"Date: {item1.date_published}")
            print(f"Date type: {type(item1.date_published)}")
            if item1.date_published:
                # Check if it's today's date (fallback)
                today = datetime.now().date()
                if item1.date_published.date() == today:
                    print("⚠️  Using today's date (datetime.now() fallback)")
                else:
                    print(f"✓ Found date: {item1.date_published.strftime('%B %d, %Y')}")
        
        # Parse WITH OpenAI client
        if openai_client:
            print("\n--- Test 2: With OpenAI client ---")
            item2 = await parser.parse(
                result.url,
                result.content,
                result.content_type,
                result.content_length,
                session,
                openai_client=openai_client,
            )
            
            if item2:
                print(f"Title: {item2.title}")
                print(f"Date: {item2.date_published}")
                print(f"Date type: {type(item2.date_published)}")
                if item2.date_published:
                    today = datetime.now().date()
                    if item2.date_published.date() == today:
                        print("⚠️  Still using today's date (LLM didn't find date)")
                    else:
                        print(f"✓ LLM found date: {item2.date_published.strftime('%B %d, %Y')}")
        else:
            print("\n--- Test 2: Skipped (no OpenAI client) ---")


if __name__ == "__main__":
    asyncio.run(test_date_extraction())
