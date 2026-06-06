import asyncio
import json
import re

from playwright.async_api import async_playwright

LINKEDIN = "https://www.linkedin.com/in/ethan-hilton/"


async def main():
    responses = []

    async def on_response(response):
        if response.request.resource_type in ("xhr", "fetch"):
            try:
                body = await response.text()
            except Exception:
                return
            if "@" in body or "email" in body.lower():
                responses.append((response.url, body[:500]))

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("response", on_response)
        await page.goto(
            "https://mailmeteor.com/tools/linkedin-email-finder",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await page.locator('input[name="linkedin-url"]').fill(LINKEDIN)
        await page.get_by_role("button", name=re.compile("find email", re.I)).click()
        await page.wait_for_timeout(25000)
        text = await page.inner_text("body")
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        print("body emails", emails)
        print("xhr hits", len(responses))
        for url, snippet in responses[:10]:
            print("---", url)
            print(snippet)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
