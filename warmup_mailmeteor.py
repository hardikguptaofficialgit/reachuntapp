"""One-time: open Mailmeteor in Chrome and pass Cloudflare Turnstile."""

import asyncio

from src.mailmeteor import MailmeteorFinder


async def main() -> None:
    finder = MailmeteorFinder()
    await finder.start()
    try:
        await finder.warmup(wait_seconds=300, interactive=True)
    finally:
        await finder.close()


if __name__ == "__main__":
    asyncio.run(main())
