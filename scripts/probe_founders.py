import httpx
import re
from bs4 import BeautifulSoup

def parse_founders(html: str):
    soup = BeautifulSoup(html, "html.parser")
    founders = []
    seen = set()

    # Strategy: links in founder area - linkedin.com/in only
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].rstrip("/")
        if "linkedin.com/in/" not in href:
            continue
        if href in seen:
            continue
        # Try to find founder name from nearby text
        name = None
        parent = a.find_parent(["div", "section", "li"])
        if parent:
            # Often name is in a div with font-bold or similar near the link
            for tag in parent.find_all(["div", "span", "h3", "h4", "a"]):
                t = tag.get_text(strip=True)
                if (
                    t
                    and "linkedin" not in t.lower()
                    and len(t) < 80
                    and "founder" not in t.lower()
                    and "@" not in t
                ):
                    if tag.name in ("div", "span", "h3", "h4") and 2 <= len(t.split()) <= 5:
                        name = t
                        break
        seen.add(href)
        founders.append({"name": name or "", "linkedin_url": href if href.endswith("/") else href + "/"})
    return founders


def main():
    url = "https://www.ycombinator.com/companies/caseflood-ai"
    r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    founders = parse_founders(r.text)
    print("founders", founders)
    # dedupe by linkedin
    unique = {}
    for f in founders:
        key = f["linkedin_url"].lower()
        if key not in unique:
            unique[key] = f
    print("unique", list(unique.values()))


if __name__ == "__main__":
    main()
