import json
import os
from typing import Dict, List, Optional, Any
import openai
from openai import OpenAI
import sys

from src.config import config


class ContentCategorizer:
    """
    Categorizes content to extract categories, entities, and direct quotes.
    
    This class handles the categorization of speech/communication data for the
    knowledge graph platform, creating a hierarchical structure of categories
    with entities and supporting quotes.
    """
    
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = config.OPENAI_MODEL
    
    def categorize_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Categorize content from a JSON data structure.
        
        Args:
            content_data: Dictionary containing content to categorize. Expected keys:
                - 'transcript': The main text content
                - 'title': Title of the content
                - 'speakers': List of speakers
                - 'date': Date of the content
                - Other metadata fields
        
        Returns:
            Dictionary containing categorization results with topics, entities, and relationships
        """
        transcript = content_data.get('transcript', '')
        title = content_data.get('title', '')
        speakers = content_data.get('speakers', [])
        date = content_data.get('date', '')
        
        if not transcript:
            raise ValueError("No transcript found in content data")
        
        # Create the prompt for categorization
        prompt = self._create_categorization_prompt(transcript, title, speakers, date)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert content analyst specializing in political and business communications. Extract structured information from text content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=config.OPENAI_TEMPERATURE,
                max_tokens=config.OPENAI_MAX_TOKENS
            )
            
            # Parse the response
            categorization_result = self._parse_categorization_response(response.choices[0].message.content)
            
            # Add metadata
            categorization_result['metadata'] = {
                'model_used': self.model,
                'content_id': content_data.get('id', ''),
                'categorization_date': date,
                'speakers': speakers
            }
            
            return categorization_result
            
        except Exception as e:
            raise Exception(f"OpenAI categorization failed: {str(e)}")
    
    def _create_categorization_prompt(self, transcript: str, title: str, speakers: List[str], date: str) -> str:
        
        prompt = f"""
Analyze the following speech and extract categories with entities and direct quotes:

TITLE: {title}
SPEAKERS: {', '.join(speakers)}
DATE: {date}
CONTENT: {transcript[:config.MAX_TRANSCRIPT_LENGTH]}

Extract the main categories discussed, identify entities within each category, and provide direct quotes about each entity.

Return JSON with this structure:
{{
    "categories": [
        {{
            "category": "Category Name (e.g., Immigration Policy, Economic Policy, Foreign Relations)",
            "entities": [
                {{
                    "entity": "Entity Name (person, organization, country, etc.)",
                    "quotes": [
                        "Direct quote about this entity",
                        "Another direct quote about this entity"
                    ]
                }}
            ]
        }}
    ]
}}

Guidelines:
- Identify 3-7 main categories from the speech
- For each category, list the key entities mentioned
- Provide 1-3 direct quotes for each entity (exact quotes from the speech)
- Keep quotes concise (1-2 sentences max)
- Focus on substantive content, not filler words

Return only valid JSON, no additional text.
"""
        return prompt
    
    def _parse_categorization_response(self, response_text: str) -> Dict[str, Any]:
        try:
            # Clean the response text (remove any markdown formatting)
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse OpenAI response as JSON: {str(e)}")
    
    def categorize_batch(self, content_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for i, content in enumerate(content_list):
            try:
                result = self.categorize_content(content)
                results.append(result)
                print(f"Processed item {i+1}/{len(content_list)}")
            except Exception as e:
                print(f"Failed to process item {i+1}: {str(e)}")
                results.append({"error": str(e), "content_id": content.get('id', '')})
        
        return results


def categorize_speech_file(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to categorize a single speech file.
    
    Args:
        file_path: Path to the JSON file containing speech data
    
    Returns:
        Categorization results with categories, entities, and quotes
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content_data = json.load(f)
    
    categorizer = ContentCategorizer()
    return categorizer.categorize_content(content_data)

