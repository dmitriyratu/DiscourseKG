"""
Graph preprocessing for Neo4j ingestion.

This module prepares categorization data for knowledge graph loading,
including sentiment aggregation and other transformations.
"""

from typing import Dict, Any, List
from src.graph.config import graph_config
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class GraphPreprocessor:
    """
    Preprocesses categorization data for Neo4j ingestion.
    Handles sentiment aggregation and other KG-specific transformations.
    """
    
    def __init__(self):
        logger.debug("GraphPreprocessor initialized")
    
    def preprocess_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Preprocess entities for Neo4j loading (in-memory)."""
        try:
            # Apply preprocessing transformations
            entities = self._compute_aggregated_sentiment(entities)
            entities = self._canonicalize_entities(entities)
            entities = self._validate_data(entities)
            
            return entities
            
        except Exception as e:
            logger.error(f"Entity preprocessing failed: {str(e)}")
            raise
    
    def _compute_aggregated_sentiment(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compute aggregated sentiment for each topic mention from its subjects."""
        for entity in entities:
            for mention in entity.get('mentions', []):
                subjects = mention.get('subjects', [])
                
                if not subjects:
                    continue
                
                # Count sentiments
                sentiment_counts = {}
                for subject in subjects:
                    sentiment_value = subject.get('sentiment')
                    if sentiment_value:
                        sentiment_counts[sentiment_value] = sentiment_counts.get(sentiment_value, 0) + 1
                
                # Calculate proportions and create aggregation
                total_subjects = len(subjects)
                mention['aggregated_sentiment'] = {
                    sentiment: {
                        'count': count,
                        'prop': round(count / total_subjects, graph_config.DECIMAL_PRECISION)
                    }
                    for sentiment, count in sentiment_counts.items()
                }
        
        return entities
    
    def _canonicalize_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Canonicalize entity names (future implementation)."""
        # TODO: Implement entity name canonicalization
        # - Remove extra whitespace
        # - Standardize capitalization
        # - Handle common aliases
        return entities
    
    def _validate_data(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate entity data before Neo4j loading."""
        # Basic validation - ensure required fields exist
        for entity in entities:
            if not entity.get('entity_name'):
                raise ValueError(f"Entity missing entity_name: {entity}")
            if not entity.get('entity_type'):
                raise ValueError(f"Entity missing entity_type: {entity}")
            if not entity.get('mentions'):
                raise ValueError(f"Entity has no mentions: {entity['entity_name']}")
        
        return entities

