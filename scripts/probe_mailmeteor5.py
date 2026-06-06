import asyncio
import re

from playwright.async_api import async_playwright

LINKEDIN = "https://www.linkedin.com/in/ethan-hilton/"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        await page.goto(
            "https://mailmeteor.com/tools/linkedin-email-finder",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await page.locator('input[name="linkedin-url"]').fill(LINKEDIN)
        await page.get_by_role("button", name=re.compile("find email", re.I)).click()
        await page.wait_for_timeout(30000)
        text = await page.inner_text("body")
        out = __file__.replace("probe_mailmeteor5.py", "mailmeteor_body.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        print("emails", emails)
        print("wrote", out)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
