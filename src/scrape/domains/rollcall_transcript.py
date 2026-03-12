# Generated extractor for rollcall.com
# Generated: 2026-02-18 23:30
# Sample URL: https://rollcall.com/factbase/trump/transcript/donald-trump-press-conference-jd-vance-joint-pashinyan-armenia-february-9-2026/
# Instructions: Focus on extracting speaker dialogue

from bs4 import BeautifulSoup


def extract(html: str) -> str:
    """
    Extract speaker dialogue from transcript HTML.
    Focuses on extracting speaker names, timestamps, and their dialogue text.
    """
    soup = BeautifulSoup(html, 'html.parser')
    output_lines = []
    
    # Find all transcript segments (each speaker's dialogue block)
    # These are divs with classes like "mb-4 border-b mx-6 my-4"
    transcript_blocks = soup.find_all('div', class_='mb-4 border-b mx-6 my-4')
    
    for block in transcript_blocks:
        # Extract speaker name (in h2 tag)
        speaker_tag = block.find('h2', class_='text-md inline')
        if not speaker_tag:
            continue
        speaker_name = speaker_tag.get_text(strip=True)
        
        # Extract timestamp (in span with specific classes)
        timestamp_tag = block.find('span', class_='text-xs text-gray-600 inline ml-2')
        timestamp = timestamp_tag.get_text(strip=True) if timestamp_tag else ""
        
        # Extract dialogue text (in div with class "flex-auto text-md text-gray-600 leading-loose")
        dialogue_tag = block.find('div', class_='flex-auto text-md text-gray-600 leading-loose')
        if not dialogue_tag:
            continue
        dialogue_text = dialogue_tag.get_text(strip=True)
        
        # Format output
        output_lines.append(f"{speaker_name} {timestamp}")
        output_lines.append(dialogue_text)
        output_lines.append("")  # Blank line for readability
    
    return "\n".join(output_lines)
