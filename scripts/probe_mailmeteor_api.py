"""Capture Mailmeteor network traffic on email lookup."""
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

LINKEDIN = "https://www.linkedin.com/in/ethan-hilton/"
OUT = Path(__file__).parent / "mailmeteor_network.jsonl"


async def main():
    hits = []

    async def on_response(response):
        try:
            if response.request.resource_type not in ("xhr", "fetch", "document"):
                return
            body = await response.text()
        except Exception:
            return
        if len(body) < 20:
            return
        low = body.lower()
        if "@" in body or "email" in low or "error" in low or response.status >= 400:
            hits.append(
                {
                    "url": response.url,
                    "status": response.status,
                    "method": response.request.method,
                    "body_preview": body[:2000],
                }
            )

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",
        )
        page = await browser.new_page()
        page.on("response", on_response)
        await page.goto(
            "https://mailmeteor.com/tools/linkedin-email-finder",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        inp = page.locator('input[name="linkedin-url"]')
        await inp.click()
        await inp.fill("")
        await inp.type(LINKEDIN, delay=50)
        await page.get_by_role("button", name="FIND EMAIL").click()
        await page.wait_for_timeout(35000)
        await page.screenshot(path=str(OUT.with_suffix(".png")), full_page=True)
        await browser.close()

    with OUT.open("w", encoding="utf-8") as f:
        for h in hits:
            f.write(json.dumps(h) + "\n")
    print("wrote", OUT, "hits", len(hits))


asyncio.run(main())
