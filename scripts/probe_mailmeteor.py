"""Quick probe for Mailmeteor email finder page structure."""
import asyncio
from urllib.parse import quote

from playwright.async_api import async_playwright

LINKEDIN = "https://www.linkedin.com/in/ethan-hilton/"


async def main():
    url = (
        "https://mailmeteor.com/tools/linkedin-email-finder?"
        f"linkedin-url={quote(LINKEDIN, safe='')}"
    )
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(3000)
        # try click find email
        btn = page.get_by_role("button", name="FIND EMAIL")
        if await btn.count():
            await btn.click()
        await page.wait_for_timeout(8000)
        text = await page.content()
        print("page length", len(text))
        # look for email patterns
        import re

        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        print("emails found", list(dict.fromkeys(emails))[:20])
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
