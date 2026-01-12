"""LangChain tool wrappers for the Split Navigation/Harvesting architecture."""
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
import json
from typing import Optional, Dict, Any
from playground.browser_tools_v11.core import get_navigation_map, harvest_content

class NavInput(BaseModel):
    url: str = Field(description="The site URL to analyze for navigation structure")

class HarvestInput(BaseModel):
    url: str = Field(description="The site URL to extract content from")
    action: Optional[Dict[str, Any]] = Field(
        None, 
        description="Optional action to perform before harvesting. Format: {'type': 'scroll', 'value': 3} or {'type': 'click', 'value': '.css-selector'}"
    )

def _serialize_nav(result) -> str:
    if not result.success:
        return json.dumps({"success": False, "error": result.error})
    return json.dumps({
        "success": True,
        "url": result.url,
        "navigation_map": result.navigation_html
    }, indent=2)

def _serialize_harvest(result) -> str:
    if not result.success:
        return json.dumps({"success": False, "error": result.error})
    
    # Return structured links - much more token efficient than HTML
    return json.dumps({
        "success": True,
        "url": result.url,
        "links_found": len(result.links),
        "links": result.links # Return all filtered links
    }, indent=2)

async def _nav_wrapper(url: str) -> str:
    res = await get_navigation_map(url)
    return _serialize_nav(res)

async def _harvest_wrapper(url: str, action: Optional[Dict] = None) -> str:
    res = await harvest_content(url, action)
    return _serialize_harvest(res)

# Tool Definitions
get_navigation_map_tool = StructuredTool.from_function(
    coroutine=_nav_wrapper,
    name="get_navigation_map",
    description=(
        "Returns a lightweight map of buttons, pagination links, and navigation bars. "
        "Use this first to see HOW to move through the site (e.g. find the 'Next' button selector)."
    ),
    args_schema=NavInput
)

harvest_content_tool = StructuredTool.from_function(
    coroutine=_harvest_wrapper,
    name="harvest_content",
    description=(
        "Performs an optional action (scroll/click) and returns a structured list of content links and context. "
        "Use this to get the actual data (titles, dates, URLs) from the page."
    ),
    args_schema=HarvestInput
)

SCRAPING_TOOLS = [get_navigation_map_tool, harvest_content_tool]
