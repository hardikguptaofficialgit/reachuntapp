import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

LINKEDIN = "https://www.linkedin.com/in/ethan-hilton/"


async def main():
    out = Path(__file__).resolve().parent / "mailmeteor_debug"
    out.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(
            "https://mailmeteor.com/tools/linkedin-email-finder",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await page.wait_for_timeout(2000)
        inputs = page.locator("input")
        print("input count", await inputs.count())
        for i in range(await inputs.count()):
            el = inputs.nth(i)
            print(i, await el.get_attribute("type"), await el.get_attribute("name"), await el.get_attribute("placeholder"))
        await inputs.first.fill(LINKEDIN)
        await page.get_by_role("button", name=re.compile("find", re.I)).first.click()
        for sec in [5, 15, 30]:
            await page.wait_for_timeout(sec * 1000)
            text = await page.inner_text("body")
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
            print(f"after {sec}s emails", emails[:5])
            if emails:
                break
        await page.screenshot(path=str(out / "screen.png"), full_page=True)
        html = await page.content()
        (out / "page.html").write_text(html, encoding="utf-8")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
