"""
Graph endpoint for loading data into Neo4j.
"""

from typing import Dict, Any
from src.shared.base_endpoint import BaseEndpoint
from src.shared.data_loaders import DataLoader
from src.graph.pipeline import load_to_graph
from src.graph.models import Neo4jLoadResult
from src.pipeline_config import PipelineStages
from src.config import config
from pathlib import Path
import json


            


class GraphEndpoint(BaseEndpoint):
    """Endpoint for loading data into Neo4j."""
    
    def __init__(self):
        super().__init__("GraphEndpoint")
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Neo4j loading process for a single item."""
        try:
            data_loader = DataLoader()
            file_paths = item.get('file_paths', {})
            
            # Load data from multiple stages
            categorization_data = self._load_categorization(data_loader, file_paths)
            communication_data = self._load_communication(data_loader, file_paths)
            speaker_data = self._load_speaker(item.get('speaker'))
            
            # Create processing context
            processing_context = {
                'id': item['id'],
                'speaker': speaker_data,
                'communication': communication_data,
                'categorization_data': categorization_data
            }
            
            # Load to Neo4j
            result = load_to_graph(processing_context)
            
            # Validate result
            load_result = Neo4jLoadResult(**result)
            
            if not load_result.success:
                raise Exception(load_result.error_message or "Neo4j load failed")
            
            self.logger.info(f"Successfully loaded {item['id']} to Neo4j: "
                           f"{load_result.nodes_created} nodes, "
                           f"{load_result.relationships_created} relationships")
            
            # Return simple success response (no data payload, no JSON storage)
            return {
                'id': item['id'],
                'success': True,
                'stage': PipelineStages.GRAPH.value,
                'nodes_created': load_result.nodes_created,
                'relationships_created': load_result.relationships_created
            }
            
        except Exception as e:
            self.logger.error(f"Graph endpoint failed for {item['id']}: {str(e)}")
            raise
    
    def _load_categorization(self, data_loader: DataLoader, file_paths: Dict[str, str]) -> list:
        """Load categorization data (entities)."""
        categorize_path = file_paths.get('categorize')
        if not categorize_path:
            raise ValueError("No categorize file path found")
        
        full_data = data_loader.load(categorize_path)
        entities = full_data.get('data', {}).get('entities')
        
        if not entities:
            raise ValueError("Empty or invalid categorization data")
        
        return entities
    
    def _load_communication(self, data_loader: DataLoader, file_paths: Dict[str, str]) -> Dict[str, Any]:
        """Load communication metadata from discover and scrape stages."""
        # Load from discover stage
        discover_path = file_paths.get('discover')
        if not discover_path:
            raise ValueError("No discover file path found")
        
        discover_data = data_loader.load(discover_path)
        
        # Load from scrape stage
        scrape_path = file_paths.get('scrape')
        if not scrape_path:
            raise ValueError("No scrape file path found")
        
        scrape_data = data_loader.load(scrape_path)
        scrape_content = scrape_data.get('data', {}).get('scrape', '')
        
        # Load from summarize stage
        summarize_path = file_paths.get('summarize')
        summarize_data = data_loader.load(summarize_path) if summarize_path else {}
        
        return {
            'id': discover_data.get('id'),
            'title': discover_data.get('data', {}).get('title', 'Unknown'),
            'content_type': discover_data.get('data', {}).get('content_type', 'unknown'),
            'content_date': discover_data.get('data', {}).get('content_date', 'Unknown'),
            'source_url': discover_data.get('data', {}).get('source_url', ''),
            'full_text': scrape_content,
            'word_count': len(scrape_content.split()) if scrape_content else 0,
            'was_summarized': summarize_data.get('data', {}).get('was_summarized', False),
            'compression_ratio': summarize_data.get('data', {}).get('compression_ratio', 1.0)
        }
    
    def _load_speaker(self, speaker_name: str) -> Dict[str, Any]:
        """Load speaker metadata from speakers.json."""
        try:

            speakers_file = Path(config.PROJECT_ROOT) / 'data' / config.ENVIRONMENT / 'speakers.json'
            
            if not speakers_file.exists():
                self.logger.warning(f"Speakers file not found: {speakers_file}")
                return self._default_speaker(speaker_name)
            
            with open(speakers_file, 'r') as f:
                speakers_data = json.load(f)
            
            # Find speaker by name
            for speaker in speakers_data.get('speakers', []):
                if speaker.get('name') == speaker_name:
                    return speaker
            
            self.logger.warning(f"Speaker {speaker_name} not found in speakers.json")
            return self._default_speaker(speaker_name)
            
        except Exception as e:
            self.logger.warning(f"Failed to load speaker data: {e}")
            return self._default_speaker(speaker_name)
    
    def _default_speaker(self, speaker_name: str) -> Dict[str, Any]:
        """Create default speaker data."""
        return {
            'name': speaker_name,
            'display_name': speaker_name,
            'role': 'Unknown',
            'organization': 'Unknown',
            'industry': 'Unknown',
            'region': 'Unknown'
        }

