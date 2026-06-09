import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

LINKEDIN = "https://www.linkedin.com/in/ethan-hilton/"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://mailmeteor.com/tools/linkedin-email-finder", timeout=60000)
        await page.locator('input[name="linkedin-url"]').fill(LINKEDIN)
        await page.get_by_role("button", name=re.compile("find email", re.I)).click()
        await page.wait_for_timeout(20000)
        text = await page.inner_text("body")
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        out = Path(__file__).with_name("headed_result.txt")
        with out.open("w", encoding="utf-8") as f:
            f.write("emails=" + str(emails) + "\n\n" + text)
        await browser.close()


asyncio.run(main())
