import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import relationship

from app.database.database import Base


class Meeting(Base):

    __tablename__ = "meetings"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    project_id = Column(
        UUID(as_uuid=True),
        nullable=False
    )

    started_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    ended_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    connection_mode = Column(
        String(50),
        nullable=False,
        default="cloud"
    )

    transcript = relationship(
        "Transcript",
        back_populates="meeting",
        uselist=False,
        cascade="all, delete-orphan"
    )


class Transcript(Base):

    __tablename__ = "transcripts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    meeting_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    format = Column(
        String(20),
        nullable=False,
        default="json"
    )

    storage_ref = Column(
        Text,
        nullable=True
    )

    meeting = relationship(
        "Meeting",
        back_populates="transcript"
    )

    segments = relationship(
        "TranscriptSegment",
        back_populates="transcript",
        cascade="all, delete-orphan",
        order_by="TranscriptSegment.start_ts"
    )


class TranscriptSegment(Base):

    __tablename__ = "transcript_segments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    transcript_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False
    )

    speaker_role = Column(
        String(50),
        nullable=False
    )

    text = Column(
        Text,
        nullable=False
    )

    start_ts = Column(
        Float,
        nullable=False
    )

    end_ts = Column(
        Float,
        nullable=False
    )

    confidence = Column(
        Float,
        nullable=True
    )

    transcript = relationship(
        "Transcript",
        back_populates="segments"
    )