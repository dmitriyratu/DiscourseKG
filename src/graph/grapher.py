"""
Grapher for assembling and loading data into Neo4j.

This module handles data loading from multiple pipeline stages,
stitching metadata, and coordinating Neo4j ingestion.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json

from src.shared.data_loaders import DataLoader
from src.graph.loader import Neo4jLoader
from src.graph.models import GraphResult, GraphData, GraphContext
from src.shared.pipeline_definitions import PipelineStages, StageResult
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
    
    def load_graph(self, processing_context: GraphContext) -> StageResult:
        """Load data into Neo4j from processing context."""
        # Extract what we need from the processing context
        id = processing_context.id
        file_paths = processing_context.file_paths
        state_metadata = processing_context.state_metadata
        
        logger.debug(f"Starting graph loading for {id}")
        
        # Load and stitch data from multiple stages
        categorization_data = self._load_categorization(file_paths)
        communication_data = self._load_communication(file_paths, state_metadata)
        speaker_data = self._load_speaker(file_paths, state_metadata)
        
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
    
    def _load_categorization(self, file_paths: Dict[str, str]) -> list:
        """Load categorization data (entities)."""
        categorize_path = file_paths.get(PipelineStages.CATEGORIZE.value)
        output = self.data_loader.load(categorize_path)
        data = output.get('data', {})
        return data.get('entities')
    
    def _load_communication(self, file_paths: Dict[str, str], state_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Load communication data by stitching stage outputs with pipeline state metadata."""
        scrape_path = file_paths.get(PipelineStages.SCRAPE.value)
        scrape_output = self.data_loader.load(scrape_path)
        scrape_data = scrape_output.get('data', {})
        scrape_content = scrape_data.get(PipelineStages.SCRAPE.value)
        
        # Use state metadata (scrape stage updates state, not output files)
        combined_metadata = {
            'title': state_metadata.get('title'),
            'content_type': state_metadata.get('content_type', 'unknown'),
            'content_date': state_metadata.get('content_date', 'Unknown'),
            'source_url': state_metadata.get('source_url')
        }

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
            'id': scrape_output.get('id'),
            'title': combined_metadata['title'],
            'content_type': combined_metadata['content_type'],
            'content_date': combined_metadata['content_date'],
            'source_url': combined_metadata['source_url'],
            'full_text': scrape_content,
            'word_count': len(scrape_content.split()) if scrape_content else 0,
            'was_summarized': was_summarized,
            'compression_ratio': compression_ratio
        }
    
    def _load_speaker(self, file_paths: Dict[str, str], state_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Load speaker metadata from pipeline state and speakers.json."""
        speaker_name = state_metadata.get('speaker')

        if not speaker_name:
            raise ValueError("Speaker name missing from state metadata")
        
        speakers_file = Path(config.PROJECT_ROOT) / 'data' / config.ENVIRONMENT / 'speakers.json'
        with open(speakers_file, 'r') as f:
            speakers_data = json.load(f)

        speakers = speakers_data.get('speakers', {})

        speaker_record: Optional[Dict[str, Any]] = None
        if isinstance(speakers, dict):
            if speaker_name in speakers:
                speaker_entry = speakers[speaker_name] or {}
                speaker_record = {'name': speaker_name, **speaker_entry}
            else:
                speaker_record = next(
                    (
                        {'name': key, **value}
                        for key, value in speakers.items()
                        if isinstance(value, dict)
                        and (value.get('name') == speaker_name or value.get('display_name') == speaker_name)
                    ),
                    None
                )
        elif isinstance(speakers, list):
            speaker_record = next(
                (
                    s for s in speakers
                    if isinstance(s, dict)
                    and (s.get('name') == speaker_name or s.get('display_name') == speaker_name)
                ),
                None
            )

        if not speaker_record:
            raise ValueError(f"Speaker '{speaker_name}' not found in speakers.json")

        return speaker_record
    
    def _create_result(self, id: str, stats: Dict[str, int]) -> StageResult:
        """Create StageResult with separated artifact and metadata."""
        graph_data = GraphData(
            nodes_created=stats['nodes_created'],
            relationships_created=stats['relationships_created']
        )
        
        # Build artifact (what gets persisted)
        artifact = GraphResult(
            id=id,
            success=True,
            data=graph_data,
            error_message=None
        )
        
        # No metadata for graph stage currently
        metadata = {}
        
        logger.debug(f"Successfully loaded {id} to Neo4j: {graph_data.nodes_created} nodes, {graph_data.relationships_created} relationships")
        
        return StageResult(artifact=artifact.model_dump(), metadata=metadata)

