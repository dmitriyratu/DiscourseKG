"""
Grapher for assembling and loading data into Neo4j.

This module handles data loading from multiple pipeline stages,
stitching metadata, and coordinating Neo4j ingestion.
"""

from typing import Dict, Any
from pathlib import Path
import json

from src.shared.data_loaders import DataLoader
from src.graph.loader import Neo4jLoader
from src.graph.models import GraphResult, GraphData
from src.pipeline_config import PipelineStages
from src.config import config
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Grapher:
    """
    Grapher implementation for loading data into Neo4j knowledge graph.
    
    This class handles data loading from multiple pipeline stages,
    stitches metadata, and coordinates Neo4j ingestion.
    """
    
    def __init__(self):
        self.data_loader = DataLoader()
        logger.debug("Grapher initialized")
    
    def load_graph(self, processing_context: Dict[str, Any]) -> Dict[str, Any]:
        """Load data into Neo4j from processing context."""
        # Extract what we need from the processing context
        id = processing_context['id']
        file_paths = processing_context.get('file_paths', {})
        
        try:
            logger.debug(f"Starting graph loading for {id}")
            
            # Load and stitch data from multiple stages
            categorization_data = self._load_categorization(file_paths)
            communication_data = self._load_communication(file_paths)
            speaker_data = self._load_speaker(file_paths)
            
            # Create Neo4j loading context
            neo4j_context = {
                'id': id,
                'speaker': speaker_data,
                'communication': communication_data,
                'categorization_data': categorization_data
            }
            
            # Load to Neo4j
            with Neo4jLoader() as loader:
                stats = loader.load_to_neo4j(neo4j_context)
            
            return self._create_result(id, stats)
            
        except Exception as e:
            logger.error(f"Graph loading failed for {id}: {str(e)}")
            raise
    
    def _load_categorization(self, file_paths: Dict[str, str]) -> list:
        """Load categorization data (entities)."""
        categorize_path = file_paths.get(PipelineStages.CATEGORIZE.value)
        output = self.data_loader.load(categorize_path)
        data = output.get('data', {})
        return data.get('entities')
    
    def _load_communication(self, file_paths: Dict[str, str]) -> Dict[str, Any]:
        """Load communication data by stitching stage outputs with pipeline state metadata."""
        scrape_path = file_paths.get(PipelineStages.SCRAPE.value)
        scrape_output = self.data_loader.load(scrape_path)
        scrape_data = scrape_output.get('data', {})
        scrape_content = scrape_data.get(PipelineStages.SCRAPE.value)
        scrape_metadata = scrape_output.get('metadata', {})

        # Load from summarize stage for compression stats
        summarize_path = file_paths.get(PipelineStages.SUMMARIZE.value)
        was_summarized = False
        compression_ratio = 1.0
        
        if summarize_path:
            summarize_output = self.data_loader.load(summarize_path)
            summarize_data = summarize_output.get('data', {})
            summary_word_count = summarize_data.get('summary_word_count')
            original_word_count = summarize_data.get('original_word_count')
            compression_ratio = summarize_data.get('compression_ratio', 1.0)
            was_summarized = (
                bool(summary_word_count is not None and original_word_count is not None)
                and summary_word_count != original_word_count
            )

        return {
            'id': scrape_output.get('id') or scrape_metadata.get('id'),
            'title': scrape_metadata.get('title'),
            'content_type': scrape_metadata.get('content_type', 'unknown'),
            'content_date': scrape_metadata.get('content_date', 'Unknown'),
            'source_url': scrape_metadata.get('source_url'),
            'full_text': scrape_content,
            'word_count': len(scrape_content.split()) if scrape_content else 0,
            'was_summarized': was_summarized,
            'compression_ratio': compression_ratio
        }
    
    def _load_speaker(self, file_paths: Dict[str, str]) -> Dict[str, Any]:
        """Load speaker metadata from scrape file and speakers.json."""
        scrape_path = file_paths.get(PipelineStages.SCRAPE.value)
        scrape_output = self.data_loader.load(scrape_path)
        scrape_metadata = scrape_output.get('metadata', {})
        speaker_name = scrape_metadata.get('speaker')
        
        speakers_file = Path(config.PROJECT_ROOT) / 'data' / config.ENVIRONMENT / 'speakers.json'
        with open(speakers_file, 'r') as f:
            speakers_data = json.load(f)
        
        return next((s for s in speakers_data.get('speakers', []) if s.get('name') == speaker_name), None)
    
    def _create_result(self, id: str, stats: Dict[str, int]) -> Dict[str, Any]:
        """Create GraphResult from Neo4j statistics."""
        graph_data = GraphData(
            nodes_created=stats['nodes_created'],
            relationships_created=stats['relationships_created']
        )
        
        result = GraphResult(
            id=id,
            success=True,
            data=graph_data,
            metadata={}
        )
        
        logger.debug(f"Successfully loaded {id} to Neo4j: {graph_data.nodes_created} nodes, {graph_data.relationships_created} relationships")
        
        return result.model_dump()

