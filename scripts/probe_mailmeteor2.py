import asyncio
import re
from urllib.parse import quote

from playwright.async_api import async_playwright

LINKEDIN = "https://www.linkedin.com/in/ethan-hilton/"


async def main():
    url = "https://mailmeteor.com/tools/linkedin-email-finder"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        inp = page.locator('input[type="url"], input[type="text"]').first
        await inp.fill(LINKEDIN)
        await page.get_by_role("button", name=re.compile("find email", re.I)).click()
        try:
            await page.wait_for_selector("text=@", timeout=45000)
        except Exception as e:
            print("wait error", e)
        body = await page.inner_text("body")
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", body)
        print("emails", list(dict.fromkeys(emails)))
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
