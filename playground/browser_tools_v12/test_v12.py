"""Test the v12 orchestrator-based scraper."""
import asyncio
from playground.browser_tools_v12.agent import ScrapingAgent
from playground.browser_tools_v12.callbacks import AgentLogger

async def main():
    agent = ScrapingAgent()
    logger = AgentLogger()
    result = await agent.run(
        url="https://rollcall.com/factbase/trump/search/",
        start_date="2026-01-06",
        end_date="2026-01-10",
        callbacks=[logger]
    )

if __name__ == "__main__":
    asyncio.run(main())
