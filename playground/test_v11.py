"""Test the v11 universal scraper."""
import asyncio
from playground.browser_tools_v11.agent import ScrapingAgent

async def main():
    agent = ScrapingAgent()
    result = await agent.run(
        url="https://rollcall.com/factbase/trump/search/",
        start_date="2026-01-06",
        end_date="2026-01-10"
    )

if __name__ == "__main__":
    asyncio.run(main())