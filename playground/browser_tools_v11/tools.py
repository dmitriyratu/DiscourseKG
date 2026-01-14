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
        "Returns a lightweight map of navigation elements (buttons, pagination links, nav bars). "
        "Returns HTML snippets with attributes (class, id, href, aria-label, title) for interactive elements. "
        "Use this first to understand the site's navigation structure before harvesting content. "
        "Returns JSON: {{'success': bool, 'url': str, 'navigation_map': str}}"
    ),
    args_schema=NavInput
)

harvest_content_tool = StructuredTool.from_function(
    coroutine=_harvest_wrapper,
    name="harvest_content",
    description=(
        "Performs an optional action (scroll/click) and returns a structured list of content links with context. "
        "Supported actions: {{'type': 'scroll', 'value': N}} to scroll N times, or {{'type': 'click', 'value': '.css-selector'}} to click an element. "
        "Returns JSON: {{'success': bool, 'url': str, 'links_found': int, 'links': [{{'url': str, 'text': str, 'context': str}}]}}. "
        "Browser session is persistent across tool calls; actions are cumulative."
    ),
    args_schema=HarvestInput
)

SCRAPING_TOOLS = [get_navigation_map_tool, harvest_content_tool]
