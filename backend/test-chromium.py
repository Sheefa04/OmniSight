
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        print("CHROMIUM LAUNCHED SUCCESSFULLY")
        await browser.close()


asyncio.run(main())
