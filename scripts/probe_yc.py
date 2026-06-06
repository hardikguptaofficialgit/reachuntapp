import httpx
import re
import json

def main():
    r = httpx.get(
        "https://www.ycombinator.com/companies",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=60,
    )
    print("status", r.status_code, "len", len(r.text))
    # Common patterns in YC bundle
    for name in ["apiKey", "ALGOLIA", "algolia", "45BWZJ1SGC"]:
        print(name, r.text.find(name))

    m = re.search(r'"apiKey":"([^"]+)"', r.text)
    if m:
        print("apiKey", m.group(1)[:120])

    m2 = re.search(r"X-Algolia-API-Key['\"]?\s*,\s*['\"]([^'\"]+)", r.text)
    if m2:
        print("header key", m2.group(1)[:120])

    # Try search page HTML for company links
    r2 = httpx.get(
        "https://www.ycombinator.com/companies?query=caseflood.ai",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=60,
    )
    links = re.findall(r'href="(/companies/[^"?]+)"', r2.text)
    company_links = [l for l in links if l != "/companies"]
    print("search links sample", company_links[:10])

    # yc-oss
    r3 = httpx.get(
        "https://yc-oss.github.io/api/companies/all.json",
        timeout=120,
    )
    print("yc-oss status", r3.status_code)
    if r3.status_code == 200:
        data = r3.json()
        print("yc-oss count", len(data))
        for c in data:
            if "caseflood" in c.get("name", "").lower():
                print("found", c)


if __name__ == "__main__":
    main()
