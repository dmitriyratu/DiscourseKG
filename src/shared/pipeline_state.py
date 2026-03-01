"""Pipeline state management backed by SQLite via Peewee ORM."""

import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from peewee import SqliteDatabase, Model, CharField, IntegerField, FloatField, TextField, CompositeKey

from src.config import config
from src.utils.logging_utils import get_logger
from src.shared.pipeline_definitions import (
    PipelineConfig,
    PipelineStages,
    PipelineStageStatus,
    PipelineState,
    StageMetadata,
    EndpointResponse,
)
from src.shared.models import StageOperationResult
from src.discover.models import DiscoveredArticle, DiscoverStageMetadata

logger = get_logger(__name__)

STAGE_ORDER = [s.value for s in PipelineStages]
_COMPLETION_STATUSES = (PipelineStageStatus.COMPLETED, PipelineStageStatus.FILTERED)
_COMPLETION_STATUS_VALUES = {s.value for s in _COMPLETION_STATUSES}

db = SqliteDatabase(None)


class PipelineStage(Model):
    """One row per article per stage."""

    article_id = CharField()
    stage = CharField()
    status = CharField()
    error_message = TextField(null=True)
    retry_count = IntegerField(default=0)
    completed_at = TextField(null=True)
    processing_time_secs = FloatField(null=True)
    file_path = TextField(null=True)
    metadata = TextField(null=True)
    title = TextField(null=True)
    publication_date = TextField(null=True)
    source_url = TextField(null=True)
    search_url = TextField(null=True)
    run_timestamp = TextField(null=True)
    created_at = TextField(null=True)
    matched_speakers = TextField(null=True)

    class Meta:
        database = db
        table_name = "pipeline_stages"
        primary_key = CompositeKey("article_id", "stage")


