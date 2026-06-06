import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from src.yc_founders import FOUNDER_BLOCK_RE, fetch_founders

url = "https://www.ycombinator.com/companies/a0-dev"
html = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text
section = html.split("Active Founders", 1)[1].split("Primary Partner", 1)[0]
print("xl matches", FOUNDER_BLOCK_RE.findall(section))
r2 = re.compile(
    r'class="text-lg font-bold">([^<]+)</div>.*?'
    r'href="(https://www\.linkedin\.com/in/[^"]+)"[^>]*aria-label="LinkedIn profile"',
    re.DOTALL,
)
print("lg matches", r2.findall(section))
r3 = re.compile(
    r'font-bold">([^<]+)</div>.*?'
    r'href="(https://www\.linkedin\.com/in/[^"]+)"[^>]*aria-label="LinkedIn profile"',
    re.DOTALL,
)
print("generic matches", r3.findall(section))
print("fetch", fetch_founders(url))
