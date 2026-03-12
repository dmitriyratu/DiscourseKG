"""Pipeline state management backed by SQLite via Peewee ORM."""

import json
from pathlib import Path
from datetime import datetime
from typing import Any

from peewee import SqliteDatabase, Model, CharField, IntegerField, FloatField, TextField, CompositeKey

from src.config import config
from src.utils.logging_utils import get_logger
from src.shared.pipeline_definitions import (
    ArticleFields,
    EndpointResponse,
    PipelineConfig,
    PipelineStages,
    PipelineStageStatus,
    PipelineState,
    StageMetadata,
    StageOperationResult,
)
from src.discover.models import DiscoveredArticle

logger = get_logger(__name__)
db = SqliteDatabase(None)


class PipelineStage(Model):
    """One row per article per stage. Article fields denormalized into every row."""

    article_id = CharField()
    stage = CharField(choices=[(s.value, s.value) for s in PipelineStages])
    status = CharField(choices=[(s.value, s.value) for s in PipelineStageStatus])
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

    class Meta:
        database = db
        table_name = "pipeline_stages"
        primary_key = CompositeKey("article_id", "stage")


_OPTIONAL_ROW_FIELDS = frozenset(("completed_at", "processing_time_secs", "file_path"))


class PipelineStateManager:
    """Manages pipeline state tracking via SQLite."""

    STAGE_ORDER = [s.value for s in PipelineStages]
    _COMPLETION_STATUS_VALUES = frozenset(
        (PipelineStageStatus.COMPLETED.value, PipelineStageStatus.FILTERED.value)
    )
    _STAGE_ROW_FIELDS = frozenset(PipelineStage._meta.fields.keys())

    @staticmethod
    def _filter_row_fields(data: dict[str, Any]) -> dict[str, Any]:
        invalid = set(data.keys()) - PipelineStateManager._STAGE_ROW_FIELDS
        if invalid:
            raise ValueError(f"Invalid PipelineStage fields: {invalid}")
        return data

    def __init__(self) -> None:
        path = Path(config.PIPELINE_STATE_DB)
        path.parent.mkdir(parents=True, exist_ok=True)
        db.init(str(path))
        db.create_tables([PipelineStage], safe=True)

    def record_discover_result(
        self, discovered: DiscoveredArticle, run_timestamp: str, file_path: str) -> None:
        """Record discover stage result for a newly discovered article."""
        now = datetime.now().isoformat()
        result_data = EndpointResponse(
            success=True,
            stage=PipelineStages.DISCOVER.value,
            output=StageOperationResult(
                id=discovered.id,
                success=True,
                data=discovered.model_dump(mode='json'),
                error_message=None,
            ).model_dump(mode='json'),
            state_update=None,
        )
        self.record_stage_result(
            status=PipelineStageStatus.COMPLETED,
            result_data=result_data,
            file_path=file_path,
            article_fields=ArticleFields(
                title=discovered.title,
                publication_date=discovered.publication_date,
                source_url=discovered.url,
                search_url=discovered.search_url,
                run_timestamp=run_timestamp,
                created_at=now,
            ),
        )

    def record_stage_result(self, status: PipelineStageStatus, result_data: EndpointResponse,
                            file_path: str | None = None,
                            article_fields: ArticleFields | None = None) -> None:
        """Create or update a stage row from endpoint result data."""
        stage = result_data.stage
        output = StageOperationResult.model_validate(result_data.output)
        article_id = output.id
        now = datetime.now().isoformat()
        completed_at = now if status.value in self._COMPLETION_STATUS_VALUES else None
        stored_error = output.error_message if status == PipelineStageStatus.FAILED else None

        existing_row = PipelineStage.get_or_none(
            (PipelineStage.article_id == article_id) & (PipelineStage.stage == stage)
        )
        row_data = self._build_stage_row_data(
            status, stored_error, completed_at,
            result_data.processing_time_seconds, file_path,
            result_data.state_update or {}, existing_row=existing_row,
        )
        if article_fields:
            row_data.update(article_fields.model_dump())

        filtered = self._filter_row_fields(row_data)
        if existing_row:
            PipelineStage.update(**filtered).where(
                (PipelineStage.article_id == article_id) & (PipelineStage.stage == stage)
            ).execute()
        else:
            PipelineStage.create(article_id=article_id, stage=stage, **filtered)

        if status == PipelineStageStatus.FAILED:
            logger.error(f"Stage {stage} failed for data point: {article_id}")
        elif status == PipelineStageStatus.COMPLETED:
            logger.debug(f"Completed {stage} for data point: {article_id}")

    def _build_stage_row_data(self, status: PipelineStageStatus, stored_error: str | None,
                              completed_at: str | None,
                              processing_time: float | None, file_path: str | None,
                              custom_metadata: dict[str, Any],
                              existing_row: PipelineStage | None = None) -> dict[str, Any]:
        if existing_row:
            meta = json.loads(existing_row.metadata or "{}")
            meta.update(custom_metadata)
            custom_metadata = meta
            retry_count = existing_row.retry_count + (1 if status == PipelineStageStatus.FAILED else 0)
        else:
            retry_count = 1 if status == PipelineStageStatus.FAILED else 0

        data: dict[str, Any] = {
            "status": status.value,
            "error_message": stored_error,
            "retry_count": retry_count,
            "completed_at": completed_at,
            "processing_time_secs": round(processing_time, 2) if processing_time else None,
            "file_path": file_path,
            "metadata": json.dumps(custom_metadata) if custom_metadata else None,
        }
        if existing_row:
            data = {k: v for k, v in data.items() if k not in _OPTIONAL_ROW_FIELDS or v is not None}
        return data

    def get_state_by_source_url(self, source_url: str) -> PipelineState | None:
        """Return state for the given source URL, or None if not found."""
        row = PipelineStage.select(PipelineStage.article_id).where(
            PipelineStage.source_url == source_url
        ).first()
        return self._build_state(row.article_id) if row else None

    def _query_states(self, next_stage: str | None = None) -> list[PipelineState]:
        rows = PipelineStage.select(PipelineStage.article_id).distinct()
        return [
            s for row in rows
            if (s := self._build_state(row.article_id))
            and (next_stage is None or s.next_stage == next_stage)
        ]

    def get_all_states(self) -> list[PipelineState]:
        """Return all pipeline state records."""
        return self._query_states()

    def get_states_for_stage(self, stage: PipelineStages) -> list[PipelineState]:
        """Return states whose next_stage matches the given stage."""
        return self._query_states(stage.value)

    @staticmethod
    def _stage_metadata_from_row(row: PipelineStage) -> StageMetadata:
        """Build StageMetadata from a PipelineStage DB row."""
        return StageMetadata(
            completed_at=row.completed_at,
            processing_time_seconds=row.processing_time_secs,
            file_path=row.file_path,
            retry_count=row.retry_count,
            error_message=row.error_message,
            metadata=json.loads(row.metadata or "{}"),
        )

    @staticmethod
    def _article_fields_from_row(row: PipelineStage) -> ArticleFields:
        """Extract article-level fields from a stage row (denormalized on all rows)."""
        return ArticleFields(
            title=row.title,
            publication_date=row.publication_date,
            source_url=row.source_url,
            search_url=row.search_url,
            run_timestamp=row.run_timestamp,
            created_at=row.created_at,
        )

    def _build_state(self, article_id: str) -> PipelineState | None:
        """Reconstruct a PipelineState from stage rows."""
        rows = list(PipelineStage.select().where(PipelineStage.article_id == article_id))
        if not rows:
            return None

        rows_by_stage = {r.stage: r for r in rows}
        discover = rows_by_stage.get(PipelineStages.DISCOVER.value)

        stages: dict[str, StageMetadata] = {}
        latest_completed: str | None = None
        error_message: str | None = None

        for stage_name in self.STAGE_ORDER:
            row = rows_by_stage.get(stage_name)
            if not row:
                continue

            stages[stage_name] = self._stage_metadata_from_row(row)

            if row.status in self._COMPLETION_STATUS_VALUES:
                latest_completed = stage_name

            if row.status == PipelineStageStatus.FAILED.value:
                error_message = row.error_message

        total_processing = sum(r.processing_time_secs or 0 for r in rows_by_stage.values())
        total_retries = sum(r.retry_count for r in rows_by_stage.values())
        is_filtered = any(r.status == PipelineStageStatus.FILTERED.value for r in rows_by_stage.values())
        next_stage = PipelineConfig.get_next_stage(latest_completed, is_filtered=is_filtered)

        article_row = discover or next(iter(rows_by_stage.values()))
        af = self._article_fields_from_row(article_row)
        af_dict = af.model_dump()
        af_dict["run_timestamp"] = af_dict.get("run_timestamp") or ""
        af_dict["created_at"] = af_dict.get("created_at") or ""
        return PipelineState(
            id=article_id,
            **af_dict,
            latest_completed_stage=latest_completed,
            next_stage=next_stage,
            error_message=error_message,
            updated_at=datetime.now().isoformat(),
            processing_time_seconds=round(total_processing, 2) if total_processing else None,
            retry_count=total_retries,
            stages=stages,
        )
