import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from src.yc_index import YCIndex

idx = YCIndex.load()
for name in ["a0.dev", "Aviro", "Agentin AI"]:
    c = idx.match(name)
    if not c:
        print(name, "no match")
        continue
    html = httpx.get(c.url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text
    print("\n===", name, c.url)
    print("Active Founders", "Active Founders" in html)
    if "Active Founders" in html:
        s = html.split("Active Founders", 1)[1][:4000]
        print("section sample:", s[:1200])
    import re

    print("font-bold names", re.findall(r'class="text-xl font-bold">([^<]+)</div>', html)[:5])
    print("linkedin aria", len(re.findall(r'aria-label="LinkedIn profile"', html)))
