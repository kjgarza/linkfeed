"""Debug script to see what's happening in date extraction."""

import asyncio
import aiohttp
from bs4 import BeautifulSoup

from linkfeed.utils.network import fetch_url


async def debug_date_extraction():
    """Debug what's in the HTML for date extraction."""
    url = "https://www.anthropic.com/engineering/multi-agent-research-system"
    
    async with aiohttp.ClientSession() as session:
        result = await fetch_url(url, session=session)
        
        if not result:
            print("Failed to fetch")
            return
        
        html_str = result.content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html_str, "html.parser")
        
        print("=== Checking for publication date in meta tags ===\n")
        
        # Check article:published_time
        og_published = soup.find("meta", property="article:published_time")
        if og_published:
            print(f"article:published_time: {og_published.get('content')}")
        else:
            print("article:published_time: NOT FOUND")
        
        # Check JSON-LD
        print("\n=== Checking JSON-LD ===")
        import json
        found_json_ld = False
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                print(f"Found JSON-LD: {type(data)}")
                if isinstance(data, dict):
                    date_pub = data.get("datePublished") or data.get("dateCreated")
                    if date_pub:
                        print(f"  datePublished/dateCreated: {date_pub}")
                        found_json_ld = True
            except:
                pass
        
        if not found_json_ld:
            print("No date in JSON-LD")
        
        # Check other meta tags
        print("\n=== Other meta date tags ===")
        meta_date = soup.find("meta", attrs={"name": "date"})
        if meta_date:
            print(f"meta[name=date]: {meta_date.get('content')}")
        else:
            print("meta[name=date]: NOT FOUND")
        
        # Check time element
        print("\n=== Time elements ===")
        time_elems = soup.find_all("time", attrs={"datetime": True})
        if time_elems:
            for time_elem in time_elems[:3]:  # Show first 3
                print(f"time[datetime]: {time_elem['datetime']}")
        else:
            print("time[datetime]: NOT FOUND")
        
        # Check plain text
        print("\n=== Plain text content (first 500 chars) ===")
        from readabilipy import simple_json_from_html_string
        article = simple_json_from_html_string(html_str, use_readability=False)
        plain_text = article.get("plain_text")
        if plain_text:
            print(f"Found {len(plain_text)} paragraphs")
            print(f"Type: {type(plain_text)}")
            # Show first few paragraphs
            for i, para in enumerate(plain_text[:5]):
                print(f"\nParagraph {i} (type: {type(para)}): {str(para)[:200]}")
        else:
            print("No plain_text found")


if __name__ == "__main__":
    asyncio.run(debug_date_extraction())
