import httpx

url = "https://www.ycombinator.com/companies/caseflood-ai"
r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
text = r.text
idx = text.find("Active Founders")
print("idx", idx)
print(text[idx : idx + 8000])
