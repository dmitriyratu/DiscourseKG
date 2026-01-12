"""LangGraph agent using the Split Navigation/Harvesting architecture."""
import json
from datetime import datetime, timedelta
from typing import TypedDict, Annotated, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from playground.browser_tools_v11.tools import SCRAPING_TOOLS
from playground.browser_tools_v11 import core
from playground.browser_tools_v11.prompts import SYSTEM_PROMPT, USER_PROMPT

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

class ScrapingAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(SCRAPING_TOOLS)
        
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", lambda state: {"messages": [self.llm.invoke(state["messages"])]})
        workflow.add_node("tools", ToolNode(SCRAPING_TOOLS))
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent", 
            lambda state: "tools" if state["messages"][-1].tool_calls else END
        )
        workflow.add_edge("tools", "agent")
        self.graph = workflow.compile()

    async def run(self, url: str, start_date: str, end_date: str) -> dict:

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        stop_date = (start_dt - timedelta(days=1)).strftime("%Y-%m-%d")

        system_msg = SYSTEM_PROMPT.format(
            start_date=start_date, 
            end_date=end_date, 
            stop_date=stop_date
        )
        input_msg = USER_PROMPT.format(
            url=url, 
            start_date=start_date, 
            end_date=end_date
        )
        
        state = {"messages": [SystemMessage(content=system_msg), HumanMessage(content=input_msg)]}
        config = {"recursion_limit": 100}
        
        async with core.AsyncWebCrawler(config=core.BROWSER_CONFIG) as crawler:
            core.ACTIVE_CRAWLER = crawler
            result = await self.graph.ainvoke(state, config=config)
                
        raw_output = result["messages"][-1].content
        try:
            parsed = json.loads(raw_output)
        except Exception:
            parsed = None
        
        return {"output": raw_output, "parsed": parsed}
