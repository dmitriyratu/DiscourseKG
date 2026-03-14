"""Neo4j write operations for graph loading."""

from typing import Any, Dict, List

from src.graph.config import graph_config
from src.graph.models import AssembledGraphData, EntityInTopic, GraphLoadStats, TopicGroup
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Neo4jLoader:
    """Loads assembled graph data into Neo4j."""

    def __init__(self, driver: Any) -> None:
        self.driver = driver

    def load(self, data: AssembledGraphData) -> GraphLoadStats:
        """Load data into Neo4j and return statistics."""
        try:
            logger.debug(f"Starting Neo4j load for {data.id}")
            with self.driver.session(database=graph_config.NEO4J_DATABASE) as session:
                stats = self._load_data(session, data)
            logger.info(f"Successfully loaded {data.id} to Neo4j: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Neo4j load failed for {data.id}: {e}")
            raise

    def _load_data(self, session: Any, data: AssembledGraphData) -> GraphLoadStats:
        stats = GraphLoadStats()
        self._create_constraints(session)

        comm_dict = data.communication.model_dump()
        for speaker in data.speakers:
            s = self._load_speaker_node(session, speaker.model_dump())
            stats.nodes_created += s.nodes_created
            c = self._load_communication_node(session, comm_dict, speaker.speaker_id)
            stats.nodes_created += c.nodes_created
            stats.relationships_created += c.relationships_created

        t = self._load_topics(session, data.id, data.topics)
        stats.nodes_created += t.nodes_created
        stats.relationships_created += t.relationships_created
        return stats

    def _create_stats(self, nodes: int = 0, relationships: int = 0) -> GraphLoadStats:
        return GraphLoadStats(nodes_created=nodes, relationships_created=relationships)

    def _create_constraints(self, session: Any) -> None:
        constraints = [
            "CREATE CONSTRAINT speaker_id IF NOT EXISTS FOR (s:Speaker) REQUIRE s.speaker_id IS UNIQUE",
            "CREATE CONSTRAINT communication_id IF NOT EXISTS FOR (c:Communication) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_name IS UNIQUE",
            "CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (t:Topic) REQUIRE t.topic_id IS UNIQUE",
        ]
        for constraint in constraints:
            try:
                session.run(constraint)
            except Exception as e:
                logger.debug(f"Constraint already exists or error: {e}")

    def _load_speaker_node(self, session: Any, speaker: Dict[str, Any]) -> GraphLoadStats:
        query = """
        MERGE (s:Speaker {speaker_id: $speaker_id})
        SET s.name = $name,
            s.role = $role,
            s.organization = $organization,
            s.industry = $industry,
            s.region = $region
        RETURN s
        """
        result = session.run(query, **speaker)
        return self._create_stats(nodes=1 if result.single() else 0)

    def _load_communication_node(
        self, session: Any, communication: Dict[str, Any], speaker_id: str
    ) -> GraphLoadStats:
        query = """
        MATCH (s:Speaker {speaker_id: $speaker_id})
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
        result = session.run(query, **{**communication, "speaker_id": speaker_id})
        record = result.single()
        return self._create_stats(nodes=1 if record else 0, relationships=1 if record else 0)

    def _load_topics(
        self, session: Any, comm_id: str, topics: List[TopicGroup]
    ) -> GraphLoadStats:
        nodes = relationships = 0
        for topic in topics:
            s = self._load_topic_group(session, comm_id, topic)
            nodes += s.nodes_created
            relationships += s.relationships_created
        return self._create_stats(nodes=nodes, relationships=relationships)

    def _load_topic_group(
        self, session: Any, comm_id: str, topic: TopicGroup
    ) -> GraphLoadStats:
        """MERGE Topic node per (comm, speaker, topic), link to Communication."""
        query = """
        MATCH (c:Communication {id: $comm_id})
        MERGE (t:Topic {topic_id: $topic_id})
        SET t.name = $topic,
            t.topic = $topic,
            t.speaker = $speaker,
            t.topic_summary = $topic_summary
        MERGE (c)-[:HAS_TOPIC]->(t)
        RETURN t
        """
        result = session.run(
            query,
            comm_id=comm_id,
            topic_id=topic.topic_id,
            topic=topic.topic,
            speaker=topic.speaker,
            topic_summary=topic.topic_summary,
        )
        if not result.single():
            return self._create_stats()

        nodes_created = 1
        relationships_created = 1

        for entity in topic.entities:
            s = self._load_entity_in_topic(session, topic.topic_id, entity)
            nodes_created += s.nodes_created
            relationships_created += s.relationships_created

        return self._create_stats(nodes=nodes_created, relationships=relationships_created)

    def _load_entity_in_topic(
        self, session: Any, topic_id: str, entity: EntityInTopic
    ) -> GraphLoadStats:
        """MERGE global Entity node, link to Topic, then load claims on Entity."""
        query = """
        MATCH (t:Topic {topic_id: $topic_id})
        MERGE (e:Entity {entity_name: $entity_name})
        SET e.name = $entity_name,
            e.entity_type = $entity_type
        MERGE (t)-[:HAS_ENTITY]->(e)
        RETURN e
        """
        result = session.run(
            query,
            topic_id=topic_id,
            entity_name=entity.entity_name,
            entity_type=entity.entity_type,
        )
        if not result.single():
            return self._create_stats()

        nodes_created = 1
        relationships_created = 1

        for claim in entity.claims:
            s = self._load_claim_node(session, entity.entity_name, claim)
            nodes_created += s.nodes_created
            relationships_created += s.relationships_created

        return self._create_stats(nodes=nodes_created, relationships=relationships_created)

    def _load_claim_node(
        self, session: Any, entity_name: str, claim: Dict[str, Any]
    ) -> GraphLoadStats:
        """Create Claim node attached to Entity."""
        query = """
        MATCH (e:Entity {entity_name: $entity_name})
        CREATE (cl:Claim {
            name: $claim_label,
            speaker: $speaker,
            topic: $topic,
            sentiment: $sentiment,
            summary: $summary,
            passages: $passages
        })
        CREATE (e)-[:HAS_CLAIM]->(cl)
        RETURN cl
        """
        result = session.run(
            query,
            entity_name=entity_name,
            claim_label=claim["claim_label"],
            speaker=claim["speaker"],
            topic=claim["topic"],
            sentiment=claim["sentiment"],
            summary=claim["summary"],
            passages=claim["passages"],
        )
        return self._create_stats(nodes=1 if result.single() else 0, relationships=1)
