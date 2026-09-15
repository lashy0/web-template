from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class BatchKeyGenerationStatus(StrEnum):
    CREATING = "CREATING"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"
    CANCELLING = "CANCELLING"


BATCH_KEY_GENERATION_STATUS_DB_TYPE = Enum(
    BatchKeyGenerationStatus,
    name="batch_key_generation_job_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum_type: [status.value for status in enum_type],
)


class BatchKeyGenerationJob(Base):
    """The durable, one-to-one preparation request for a batch."""

    __tablename__ = "batch_key_generation_jobs"

    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[BatchKeyGenerationStatus] = mapped_column(
        BATCH_KEY_GENERATION_STATUS_DB_TYPE,
        nullable=False,
        default=BatchKeyGenerationStatus.CREATING,
        server_default=BatchKeyGenerationStatus.CREATING.value,
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="batch_key_generation_job_progress_range",
        ),
        Index("ix_batch_key_generation_jobs_status", status),
    )
