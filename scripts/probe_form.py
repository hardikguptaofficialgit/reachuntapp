import httpx

t = httpx.get("https://mailmeteor.com/tools/linkedin-email-finder", timeout=60).text
print("turnstile", "turnstile" in t.lower())
print("cf-turnstile", "cf-turnstile" in t)
idx = t.find("linkedin-url")
print(t[idx - 200 : idx + 800])
