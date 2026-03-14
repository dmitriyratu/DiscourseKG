"""Assembles graph data from pipeline stage outputs."""

import json
from typing import Any, Dict, List

from src.categorize.models import CategorizationResult
from src.filter.models import FilterStageMetadata
from src.graph.models import AssembledGraphData, CommunicationData, GraphContext, SpeakerNode
from src.shared.data_loaders import DataLoader
from src.shared.models import ContentType
from src.shared.pipeline_definitions import PipelineStages
from src.scrape.models import ScrapingResult
from src.speakers import SPEAKERS_FILE
from src.speakers.models import SpeakerRegistry
from src.summarize.models import SummarizationResult
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class GraphDataAssembler:
    """Loads and stitches data from pipeline stages for Neo4j ingestion."""

    def assemble(self, context: GraphContext) -> AssembledGraphData:
        """Load from all stages, preprocess, and return Neo4j-ready context."""
        file_paths = {stage: meta.file_path for stage, meta in context.stage_outputs.items()}

        categorization_data = self._load_categorization(file_paths)
        communication_data = self._load_communication(file_paths, context)
        speakers_data = self._load_speakers(context.matched_speakers)
        preprocessed_entities = self._preprocess_entities(categorization_data)

        return AssembledGraphData(
            id=communication_data.id,
            speakers=speakers_data,
            communication=communication_data,
            entities=preprocessed_entities,
        )

    def _load_categorization(self, file_paths: Dict[str, str]) -> List[Dict[str, Any]]:
        """Load categorization data (entities)."""
        categorize_path = file_paths.get(PipelineStages.CATEGORIZE.value)
        output = DataLoader.load(categorize_path)
        categorization_result = CategorizationResult.model_validate(output)
        if not categorization_result.data:
            return []
        return [e.model_dump(mode='json') for e in categorization_result.data.entities]

    def _load_communication(
        self, file_paths: Dict[str, str], context: GraphContext
    ) -> CommunicationData:
        """Load communication data by stitching stage outputs and metadata."""
        scrape_path = file_paths.get(PipelineStages.SCRAPE.value)
        scrape_output = DataLoader.load(scrape_path)
        scraping_result = ScrapingResult.model_validate(scrape_output)
        scrape_content = scraping_result.data.scrape if scraping_result.data else ""
        word_count = scraping_result.data.word_count if scraping_result.data else 0

        title = context.title or "Unknown"
        content_date = context.publication_date or "Unknown"

        filter_stage = context.stage_outputs.get(PipelineStages.FILTER.value)
        filter_metadata_dict = (filter_stage.metadata or {}) if filter_stage else {}
        if filter_metadata_dict:
            filter_metadata = FilterStageMetadata.model_validate(filter_metadata_dict)
            content_type = (filter_metadata.content_type or ContentType.OTHER).value
        else:
            content_type = ContentType.OTHER.value

        summarize_path = file_paths.get(PipelineStages.SUMMARIZE.value)
        was_summarized = False
        compression_ratio = 1.0

        if summarize_path:
            summarize_output = DataLoader.load(summarize_path)
            summarization_result = SummarizationResult.model_validate(summarize_output)
            if summarization_result.data:
                compression_of_original = summarization_result.data.compression_of_original
                compression_ratio = compression_of_original
                was_summarized = compression_of_original < 1.0

        return CommunicationData(
            id=scraping_result.id,
            title=title,
            content_type=content_type,
            content_date=content_date,
            source_url=context.source_url or "",
            full_text=scrape_content,
            word_count=word_count,
            was_summarized=was_summarized,
            compression_ratio=compression_ratio,
        )

    def _load_speakers(self, matched_speakers: List[str]) -> List[SpeakerNode]:
        """Load speaker metadata from speakers.json for each matched speaker (display names)."""
        if not matched_speakers:
            raise ValueError("No matched speakers provided")

        with open(SPEAKERS_FILE) as f:
            registry = SpeakerRegistry(**json.load(f))

        results = []
        for display_name in matched_speakers:
            if display_name not in registry.speakers:
                logger.warning(f"Speaker '{display_name}' not found in speakers.json, skipping")
                continue
            speaker_obj = registry.speakers[display_name]
            industry = getattr(speaker_obj.industry, "value", speaker_obj.industry)
            results.append(SpeakerNode(
                speaker_id=display_name,
                name=display_name,
                display_name=display_name,
                role=speaker_obj.role,
                organization=speaker_obj.organization,
                industry=industry,
                region=speaker_obj.region,
            ))

        if not results:
            raise ValueError(f"None of the matched speakers found in registry: {matched_speakers}")
        return results

    def _preprocess_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Preprocess entities for Neo4j loading."""
        try:
            entities = self._group_claims_by_topic(entities)
            entities = self._validate_entities(entities)
            return entities
        except Exception as e:
            logger.error(f"Entity preprocessing failed: {str(e)}")
            raise

    def _group_claims_by_topic(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group flat claims by (speaker, topic) for Neo4j loading."""
        result = []
        for entity in entities:
            claims = entity["claims"]
            if not claims:
                continue

            topics_map: Dict[tuple, List[Dict]] = {}
            for claim in claims:
                key = (claim["speaker"], claim["topic"])
                topics_map.setdefault(key, []).append(claim)

            topics = []
            for (speaker, topic), group_claims in topics_map.items():
                topics.append({
                    "speaker": speaker,
                    "topic": topic,
                    "topic_summary": group_claims[0]["summary"][:500],
                    "claims": group_claims,
                })
            result.append({**entity, "topics": topics})
        return result

    def _validate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate entity data before Neo4j loading."""
        for entity in entities:
            if not entity.get("entity_name"):
                raise ValueError(f"Entity missing entity_name: {entity}")
            if not entity.get("entity_type"):
                raise ValueError(f"Entity missing entity_type: {entity}")
            if not entity.get("topics"):
                raise ValueError(f"Entity has no topics: {entity['entity_name']}")
        return entities
