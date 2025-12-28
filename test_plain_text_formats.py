"""Test that plain_text handling works for both dict and string formats."""

import asyncio
from datetime import datetime

from readabilipy import simple_json_from_html_string

from linkfeed.parsers.generic import GenericParser
from linkfeed.utils.url import generate_id


async def test_plain_text_handling():
    """Test that we handle both dict and string plain_text formats."""
    
    parser = GenericParser()
    
    # Test HTML with date in content
    html_with_date = """
    <html>
    <head><title>Test Article</title></head>
    <body>
        <h1>Test Article</h1>
        <p>Published June 13, 2025</p>
        <p>This is the first real paragraph of content that should be used as the summary.</p>
        <p>This is more content.</p>
    </body>
    </html>
    """
    
    # Test with actual readabilipy output (dict format)
    print("=== Test 1: Readabilipy dict format ===")
    article = simple_json_from_html_string(html_with_date, use_readability=False)
    
    print(f"plain_text type: {type(article.get('plain_text'))}")
    print(f"plain_text[0] type: {type(article.get('plain_text')[0])}")
    print(f"plain_text structure: {article.get('plain_text')[:3]}")
    
    item = parser._build_item_from_readability(
        url="https://example.com/test",
        article=article,
        html_str=html_with_date,
        openai_client=None,
    )
    
    print(f"\nExtracted summary: {item.summary}")
    print(f"Summary length: {len(item.summary) if item.summary else 0}")
    
    # Verify summary was extracted correctly
    if item.summary and len(item.summary) > 20:
        print("✓ Summary extracted successfully from dict format")
    else:
        print("❌ Failed to extract summary from dict format")
    
    # Test 2: Manually create string format (for compatibility)
    print("\n=== Test 2: String list format (for compatibility) ===")
    
    # Simulate if readabilipy ever changed to return strings
    article_str_format = {
        'title': 'Test Article',
        'plain_text': [
            'Test Article',
            'Published June 13, 2025',
            'This is the first real paragraph of content that should be used as the summary.',
        ],
        'plain_content': '<div><p>content</p></div>',
    }
    
    # This should also work with our isinstance checks
    item2 = parser._build_item_from_readability(
        url="https://example.com/test2",
        article=article_str_format,
        html_str=html_with_date,
        openai_client=None,
    )
    
    print(f"Extracted summary: {item2.summary}")
    
    if item2.summary and len(item2.summary) > 20:
        print("✓ Summary extracted successfully from string format")
    else:
        print("❌ Failed to extract summary from string format")
    
    print("\n=== All tests completed ===")


if __name__ == "__main__":
    asyncio.run(test_plain_text_handling())
