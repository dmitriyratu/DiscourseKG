from crewai import Agent, Task, Crew, LLM
import json
import logging
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from playground.browser_tools_ai import InspectPage

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscriptMetadata(BaseModel):
    total_found: int = Field(description="Total transcripts found")
    coverage_complete: bool = Field(description="Whether coverage is complete")
    date_range_covered: str = Field(description="Date range covered")
    notes: str = Field(description="Explanation of coverage or issues")

class TranscriptResult(BaseModel):
    url: str = Field(description="Direct transcript URL")
    title: str = Field(description="Transcript title")
    date: str = Field(description="Transcript date")

class TranscriptOutput(BaseModel):
    transcripts: List[TranscriptResult] = Field(description="List of found transcripts")
    metadata: TranscriptMetadata = Field(description="Search metadata")


explorer = Agent(
    role="Transcript Discovery Specialist",
    goal="{goal}",
    backstory="""Expert at discovering transcript URLs from diverse website structures.
    
    You analyze site patterns, adapt your strategy, and determine optimal 
    approaches for complete coverage. You recognize when you've found everything 
    vs when more content exists.""",
    llm=LLM(model="gpt-4o-mini"),
    tools=[InspectPage()],
    verbose=True,
    max_iter=15
)

crew = Crew(
    agents=[explorer], 
    tasks=[], 
    max_rpm=10,
    manager_llm=LLM(model="gpt-4o-mini"),
    memory=True,
    verbose=True,
    tracing=True,
)


def find_transcripts(url, speaker=None, start_date=None, end_date=None, guidance=None):
    """Systematically find transcript URLs matching criteria."""
    
    # Build filter descriptions
    filters = []
    if speaker:
        filters.append(f"Speaker: {speaker}")
    if start_date and end_date:
        filters.append(f"Date range: {start_date} to {end_date}")
    elif start_date:
        filters.append(f"Date: {start_date} or later")
    elif end_date:
        filters.append(f"Date: {end_date} or earlier")
    
    filter_text = " | ".join(filters) if filters else "No filters"
    guidance_text = f"\n\nSite-specific guidance:\n{guidance}" if guidance else ""
    
    task = Task(
        description=f"""
        Find all transcript URLs from: {url}
        
        Criteria: {filter_text}{guidance_text}
        
        Success means: Complete coverage of the specified date range with 
        confidence you found all matching transcripts, or clear explanation 
        of coverage limits.
        
        Return only direct transcript URLs (not listing/category pages).
        """,
        expected_output="""List of transcript objects with url, title, and date, plus metadata about coverage.""",
        output_pydantic=TranscriptOutput,
        agent=explorer
    )
    
    crew.tasks = [task]
    result = crew.kickoff(inputs={"goal": f"Find {speaker or 'all'} transcript URLs"})
    
    # Use structured output directly
    logger.info(f"Agent metadata: {result.pydantic.metadata}")
    
    # Extract and return URLs
    return [t.url for t in result.pydantic.transcripts]


if __name__ == "__main__":
    # urls = find_transcripts(
    #     url='https://www.rev.com/category/donald-trump',
    #     speaker='Donald Trump',
    #     start_date="2025-11-23",
    #     guidance="info should be under the 'Transcripts' section and you can load more if needed, the dates of the transcripts can be found under the titles"
    # )

    urls = find_transcripts(
        url='https://rollcall.com/factbase/trump/search/',
        speaker='Donald Trump',
        start_date="2025-11-23",
        end_date="2025-11-29"
    )
    