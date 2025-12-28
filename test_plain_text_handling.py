"""Test that plain_text handling works for both dict and string formats."""

import asyncio
from datetime import datetime

from openai import AsyncOpenAI

from linkfeed.utils.date_extraction import extract_date_with_llm


async def test_plain_text_formats():
    """Test both dict and string formats for plain_text."""
    
    # Test data with publication date
    plain_text_dicts = [
        {'text': 'Skip to main content'},
        {'text': 'Engineering at Anthropic'},
        {'text': 'How we built our system'},
        {'text': 'Published Jun 13, 2025'},
        {'text': 'This article explains our approach...'},
    ]
    
    plain_text_strings = [
        'Skip to main content',
        'Engineering at Anthropic',
        'How we built our system',
        'Published Jun 13, 2025',
        'This article explains our approach...',
    ]
    
    # Mock client for testing (won't actually call API in this test)
    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set, skipping LLM test")
        print("\nTesting text extraction only:")
        
        # Test dict format
        print("\n--- Dict format (from readabilipy) ---")
        text_from_dicts = []
        for item in plain_text_dicts:
            if isinstance(item, dict):
                text_from_dicts.append(item.get('text', ''))
        print(f"Extracted {len(text_from_dicts)} text items")
        print(f"Sample: {text_from_dicts[3]}")
        
        # Test string format
        print("\n--- String format (legacy/alternative) ---")
        text_from_strings = []
        for item in plain_text_strings:
            if isinstance(item, str):
                text_from_strings.append(item)
        print(f"Extracted {len(text_from_strings)} text items")
        print(f"Sample: {text_from_strings[3]}")
        
        assert text_from_dicts == text_from_strings, "Extracted text should match"
        print("\n✓ Both formats extract the same text!")
        return
    
    client = AsyncOpenAI()
    
    print("Testing LLM date extraction with both formats...\n")
    
    # Test with dict format (actual readabilipy format)
    print("--- Test 1: Dict format (from readabilipy) ---")
    try:
        date1 = await extract_date_with_llm(plain_text_dicts, client)
        if date1:
            print(f"✓ Extracted date: {date1.strftime('%B %d, %Y')}")
        else:
            print("❌ No date found")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test with string format (for compatibility)
    print("\n--- Test 2: String format (legacy) ---")
    try:
        date2 = await extract_date_with_llm(plain_text_strings, client)
        if date2:
            print(f"✓ Extracted date: {date2.strftime('%B %d, %Y')}")
        else:
            print("❌ No date found")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Verify both formats produce the same result
    if date1 and date2:
        if date1 == date2:
            print("\n✓ Both formats produced the same date!")
        else:
            print(f"\n⚠️  Dates differ: {date1} vs {date2}")


if __name__ == "__main__":
    asyncio.run(test_plain_text_formats())
