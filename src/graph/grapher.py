"""
Grapher for assembling and loading data into Neo4j.

This module handles data loading from multiple pipeline stages,
stitching metadata, and coordinating Neo4j ingestion.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import json
from neo4j import GraphDatabase

from src.shared.data_loaders import DataLoader
from src.graph.models import GraphResult, GraphData, GraphContext
from src.speakers.models import SpeakerRegistry
from src.shared.pipeline_definitions import PipelineStages, StageResult
from src.shared.models import ContentType, StageOperationResult
from src.categorize.models import CategorizationResult
from src.scrape.models import ScrapingResult
from src.summarize.models import SummarizationResult
from src.categorize.models import CategorizeStageMetadata
from src.graph.config import graph_config
from src.config import config
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Grapher:
    """
    Grapher implementation for loading data into Neo4j knowledge graph.
    
    Handles data loading, preprocessing, and Neo4j ingestion.
    """
    
    def __init__(self) -> None:
        self.data_loader = DataLoader()
        self.driver: Any = None
        logger.debug("Grapher initialized")

    def __enter__(self) -> "Grapher":
        """Context manager entry - establish Neo4j connection."""
        self.driver = GraphDatabase.driver(
            graph_config.NEO4J_URI,
            auth=(graph_config.NEO4J_USER, graph_config.NEO4J_PASSWORD)
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - close Neo4j connection."""
        if self.driver:
            self.driver.close()
    
    def load_graph(self, processing_context: GraphContext) -> StageResult:
        """Load data into Neo4j from processing context."""
        id = processing_context.id
        # Convert stages to file_paths dict for data loading
        file_paths = {stage: meta.get('file_path') for stage, meta in processing_context.stages.items()}
        speaker = processing_context.speaker
        
        logger.debug(f"Starting graph loading for {id}")
        
        # Load and stitch data from multiple stages
        categorization_data = self._load_categorization(file_paths)
        communication_data = self._load_communication(file_paths, processing_context.stages, processing_context.title, processing_context.publication_date)
        speaker_data = self._load_speaker(speaker)
        
        # Preprocess entities
        preprocessed_entities = self._preprocess_entities(categorization_data)
        
        # Create Neo4j loading context
        neo4j_context = {
            'id': id,
            'speaker': speaker_data,
            'communication': communication_data,
            'entities': preprocessed_entities
        }
        
        # Load to Neo4j
        stats = self._load_to_neo4j(neo4j_context)
        
        return self._create_result(id, stats)
    
    # ========================
    # Data Loading Methods
    # ========================
    
    def _load_categorization(self, file_paths: Dict[str, str]) -> List[Dict[str, Any]]:
        """Load categorization data (entities)."""
        categorize_path = file_paths.get(PipelineStages.CATEGORIZE.value)
        output = self.data_loader.load(categorize_path)
        categorization_result = CategorizationResult.model_validate(output)
        return categorization_result.data.entities if categorization_result.data else []
    
    def _load_communication(self, file_paths: Dict[str, str], stages: Dict[str, Any], title: Optional[str] = None, publication_date: Optional[str] = None) -> Dict[str, Any]:
        """Load communication data by stitching stage outputs and metadata."""
        scrape_path = file_paths.get(PipelineStages.SCRAPE.value)
        scrape_output = self.data_loader.load(scrape_path)
        scraping_result = ScrapingResult.model_validate(scrape_output)
        scrape_content = scraping_result.data.scrape if scraping_result.data else ''

        # Get title and publication_date from top-level state
        title = title or 'Unknown'
        content_date = publication_date or 'Unknown'
        
        # Get content_type from categorize stage metadata (if available)
        categorize_stage = stages.get(PipelineStages.CATEGORIZE.value, {})
        categorize_metadata_dict = categorize_stage.get('metadata', {}) if isinstance(categorize_stage, dict) else {}
        if categorize_metadata_dict:
            categorize_metadata = CategorizeStageMetadata.model_validate(categorize_metadata_dict)
            content_type = categorize_metadata.content_type or ContentType.UNKNOWN.value
        else:
            content_type = ContentType.UNKNOWN.value

        # Load from summarize stage for compression stats
        summarize_path = file_paths.get(PipelineStages.SUMMARIZE.value)
        was_summarized = False
        compression_ratio = 1.0
        
        if summarize_path:
            summarize_output = self.data_loader.load(summarize_path)
            summarization_result = SummarizationResult.model_validate(summarize_output)
            if summarization_result.data:
                summary_word_count = summarization_result.data.summary_word_count
                original_word_count = summarization_result.data.original_word_count
                compression_ratio = summarization_result.data.compression_ratio
                was_summarized = (
                    summary_word_count is not None 
                    and original_word_count is not None
                    and summary_word_count != original_word_count
                )

        return {
            'id': scraping_result.id,
            'title': title,
            'content_type': content_type,
            'content_date': content_date,
            'full_text': scrape_content,
            'word_count': len(scrape_content.split()) if scrape_content else 0,
            'was_summarized': was_summarized,
            'compression_ratio': compression_ratio
        }
    
    def _load_speaker(self, speaker_name: str) -> Dict[str, Any]:
        """Load speaker metadata from speakers.json."""
        if not speaker_name:
            raise ValueError("Speaker name is required")
        
        # Load and validate speakers.json with Pydantic schema
        speakers_file = Path(config.PROJECT_ROOT) / 'data' / config.ENVIRONMENT / 'speakers.json'
        with open(speakers_file, 'r') as f:
            speakers_data = json.load(f)
        
        # Validate against schema
        speakers_registry = SpeakerRegistry(**speakers_data)
        
        speaker_obj = speakers_registry.speakers[speaker_name]
        
        return {
            'name_id': speaker_name,
            'name': speaker_obj.display_name,
            'display_name': speaker_obj.display_name,
            'role': speaker_obj.role,
            'organization': speaker_obj.organization,
            'industry': speaker_obj.industry,
            'region': speaker_obj.region
        }
    
    # ========================
    # Preprocessing Methods
    # ========================
    
    def _preprocess_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Preprocess entities for Neo4j loading."""
        try:
            entities = self._compute_aggregated_sentiment(entities)
            entities = self._validate_entities(entities)
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
    
    def _validate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate entity data before Neo4j loading."""
        for entity in entities:
            if not entity.get('entity_name'):
                raise ValueError(f"Entity missing entity_name: {entity}")
            if not entity.get('entity_type'):
                raise ValueError(f"Entity missing entity_type: {entity}")
            if not entity.get('mentions'):
                raise ValueError(f"Entity has no mentions: {entity['entity_name']}")
        
        return entities
    
    # ========================
    # Neo4j Loading Methods
    # ========================
    
    def _create_stats(self, nodes: int = 0, relationships: int = 0) -> Dict[str, int]:
        """Create stats dict for tracking Neo4j operations."""
        return {'nodes_created': nodes, 'relationships_created': relationships}
    
    def _load_to_neo4j(self, data: Dict[str, Any]) -> Dict[str, int]:
        """Load data into Neo4j and return statistics."""
        id = data['id']
        
        try:
            logger.debug(f"Starting Neo4j load for {id}")
            
            with self.driver.session(database=graph_config.NEO4J_DATABASE) as session:
                stats = self._load_data(session, data)
            
            logger.info(f"Successfully loaded {id} to Neo4j: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Neo4j load failed for {id}: {str(e)}")
            raise
    
    def _load_data(self, session: Any, data: Dict[str, Any]) -> Dict[str, int]:
        """Load all data into Neo4j and return statistics."""
        stats = self._create_stats()
        
        # Create constraints (idempotent)
        self._create_constraints(session)
        
        # Load Speaker node
        speaker_stats = self._load_speaker_node(session, data['speaker'])
        stats['nodes_created'] += speaker_stats['nodes_created']
        
        # Load Communication node
        comm_stats = self._load_communication_node(session, data['communication'], data['speaker']['name_id'])
        stats['nodes_created'] += comm_stats['nodes_created']
        stats['relationships_created'] += comm_stats['relationships_created']
        
        # Load Entities, Mentions, and Subjects
        entity_stats = self._load_entities_and_mentions(
            session, 
            data['id'], 
            data['entities']
        )
        stats['nodes_created'] += entity_stats['nodes_created']
        stats['relationships_created'] += entity_stats['relationships_created']
        
        return stats
    
    def _create_constraints(self, session: Any) -> None:
        """Create Neo4j constraints (idempotent)."""
        constraints = [
            "CREATE CONSTRAINT speaker_name_id IF NOT EXISTS FOR (s:Speaker) REQUIRE s.name_id IS UNIQUE",
            "CREATE CONSTRAINT communication_id IF NOT EXISTS FOR (c:Communication) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.canonical_name IS UNIQUE"
        ]
        
        for constraint in constraints:
            try:
                session.run(constraint)
            except Exception as e:
                logger.debug(f"Constraint already exists or error: {e}")
    
    def _load_speaker_node(self, session: Any, speaker: Dict[str, Any]) -> Dict[str, int]:
        """Load Speaker node."""
        query = """
        MERGE (s:Speaker {name_id: $name_id})
        SET s.name = $name,
            s.display_name = $display_name,
            s.role = $role,
            s.organization = $organization,
            s.industry = $industry,
            s.region = $region
        RETURN s
        """
        
        result = session.run(query, **speaker)
        return self._create_stats(nodes=1 if result.single() else 0)
    
    def _load_communication_node(self, session: Any, communication: Dict[str, Any], speaker_name_id: str) -> Dict[str, int]:
        """Load Communication node and DELIVERED relationship."""
        query = """
        MATCH (s:Speaker {name_id: $speaker_name_id})
        MERGE (c:Communication {id: $id})
        SET c.name = $title,
            c.title = $title,
            c.content_type = $content_type,
            c.content_date = $content_date,
            c.source_url = $source_url,
            c.full_text = $full_text,
            c.word_count = $word_count,
            c.was_summarized = $was_summarized,
            c.compression_ratio = $compression_ratio
        MERGE (s)-[r:DELIVERED]->(c)
        RETURN c, r
        """
        
        params = {**communication, 'speaker_name_id': speaker_name_id}
        result = session.run(query, **params)
        record = result.single()
        
        return self._create_stats(nodes=1 if record else 0, relationships=1 if record else 0)
    
    def _load_entities_and_mentions(self, session: Any, comm_id: str, entities: List[Dict[str, Any]]) -> Dict[str, int]:
        """Load Entities, Mentions, Subjects and their relationships."""
        nodes_created = 0
        relationships_created = 0
        
        for entity in entities:
            # Load Entity node
            entity_stats = self._load_entity_node(session, entity)
            nodes_created += entity_stats['nodes_created']
            
            # Load Mentions and Subjects for this entity
            for mention in entity.get('mentions', []):
                mention_stats = self._load_mention_and_subjects(
                    session,
                    comm_id,
                    entity['entity_name'],
                    mention
                )
                nodes_created += mention_stats['nodes_created']
                relationships_created += mention_stats['relationships_created']
        
        return self._create_stats(nodes=nodes_created, relationships=relationships_created)
    
    def _load_entity_node(self, session: Any, entity: Dict[str, Any]) -> Dict[str, int]:
        """Load Entity node."""
        query = """
        MERGE (e:Entity {canonical_name: $entity_name})
        SET e.name = $entity_name,
            e.entity_type = $entity_type
        RETURN e
        """
        
        result = session.run(query, 
            entity_name=entity['entity_name'],
            entity_type=entity['entity_type']
        )
        
        return self._create_stats(nodes=1 if result.single() else 0)
    
    def _load_mention_and_subjects(self, session: Any, comm_id: str, entity_name: str,
                                   mention: Dict[str, Any]) -> Dict[str, int]:
        """Load Mention node with Subjects and create relationships."""
        topic = mention.get('topic', '')
        
        # Create Mention node with aggregated_sentiment
        mention_query = """
        MATCH (c:Communication {id: $comm_id})
        MATCH (e:Entity {canonical_name: $entity_name})
        CREATE (m:Mention {
            name: $topic,
            topic: $topic,
            context: $context,
            aggregated_sentiment: $aggregated_sentiment
        })
        CREATE (c)-[:HAS_MENTION]->(m)
        CREATE (m)-[:REFERS_TO]->(e)
        RETURN m
        """
        
        result = session.run(mention_query,
            comm_id=comm_id,
            entity_name=entity_name,
            topic=topic,
            context=mention['context'],
            aggregated_sentiment=json.dumps(mention['aggregated_sentiment'])
        )
        
        mention_node = result.single()
        if not mention_node:
            return self._create_stats()
        
        nodes_created = 1
        relationships_created = 2  # HAS_MENTION + REFERS_TO
        
        # Create Subject nodes and relationships
        for subject in mention.get('subjects', []):
            subject_stats = self._load_subject_node(session, mention_node['m'].element_id, subject)
            nodes_created += subject_stats['nodes_created']
            relationships_created += subject_stats['relationships_created']
        
        return self._create_stats(nodes=nodes_created, relationships=relationships_created)
    
    def _load_subject_node(self, session: Any, mention_id: str, subject: Dict[str, Any]) -> Dict[str, int]:
        """Load Subject node and HAS_SUBJECT relationship."""
        query = """
        MATCH (m:Mention) WHERE elementId(m) = $mention_id
        CREATE (s:Subject {
            name: $subject_name,
            subject_name: $subject_name,
            sentiment: $sentiment,
            quotes: $quotes
        })
        CREATE (m)-[:HAS_SUBJECT]->(s)
        RETURN s
        """
        
        result = session.run(query,
            mention_id=mention_id,
            subject_name=subject['subject_name'],
            sentiment=subject['sentiment'],
            quotes=subject['quotes']
        )
        
        return self._create_stats(nodes=1 if result.single() else 0, relationships=1)
    
    # ========================
    # Result Creation
    # ========================
    
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
