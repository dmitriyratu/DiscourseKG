"""Test the v13 autonomous scraping agent."""
import asyncio
from playground.browser_tools_v13.agent import ScrapingAgent

async def main():
    agent = ScrapingAgent(max_pages=10, headless=False)
    articles = await agent.run(
        url="https://rollcall.com/factbase/trump/search/",
        start_date="2026-01-06",
        end_date="2026-01-10",
    )
    print(f"\nCollected {len(articles)} articles")

if __name__ == "__main__":
    asyncio.run(main())
