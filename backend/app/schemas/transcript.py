from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class SpeakerRole(str, Enum):

    PROJECT_MANAGER = "project_manager"

    CLIENT = "client"


class ConnectionMode(str, Enum):

    CLOUD = "cloud"

    LOCAL_FALLBACK = "local_fallback"


class TranscriptSegment(BaseModel):

    segment_id: UUID

    speaker_role: SpeakerRole

    text: str = Field(
        min_length=1
    )

    start_ts: float = Field(
        ge=0
    )

    end_ts: float = Field(
        ge=0
    )

    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1
    )

    @model_validator(mode="after")
    def validate_timestamps(self):

        if self.end_ts < self.start_ts:

            raise ValueError(
                "end_ts must be greater than or equal to start_ts"
            )

        return self


class Transcript(BaseModel):

    meeting_id: UUID

    project_id: UUID

    connection_mode: ConnectionMode

    format_version: str = "1.0"

    segments: list[TranscriptSegment]

    @model_validator(mode="after")
    def validate_speakers(self):

        speakers = {
            segment.speaker_role
            for segment in self.segments
        }

        invalid = speakers - {
            SpeakerRole.PROJECT_MANAGER,
            SpeakerRole.CLIENT
        }

        if invalid:

            raise ValueError(
                f"Invalid speaker roles: {invalid}"
            )

        return self