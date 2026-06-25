"""Generate an email preview HTML file you can open in a browser."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from briefing import run_briefing

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

result = run_briefing()

preview_path = os.path.join(REPO_ROOT, "docs", "email_preview.html")
with open(preview_path, "w", encoding="utf-8") as f:
    f.write(
        '<html><body style="background:#0d1117;padding:20px;">'
        + result["email_html"]
        + "</body></html>"
    )
print(f"\nEmail preview saved to: {preview_path}")
