"""LangChain agent using modern create_agent API (LangChain 1.0+)."""
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler
from langchain.agents import create_agent
from playground.browser_tools_v11.tools import SCRAPING_TOOLS
from playground.browser_tools_v11 import core
from playground.browser_tools_v11.prompts import SYSTEM_PROMPT, USER_PROMPT
from playground.browser_tools_v11.callbacks import AgentLogger

load_dotenv()

class ContentLink(BaseModel):
    date: str
    title: str
    url: str

class ScrapingResult(BaseModel):
    total_found: int
    links: List[ContentLink]

class ScrapingAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind(parallel_tool_calls=False)

    async def run(
        self, 
        url: str, 
        start_date: str, 
        end_date: str, 
        callbacks: Optional[List[BaseCallbackHandler]] = None,
        verbose: bool = True
    ) -> dict:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        stop_date = (start_dt - timedelta(days=1)).strftime("%Y-%m-%d")

        input_msg = USER_PROMPT.format(
            url=url, 
            start_date=start_date, 
            end_date=end_date,
            stop_date=stop_date
        )
        
        if callbacks is None and verbose:
            callbacks = [AgentLogger()]
        
        # Modern approach: create_agent with system_prompt
        agent = create_agent(
            model=self.llm,
            tools=SCRAPING_TOOLS,
            system_prompt=SYSTEM_PROMPT
        )
        
        # Run agent with browser session
        async with core.AsyncWebCrawler(config=core.BROWSER_CONFIG) as crawler:
            core.ACTIVE_CRAWLER = crawler
            
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": input_msg}]},
                config={
                    "callbacks": callbacks or [],
                    "recursion_limit": 50,
                    "max_execution_time": 300  # 5 minute timeout
                }
            )
        
        # Extract final message
        raw_output = result["messages"][-1].content if result.get("messages") else ""
        
        # Structure the output using LLM
        structured_llm = self.llm.with_structured_output(ScrapingResult)
        parsed_result = await structured_llm.ainvoke(
            f"Extract the structured data from this response:\n\n{raw_output}"
        )
        
        return {"output": raw_output, "parsed": parsed_result}