class PipelineStateManager:
    """Manages pipeline state tracking via SQLite."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        path = Path(db_path or config.PIPELINE_STATE_DB)
        path.parent.mkdir(parents=True, exist_ok=True)
        db.init(str(path))
        db.execute_sql("PRAGMA journal_mode=WAL")
        db.create_tables([PipelineStage], safe=True)

    def create_state(self, discovered_article: DiscoveredArticle, run_timestamp: str,
                     file_path: Optional[str] = None) -> PipelineState:
        """Create a new pipeline state for a discovered article."""
        now = datetime.now().isoformat()
        meta = DiscoverStageMetadata(
            date_score=discovered_article.date_score,
            date_source=discovered_article.date_source
        )

        PipelineStage.create(
            article_id=discovered_article.id,
            stage=PipelineStages.DISCOVER.value,
            status=PipelineStageStatus.COMPLETED.value,
            completed_at=now,
            file_path=file_path,
            metadata=json.dumps(meta.model_dump()),
            title=discovered_article.title,
            publication_date=discovered_article.publication_date,
            source_url=discovered_article.url,
            search_url=discovered_article.search_url,
            run_timestamp=run_timestamp,
            created_at=now,
        )

        state = self._build_state(discovered_article.id)
        logger.debug(f"Created pipeline state for data point: {discovered_article.id}")
        return state

    def record_stage_result(self, status: PipelineStageStatus, result_data: EndpointResponse,
                            file_path: Optional[str] = None) -> None:
        """Create or update a stage row from endpoint result data."""
        stage = result_data.stage
        output = StageOperationResult.model_validate(result_data.output)
        article_id = output.id

        processing_time = result_data.processing_time_seconds
        custom_metadata = result_data.state_update or {}
        error_message = output.error_message

        now = datetime.now().isoformat()
        completed_at = now if status in _COMPLETION_STATUSES else None
        row_status = status.value
        stored_error = error_message if status == PipelineStageStatus.FAILED else None

        matched_speakers_json = None
        if status == PipelineStageStatus.COMPLETED and (matched := custom_metadata.get("matched_speakers")):
            matched_speakers_json = json.dumps(matched)

        row, created = PipelineStage.get_or_create(
            article_id=article_id,
            stage=stage,
            defaults={
                "status": row_status,
                "error_message": stored_error,
                "retry_count": 1 if status == PipelineStageStatus.FAILED else 0,
                "completed_at": completed_at,
                "processing_time_secs": round(processing_time, 2) if processing_time else None,
                "file_path": file_path,
                "metadata": json.dumps(custom_metadata) if custom_metadata else None,
                "matched_speakers": matched_speakers_json,
            },
        )

        if not created:
            old_meta = json.loads(row.metadata) if row.metadata else {}
            old_meta.update(custom_metadata)
            retry_count = row.retry_count + (1 if status == PipelineStageStatus.FAILED else 0)

            updates = {
                "status": row_status,
                "error_message": stored_error,
                "retry_count": retry_count,
                "metadata": json.dumps(old_meta),
            }
            if completed_at:
                updates["completed_at"] = completed_at
            if processing_time is not None:
                updates["processing_time_secs"] = round(processing_time, 2)
            if file_path:
                updates["file_path"] = file_path
            if matched_speakers_json:
                updates["matched_speakers"] = matched_speakers_json

            PipelineStage.update(**updates).where(
                (PipelineStage.article_id == article_id) & (PipelineStage.stage == stage)
            ).execute()

        if status == PipelineStageStatus.FAILED:
            logger.error(f"Stage {stage} failed for data point: {article_id}")
        elif status == PipelineStageStatus.COMPLETED:
            logger.debug(f"Completed {stage} for data point: {article_id}")

    def get_state_by_source_url(self, source_url: str) -> Optional[PipelineState]:
        """Return state for the given source URL, or None if not found."""
        row = PipelineStage.select(PipelineStage.article_id).where(
            PipelineStage.source_url == source_url
        ).first()
        return self._build_state(row.article_id) if row else None

    def get_all_states(self) -> List[PipelineState]:
        """Return all pipeline state records."""
        article_ids = PipelineStage.select(PipelineStage.article_id).distinct()
        return [s for r in article_ids if (s := self._build_state(r.article_id))]

    def get_states_for_stage(self, stage: PipelineStages) -> List[PipelineState]:
        """Return states whose next_stage matches the given stage."""
        target = stage.value
        return [
            s for aid in PipelineStage.select(PipelineStage.article_id).distinct()
            if (s := self._build_state(aid.article_id)) and s.next_stage == target
        ]

    @staticmethod
    def _stage_metadata_from_row(row: PipelineStage) -> StageMetadata:
        """Build StageMetadata from a PipelineStage DB row."""
        return StageMetadata(
            completed_at=row.completed_at,
            processing_time_seconds=row.processing_time_secs,
            file_path=row.file_path,
            retry_count=row.retry_count,
            error_message=row.error_message,
            metadata=json.loads(row.metadata) if row.metadata else {},
        )

    @staticmethod
    def _article_fields_from_discover(discover: Optional[PipelineStage]) -> Dict[str, Optional[str]]:
        """Extract article-level fields from the discover stage row."""
        if not discover:
            return {"publication_date": None, "title": None, "source_url": None, "search_url": None, "run_timestamp": "", "created_at": ""}
        return {
            "publication_date": discover.publication_date,
            "title": discover.title,
            "source_url": discover.source_url,
            "search_url": discover.search_url,
            "run_timestamp": discover.run_timestamp or "",
            "created_at": discover.created_at or "",
        }

    def _build_state(self, article_id: str) -> Optional[PipelineState]:
        """Reconstruct a PipelineState from stage rows."""
        rows = list(PipelineStage.select().where(PipelineStage.article_id == article_id))
        if not rows:
            return None

        rows_by_stage = {r.stage: r for r in rows}
        discover = rows_by_stage.get(PipelineStages.DISCOVER.value)

        stages: Dict[str, StageMetadata] = {}
        latest_completed: Optional[str] = None
        total_processing = 0.0
        total_retries = 0
        error_message: Optional[str] = None

        for stage_name in STAGE_ORDER:
            row = rows_by_stage.get(stage_name)
            if not row:
                continue

            stages[stage_name] = self._stage_metadata_from_row(row)

            if row.processing_time_secs:
                total_processing += row.processing_time_secs
            total_retries += row.retry_count

            if row.status in _COMPLETION_STATUS_VALUES:
                latest_completed = stage_name

            if row.status == PipelineStageStatus.FAILED.value:
                error_message = row.error_message

        is_filtered = any(r.status == PipelineStageStatus.FILTERED.value for r in rows_by_stage.values())
        next_stage = None if is_filtered else PipelineConfig.get_next_stage(latest_completed) if latest_completed else None

        matched_speakers = {}
        filter_row = rows_by_stage.get(PipelineStages.FILTER.value)
        if filter_row and filter_row.matched_speakers:
            matched_speakers = json.loads(filter_row.matched_speakers)

        article_fields = self._article_fields_from_discover(discover)
        return PipelineState(
            id=article_id,
            matched_speakers=matched_speakers,
            publication_date=article_fields["publication_date"],
            title=article_fields["title"],
            source_url=article_fields["source_url"],
            search_url=article_fields["search_url"],
            run_timestamp=article_fields["run_timestamp"],
            created_at=article_fields["created_at"],
            latest_completed_stage=latest_completed,
            next_stage=next_stage,
            error_message=error_message,
            updated_at=datetime.now().isoformat(),
            processing_time_seconds=round(total_processing, 2) if total_processing else None,
            retry_count=total_retries,
            stages=stages,
        )
