# Generated extractor for rollcall.com
# Generated: 2026-02-17 19:28
# Sample URL: https://rollcall.com/factbase/trump/transcript/donald-trump-interview-tom-llamas-nbc-news-february-4-2026/
# Instructions: Focus on extracting speaker dialogue with timestamps and metadata


from bs4 import BeautifulSoup
import re

def extract(html: str) -> str:
    """
    Extract speaker dialogue with timestamps and metadata from transcript HTML.
    """
    soup = BeautifulSoup(html, 'html.parser')
    output = []
    
    # Extract title
    title_elem = soup.find('h1', class_='text-[#2F3C4B]')
    if title_elem:
        title = title_elem.get_text(strip=True)
        output.append(f"TITLE: {title}")
        output.append("=" * 80)
        output.append("")
    
    # Extract speaker statistics
    speakers_section = soup.find('div', {'x-show': "currentTab === 'speakers'"})
    if speakers_section:
        output.append("SPEAKER STATISTICS:")
        output.append("-" * 80)
        speaker_divs = speakers_section.find_all('div', class_='flex-1 h-content')
        for speaker_div in speaker_divs:
            speaker_name_elem = speaker_div.find('div', class_='font-graphik text-sm font-medium')
            if speaker_name_elem:
                speaker_name = speaker_name_elem.get_text(strip=True)
                output.append(f"\n{speaker_name}:")
                
                # Extract statistics
                stats = speaker_div.find_all('div', class_='font-graphik text-xs font-medium text-[#2F3C4B]')
                for stat in stats:
                    stat_text = stat.get_text(strip=True)
                    output.append(f"  {stat_text}")
        output.append("")
        output.append("=" * 80)
        output.append("")
    
    # Extract topics
    topics_section = soup.find('div', {'x-show': "currentTab === 'topics'"})
    if topics_section:
        output.append("TOPICS:")
        output.append("-" * 80)
        topic_links = topics_section.find_all('a', class_='text-[#015582]')
        for link in topic_links:
            topic = link.get_text(strip=True)
            output.append(f"  - {topic}")
        output.append("")
        output.append("=" * 80)
        output.append("")
    
    # Extract entities
    entities_section = soup.find('div', {'x-show': "currentTab === 'entities'"})
    if entities_section:
        output.append("ENTITIES:")
        output.append("-" * 80)
        entity_divs = entities_section.find_all('div', class_='text-[#015582] text-sm font-normal')
        for entity_div in entity_divs:
            entity = entity_div.get_text(strip=True)
            output.append(f"  - {entity}")
        output.append("")
        output.append("=" * 80)
        output.append("")
    
    # Extract full transcript
    output.append("FULL TRANSCRIPT:")
    output.append("=" * 80)
    output.append("")
    
    # Find all transcript segments
    transcript_divs = soup.find_all('div', class_='mb-4 border-b mx-6 my-4')
    
    for idx, div in enumerate(transcript_divs, 1):
        # Extract speaker name and timestamp
        h2_elem = div.find('h2', class_='text-md inline')
        timestamp_elem = div.find('span', class_='text-xs text-gray-600 inline ml-2')
        
        if h2_elem:
            speaker = h2_elem.get_text(strip=True)
            timestamp = ""
            if timestamp_elem:
                timestamp = timestamp_elem.get_text(strip=True)
            
            # Extract the dialogue text
            dialogue_elem = div.find('div', class_='flex-auto text-md text-gray-600 leading-loose')
            if dialogue_elem:
                dialogue = dialogue_elem.get_text(strip=True)
                
                # Format output
                if speaker == "Note":
                    output.append(f"[{dialogue}]")
                else:
                    output.append(f"{speaker} {timestamp}")
                    output.append(dialogue)
                output.append("")
    
    return "\n".join(output)
