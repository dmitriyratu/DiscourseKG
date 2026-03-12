"""Neo4j write operations for graph loading."""

import json
from typing import Any, Dict, List

from src.graph.config import graph_config
from src.graph.models import AssembledGraphData, GraphData
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Neo4jLoader:
    """Loads assembled graph data into Neo4j."""

    def __init__(self, driver: Any) -> None:
        self.driver = driver

    def load(self, data: AssembledGraphData) -> GraphData:
        """Load data into Neo4j and return statistics."""
        id = data.id

        try:
            logger.debug(f"Starting Neo4j load for {id}")

            with self.driver.session(database=graph_config.NEO4J_DATABASE) as session:
                stats = self._load_data(session, data)

            logger.info(f"Successfully loaded {id} to Neo4j: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Neo4j load failed for {id}: {e}")
            raise

    def _load_data(self, session: Any, data: AssembledGraphData) -> GraphData:
        """Load all data into Neo4j and return statistics."""
        stats = GraphData()

        self._create_constraints(session)

        comm_dict = data.communication.model_dump()
        for speaker in data.speakers:
            speaker_stats = self._load_speaker_node(session, speaker.model_dump())
            stats.nodes_created += speaker_stats.nodes_created

            comm_stats = self._load_communication_node(
                session, comm_dict, speaker.name_id
            )
            stats.nodes_created += comm_stats.nodes_created
            stats.relationships_created += comm_stats.relationships_created

        entity_stats = self._load_entities_and_topics(
            session, data.id, data.entities
        )
        stats.nodes_created += entity_stats.nodes_created
        stats.relationships_created += entity_stats.relationships_created

        return stats

    def _create_stats(self, nodes: int = 0, relationships: int = 0) -> GraphData:
        """Create stats for tracking Neo4j operations."""
        return GraphData(nodes_created=nodes, relationships_created=relationships)

    def _create_constraints(self, session: Any) -> None:
        """Create Neo4j constraints (idempotent)."""
        constraints = [
            "CREATE CONSTRAINT speaker_name_id IF NOT EXISTS FOR (s:Speaker) REQUIRE s.name_id IS UNIQUE",
            "CREATE CONSTRAINT communication_id IF NOT EXISTS FOR (c:Communication) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.canonical_name IS UNIQUE",
        ]
        for constraint in constraints:
            try:
                session.run(constraint)
            except Exception as e:
                logger.debug(f"Constraint already exists or error: {e}")

    def _load_speaker_node(self, session: Any, speaker: Dict[str, Any]) -> GraphData:
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

    def _load_communication_node(
        self, session: Any, communication: Dict[str, Any], speaker_name_id: str
    ) -> GraphData:
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
        params = {**communication, "speaker_name_id": speaker_name_id}
        result = session.run(query, **params)
        record = result.single()
        return self._create_stats(nodes=1 if record else 0, relationships=1 if record else 0)

    def _load_entities_and_topics(
        self, session: Any, comm_id: str, entities: List[Dict[str, Any]]
    ) -> GraphData:
        """Load Entities, Topics, Claims and their relationships."""
        nodes_created = 0
        relationships_created = 0

        for entity in entities:
            entity_stats = self._load_entity_node(session, entity)
            nodes_created += entity_stats.nodes_created

            for topic in entity["topics"]:
                topic_stats = self._load_topic_and_claims(
                    session, comm_id, entity["entity_name"], topic
                )
                nodes_created += topic_stats.nodes_created
                relationships_created += topic_stats.relationships_created

        return self._create_stats(nodes=nodes_created, relationships=relationships_created)

    def _load_entity_node(self, session: Any, entity: Dict[str, Any]) -> GraphData:
        """Load Entity node."""
        query = """
        MERGE (e:Entity {canonical_name: $entity_name})
        SET e.name = $entity_name,
            e.entity_type = $entity_type
        RETURN e
        """
        result = session.run(
            query,
            entity_name=entity["entity_name"],
            entity_type=entity["entity_type"],
        )
        return self._create_stats(nodes=1 if result.single() else 0)

    def _load_topic_and_claims(
        self,
        session: Any,
        comm_id: str,
        entity_name: str,
        mention: Dict[str, Any],
    ) -> GraphData:
        """Load Topic node with Claims and create relationships."""
        
        topic = mention["topic"]
        speaker = mention["speaker"]
        topic_query = """
        MATCH (c:Communication {id: $comm_id})
        MATCH (e:Entity {canonical_name: $entity_name})
        CREATE (t:Topic {
            name: $topic,
            topic: $topic,
            speaker: $speaker,
            context: $context,
            aggregated_sentiment: $aggregated_sentiment
        })
        CREATE (c)-[:HAS_TOPIC]->(t)
        CREATE (t)-[:REFERS_TO]->(e)
        RETURN t
        """
        result = session.run(
            topic_query,
            comm_id=comm_id,
            entity_name=entity_name,
            topic=topic,
            speaker=speaker,
            context=mention["context"],
            aggregated_sentiment=json.dumps(mention["aggregated_sentiment"]),
        )
        topic_node = result.single()
        if not topic_node:
            return self._create_stats()

        nodes_created = 1
        relationships_created = 2

        for claim in mention["claims"]:
            claim_stats = self._load_claim_node(
                session, topic_node["t"].element_id, claim
            )
            nodes_created += claim_stats.nodes_created
            relationships_created += claim_stats.relationships_created

        return self._create_stats(nodes=nodes_created, relationships=relationships_created)

    def _load_claim_node(
        self, session: Any, topic_id: str, claim: Dict[str, Any]
    ) -> GraphData:
        """Load Claim node and HAS_CLAIM relationship."""
        query = """
        MATCH (t:Topic) WHERE elementId(t) = $topic_id
        CREATE (cl:Claim {
            name: $claim_label,
            subject_name: $claim_label,
            sentiment: $sentiment,
            summary: $summary,
            passages: $passages
        })
        CREATE (t)-[:HAS_CLAIM]->(cl)
        RETURN cl
        """
        result = session.run(
            query,
            topic_id=topic_id,
            claim_label=claim["claim_label"],
            sentiment=claim["sentiment"],
            summary=claim["summary"],
            passages=claim["passages"],
        )
        return self._create_stats(nodes=1 if result.single() else 0, relationships=1)
