# Generated extractor for rollcall.com
# Generated: 2026-03-12 08:59
# Sample URL: https://rollcall.com/factbase/trump/transcript/donald-trump-interview-tom-llamas-nbc-news-february-4-2026/
# Instructions: Focus on extracting speaker dialogue

from bs4 import BeautifulSoup
import re


def extract(html: str) -> str:
    """
    Extract speaker dialogue from transcript HTML.
    
    Returns formatted text with speaker names and their dialogue.
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all transcript entries - they have class "mb-4 border-b mx-6 my-4"
    # and contain speaker dialogue structure
    transcript_entries = soup.find_all('div', class_='mb-4 border-b mx-6 my-4')
    
    result = []
    
    for entry in transcript_entries:
        # Find speaker name - it's in an h2 tag
        speaker_tag = entry.find('h2', class_='text-md inline')
        if not speaker_tag:
            continue
        speaker_name = speaker_tag.get_text(strip=True)
        
        # Find timestamp - it's in a span with class "text-xs text-gray-600 inline ml-2"
        timestamp_tag = entry.find('span', class_='text-xs text-gray-600 inline ml-2')
        timestamp = timestamp_tag.get_text(strip=True) if timestamp_tag else ""
        
        # Find dialogue text - it's in a div with class "flex-auto text-md text-gray-600 leading-loose"
        dialogue_tag = entry.find('div', class_='flex-auto text-md text-gray-600 leading-loose')
        if not dialogue_tag:
            continue
        dialogue = dialogue_tag.get_text(strip=True)
        
        # Format the output
        if timestamp:
            result.append(f"{speaker_name} [{timestamp}]:")
        else:
            result.append(f"{speaker_name}:")
        result.append(f"  {dialogue}")
        result.append("")  # Empty line between entries
    
    return "\n".join(result)
