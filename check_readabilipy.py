"""Quick check of readabilipy structure."""

from readabilipy import simple_json_from_html_string

html = """
<html>
<head><title>Test</title></head>
<body>
<article>
<p>First paragraph</p>
<p>Second paragraph</p>
</article>
</body>
</html>
"""

result = simple_json_from_html_string(html, use_readability=False)

print("Keys in result:")
for key in result.keys():
    print(f"  {key}: {type(result[key])}")

print("\nplain_content type:", type(result.get('plain_content')))
print("plain_content sample:", str(result.get('plain_content'))[:200])

print("\nplain_text type:", type(result.get('plain_text')))
print("plain_text structure:")
if isinstance(result.get('plain_text'), list):
    for i, item in enumerate(result.get('plain_text')[:3]):
        print(f"  [{i}] type={type(item)}, value={item}")
