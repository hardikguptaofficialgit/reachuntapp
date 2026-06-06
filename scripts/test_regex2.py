import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

url = "https://www.ycombinator.com/companies/a0-dev"
html = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text
section = html.split("Active Founders", 1)[1].split("Primary Partner", 1)[0]

for i, m in enumerate(re.finditer(r'aria-label="LinkedIn profile"', section)):
    start = max(0, m.start() - 400)
    print(f"\n--- linkedin {i} ---")
    print(section[start : m.end() + 80])
