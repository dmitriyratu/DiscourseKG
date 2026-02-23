"""Neo4j write operations for graph loading."""

import json
from typing import Any, Dict, List

from src.graph.config import graph_config
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Neo4jLoader:
    """Loads assembled graph data into Neo4j."""

    def __init__(self, driver: Any) -> None:
        self.driver = driver

    def load(self, data: Dict[str, Any]) -> Dict[str, int]:
        """Load data into Neo4j and return statistics."""
        id = data["id"]

        try:
            logger.debug(f"Starting Neo4j load for {id}")

            with self.driver.session(database=graph_config.NEO4J_DATABASE) as session:
                stats = self._load_data(session, data)

            logger.info(f"Successfully loaded {id} to Neo4j: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Neo4j load failed for {id}: {e}")
            raise

    def _load_data(self, session: Any, data: Dict[str, Any]) -> Dict[str, int]:
        """Load all data into Neo4j and return statistics."""
        stats = self._create_stats()

        self._create_constraints(session)

        # Load speaker nodes and DELIVERED relationships for each matched speaker
        for speaker in data["speakers"]:
            speaker_stats = self._load_speaker_node(session, speaker)
            stats["nodes_created"] += speaker_stats["nodes_created"]

            comm_stats = self._load_communication_node(
                session, data["communication"], speaker["name_id"]
            )
            stats["nodes_created"] += comm_stats["nodes_created"]
            stats["relationships_created"] += comm_stats["relationships_created"]

        entity_stats = self._load_entities_and_mentions(
            session, data["id"], data["entities"]
        )
        stats["nodes_created"] += entity_stats["nodes_created"]
        stats["relationships_created"] += entity_stats["relationships_created"]

        return stats

    def _create_stats(self, nodes: int = 0, relationships: int = 0) -> Dict[str, int]:
        """Create stats dict for tracking Neo4j operations."""
        return {"nodes_created": nodes, "relationships_created": relationships}

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

    def _load_communication_node(
        self, session: Any, communication: Dict[str, Any], speaker_name_id: str
    ) -> Dict[str, int]:
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

    def _load_entities_and_mentions(
        self, session: Any, comm_id: str, entities: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Load Entities, Mentions, Subjects and their relationships."""
        nodes_created = 0
        relationships_created = 0

        for entity in entities:
            entity_stats = self._load_entity_node(session, entity)
            nodes_created += entity_stats["nodes_created"]

            for mention in entity.get("mentions", []):
                mention_stats = self._load_mention_and_subjects(
                    session, comm_id, entity["entity_name"], mention
                )
                nodes_created += mention_stats["nodes_created"]
                relationships_created += mention_stats["relationships_created"]

        return self._create_stats(nodes=nodes_created, relationships=relationships_created)

    def _load_entity_node(self, session: Any, entity: Dict[str, Any]) -> Dict[str, int]:
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

    def _load_mention_and_subjects(
        self,
        session: Any,
        comm_id: str,
        entity_name: str,
        mention: Dict[str, Any],
    ) -> Dict[str, int]:
        """Load Mention node with Subjects and create relationships."""
        topic = mention.get("topic", "")

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
        result = session.run(
            mention_query,
            comm_id=comm_id,
            entity_name=entity_name,
            topic=topic,
            context=mention["context"],
            aggregated_sentiment=json.dumps(mention["aggregated_sentiment"]),
        )
        mention_node = result.single()
        if not mention_node:
            return self._create_stats()

        nodes_created = 1
        relationships_created = 2

        for subject in mention.get("subjects", []):
            subject_stats = self._load_subject_node(
                session, mention_node["m"].element_id, subject
            )
            nodes_created += subject_stats["nodes_created"]
            relationships_created += subject_stats["relationships_created"]

        return self._create_stats(nodes=nodes_created, relationships=relationships_created)

    def _load_subject_node(
        self, session: Any, mention_id: str, subject: Dict[str, Any]
    ) -> Dict[str, int]:
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
        result = session.run(
            query,
            mention_id=mention_id,
            subject_name=subject["subject_name"],
            sentiment=subject["sentiment"],
            quotes=subject["quotes"],
        )
        return self._create_stats(nodes=1 if result.single() else 0, relationships=1)
