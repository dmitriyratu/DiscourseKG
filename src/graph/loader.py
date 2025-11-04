"""
Neo4j loader for knowledge graph ingestion.

This module loads preprocessed data directly into Neo4j,
creating nodes and relationships for the DiscourseKG platform.
"""

from typing import Dict, Any, List
from neo4j import GraphDatabase
from src.graph.config import graph_config
from src.graph.preprocessor import GraphPreprocessor
from src.graph.models import Neo4jLoadResult
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Neo4jLoader:
    """
    Loads preprocessed data into Neo4j knowledge graph.
    Handles connection management, preprocessing, and Cypher execution.
    """
    
    def __init__(self):
        self.driver = None
        self.preprocessor = GraphPreprocessor()
        logger.debug("Neo4jLoader initialized")
    
    def __enter__(self):
        """Context manager entry - establish Neo4j connection."""
        self.driver = GraphDatabase.driver(
            graph_config.NEO4J_URI,
            auth=(graph_config.NEO4J_USER, graph_config.NEO4J_PASSWORD)
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close Neo4j connection."""
        if self.driver:
            self.driver.close()
    
    def load_to_neo4j(self, processing_context: Dict[str, Any]) -> Dict[str, Any]:
        """Load data into Neo4j from processing context."""
        id = processing_context['id']
        
        try:
            logger.debug(f"Starting Neo4j load for {id}")
            
            # Preprocess data in-memory
            preprocessed_data = self._preprocess_data(processing_context)
            
            # Load into Neo4j
            with self.driver.session(database=graph_config.NEO4J_DATABASE) as session:
                stats = self._load_data(session, preprocessed_data)
            
            logger.info(f"Successfully loaded {id} to Neo4j: {stats}")
            
            return self._create_result(id, stats)
            
        except Exception as e:
            logger.error(f"Neo4j load failed for {id}: {str(e)}")
            raise
    
    def _preprocess_data(self, processing_context: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess data before Neo4j loading."""
        return {
            'id': processing_context['id'],
            'speaker': processing_context['speaker'],
            'communication': processing_context['communication'],
            'entities': self.preprocessor.preprocess_entities(
                processing_context['categorization_data']
            )
        }
    
    def _load_data(self, session, data: Dict[str, Any]) -> Dict[str, int]:
        """Load all data into Neo4j and return statistics."""
        stats = {'nodes_created': 0, 'relationships_created': 0}
        
        # Create constraints (idempotent)
        self._create_constraints(session)
        
        # Load Speaker node
        speaker_stats = self._load_speaker(session, data['speaker'])
        stats['nodes_created'] += speaker_stats['nodes_created']
        
        # Load Communication node
        comm_stats = self._load_communication(session, data['communication'], data['speaker']['name'])
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
    
    def _create_constraints(self, session):
        """Create Neo4j constraints (idempotent)."""
        constraints = [
            "CREATE CONSTRAINT speaker_name IF NOT EXISTS FOR (s:Speaker) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT communication_id IF NOT EXISTS FOR (c:Communication) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.canonical_name IS UNIQUE"
        ]
        
        for constraint in constraints:
            try:
                session.run(constraint)
            except Exception as e:
                logger.debug(f"Constraint already exists or error: {e}")
    
    def _load_speaker(self, session, speaker: Dict[str, Any]) -> Dict[str, int]:
        """Load Speaker node."""
        query = """
        MERGE (s:Speaker {name: $name})
        SET s.display_name = $display_name,
            s.role = $role,
            s.organization = $organization,
            s.industry = $industry,
            s.region = $region
        RETURN s
        """
        
        result = session.run(query, **speaker)
        return {'nodes_created': 1 if result.single() else 0}
    
    def _load_communication(self, session, communication: Dict[str, Any], speaker_name: str) -> Dict[str, int]:
        """Load Communication node and DELIVERED relationship."""
        query = """
        MATCH (s:Speaker {name: $speaker_name})
        MERGE (c:Communication {id: $id})
        SET c.title = $title,
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
        
        params = {**communication, 'speaker_name': speaker_name}
        result = session.run(query, **params)
        record = result.single()
        
        return {
            'nodes_created': 1 if record else 0,
            'relationships_created': 1 if record else 0
        }
    
    def _load_entities_and_mentions(self, session, comm_id: str, entities: List[Dict[str, Any]]) -> Dict[str, int]:
        """Load Entities, Mentions, Subjects and their relationships."""
        nodes_created = 0
        relationships_created = 0
        
        for entity in entities:
            # Load Entity node
            entity_stats = self._load_entity(session, entity)
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
        
        return {
            'nodes_created': nodes_created,
            'relationships_created': relationships_created
        }
    
    def _load_entity(self, session, entity: Dict[str, Any]) -> Dict[str, int]:
        """Load Entity node."""
        query = """
        MERGE (e:Entity {canonical_name: $entity_name})
        SET e.entity_type = $entity_type
        RETURN e
        """
        
        result = session.run(query, 
            entity_name=entity['entity_name'],
            entity_type=entity['entity_type']
        )
        
        return {'nodes_created': 1 if result.single() else 0}
    
    def _load_mention_and_subjects(self, session, comm_id: str, entity_name: str, 
                                   mention: Dict[str, Any]) -> Dict[str, int]:
        """Load Mention node with Subjects and create relationships."""
        # Create Mention node with aggregated_sentiment
        mention_query = """
        MATCH (c:Communication {id: $comm_id})
        MATCH (e:Entity {canonical_name: $entity_name})
        CREATE (m:Mention {
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
            topic=mention['topic'],
            context=mention['context'],
            aggregated_sentiment=mention.get('aggregated_sentiment', {})
        )
        
        mention_node = result.single()
        if not mention_node:
            return {'nodes_created': 0, 'relationships_created': 0}
        
        nodes_created = 1
        relationships_created = 2  # HAS_MENTION + REFERS_TO
        
        # Create Subject nodes and relationships
        for subject in mention.get('subjects', []):
            subject_stats = self._load_subject(session, mention_node['m'].element_id, subject)
            nodes_created += subject_stats['nodes_created']
            relationships_created += subject_stats['relationships_created']
        
        return {
            'nodes_created': nodes_created,
            'relationships_created': relationships_created
        }
    
    def _load_subject(self, session, mention_id: str, subject: Dict[str, Any]) -> Dict[str, int]:
        """Load Subject node and HAS_SUBJECT relationship."""
        query = """
        MATCH (m:Mention) WHERE elementId(m) = $mention_id
        CREATE (s:Subject {
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
        
        return {
            'nodes_created': 1 if result.single() else 0,
            'relationships_created': 1
        }
    
    def _create_result(self, id: str, stats: Dict[str, int]) -> Dict[str, Any]:
        """Helper to create Neo4jLoadResult."""
        result = Neo4jLoadResult(
            id=id,
            success=True,
            nodes_created=stats['nodes_created'],
            relationships_created=stats['relationships_created']
        )
        
        logger.debug(f"Successfully loaded {id}: {stats['nodes_created']} nodes, {stats['relationships_created']} relationships")
        return result.model_dump()

