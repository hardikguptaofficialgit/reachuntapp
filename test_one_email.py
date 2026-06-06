"""Test a single LinkedIn URL on Mailmeteor."""

import argparse
import asyncio

from src.mailmeteor import MailmeteorFinder


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--url",
        default="https://www.linkedin.com/in/ethan-hilton/",
        help="LinkedIn profile URL",
    )
    p.add_argument("--connect-chrome", type=int, default=0, help="CDP port e.g. 9222")
    args = p.parse_args()
    cdp = f"http://127.0.0.1:{args.connect_chrome}" if args.connect_chrome else None
    finder = MailmeteorFinder(connect_cdp=cdp)
    await finder.start()
    try:
        await finder.warmup(wait_seconds=120, interactive=True)
        email, status = await finder.find_email(args.url)
        print(f"status={status} email={email or '(none)'}")
        if status == "error":
            print("Mailmeteor returned an error. Run .\\run-warmup.ps1 and complete Cloudflare.")
    finally:
        await finder.close()


if __name__ == "__main__":
    asyncio.run(main())
