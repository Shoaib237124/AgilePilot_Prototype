import json
import mimetypes
import uuid
from pathlib import Path
import requests
from sqlalchemy.orm import Session

from app.config import (
    DEEPGRAM_API_KEY,
    TRANSCRIPT_DIR
)
from app.database.models import (
    Meeting,
    Transcript as TranscriptModel,
    TranscriptSegment as TranscriptSegmentModel
)
from app.schemas.transcript import (
    Transcript,
    TranscriptSegment,
    SpeakerRole,
    ConnectionMode
)


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================

class DeepgramError(Exception):
    pass


class TranscriptPipelineError(Exception):
    pass


# ============================================================
# DEEPGRAM CLIENT
# ============================================================

class DeepgramClient:

    BASE_URL = "https://api.deepgram.com/v1/listen"

    def __init__(self):
        self.api_key = DEEPGRAM_API_KEY
        if not self.api_key:
            raise DeepgramError("DEEPGRAM_API_KEY is not configured.")

    def transcribe_file(self, audio_path: str) -> dict:
        path = Path(audio_path)

        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        if not path.is_file():
            raise ValueError(f"Audio path is not a file: {path}")

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type is None:
            mime_type = "audio/wav"

        # Deepgram REST parameters
        params = {
            "model": "nova-3",
            "language": "en",
            "smart_format": "true",
            "diarize": "true",
            "utterances": "true",
            "punctuate": "true"
        }

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": mime_type
        }

        with open(path, "rb") as audio_file:
            audio_data = audio_file.read()

        try:
            response = requests.post(
                self.BASE_URL,
                params=params,
                headers=headers,
                data=audio_data,
                timeout=600
            )
        except requests.RequestException as exc:
            raise DeepgramError(f"Deepgram request failed: {exc}") from exc

        if not response.ok:
            raise DeepgramError(
                f"Deepgram API returned {response.status_code}: {response.text}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise DeepgramError("Deepgram returned invalid JSON.") from exc


# ============================================================
# TRANSCRIPT NORMALIZER
# ============================================================

class TranscriptNormalizer:

    def __init__(self):
        self.speaker_mapping = {
            0: SpeakerRole.PROJECT_MANAGER,
            1: SpeakerRole.CLIENT
        }

    def extract_utterances_or_words(self, raw_response: dict) -> tuple[list, bool]:
        """
        Extracts utterances if available. If utterances are empty or missing,
        falls back to extracting the word array.
        Returns a tuple: (data_list, is_utterances_boolean)
        """
        try:
            channels = raw_response["results"]["channels"]
        except KeyError as exc:
            raise TranscriptPipelineError(
                "Invalid Deepgram response: results.channels not found."
            ) from exc

        if not channels:
            raise TranscriptPipelineError("Deepgram returned no channels.")

        alternatives = channels[0].get("alternatives", [])
        if not alternatives:
            raise TranscriptPipelineError("Deepgram returned no alternatives.")

        alternative = alternatives[0]
        utterances = alternative.get("utterances", [])

        # Standard path: utterances exist
        if utterances:
            return utterances, True

        # Fallback path: parse word tokens directly
        words = alternative.get("words", [])
        if words:
            return words, False

        raise TranscriptPipelineError(
            "Deepgram returned no speech, words, or utterances."
        )

    def validate_speakers(self, utterances: list):
        speaker_ids = {
            utt.get("speaker")
            for utt in utterances
            if utt.get("speaker") is not None
        }

        if speaker_ids and not speaker_ids.issubset({0, 1}):
            detected = sorted(speaker_ids)
            raise TranscriptPipelineError(
                f"Expected speaker IDs {{0, 1}}. Detected speakers: {detected}"
            )

    def _build_segments_from_words(self, words: list) -> list[TranscriptSegment]:
        segments = []
        current_speaker = None
        current_text = []
        start_ts = 0.0
        end_ts = 0.0

        for word_info in words:
            speaker_id = word_info.get("speaker", 0)
            word_text = word_info.get("word", "").strip()
            word_start = float(word_info.get("start", 0.0))
            word_end = float(word_info.get("end", word_start))

            if not word_text:
                continue

            if current_speaker is None:
                current_speaker = speaker_id
                start_ts = word_start

            if speaker_id != current_speaker:
                role = self.speaker_mapping.get(current_speaker, SpeakerRole.PROJECT_MANAGER)
                segments.append(
                    TranscriptSegment(
                        segment_id=uuid.uuid4(),
                        speaker_role=role,
                        text=" ".join(current_text),
                        start_ts=start_ts,
                        end_ts=end_ts,
                        confidence=0.95
                    )
                )
                current_speaker = speaker_id
                current_text = [word_text]
                start_ts = word_start
            else:
                current_text.append(word_text)
                end_ts = word_end

        if current_text:
            role = self.speaker_mapping.get(current_speaker, SpeakerRole.PROJECT_MANAGER)
            segments.append(
                TranscriptSegment(
                    segment_id=uuid.uuid4(),
                    speaker_role=role,
                    text=" ".join(current_text),
                    start_ts=start_ts,
                    end_ts=end_ts,
                    confidence=0.95
                )
            )

        return segments

    def normalize(
        self,
        raw_response: dict,
        meeting_id: uuid.UUID,
        project_id: uuid.UUID,
        connection_mode: ConnectionMode = ConnectionMode.CLOUD
    ) -> Transcript:

        data_list, is_utterances = self.extract_utterances_or_words(raw_response)

        if is_utterances:
            self.validate_speakers(data_list)
            segments = []

            for utterance in data_list:
                speaker_id = utterance.get("speaker", 0)
                role = self.speaker_mapping.get(speaker_id, SpeakerRole.PROJECT_MANAGER)

                text = utterance.get("transcript", "").strip()
                if not text:
                    continue

                start = float(utterance.get("start", 0.0))
                end = float(utterance.get("end", start))
                confidence = utterance.get("confidence")
                if confidence is not None:
                    confidence = float(confidence)

                segment = TranscriptSegment(
                    segment_id=uuid.uuid4(),
                    speaker_role=role,
                    text=text,
                    start_ts=start,
                    end_ts=end,
                    confidence=confidence
                )
                segments.append(segment)
        else:
            # Reconstruct utterances from raw word blocks
            segments = self._build_segments_from_words(data_list)

        if not segments:
            raise TranscriptPipelineError("No valid transcript segments could be processed.")

        return Transcript(
            meeting_id=meeting_id,
            project_id=project_id,
            connection_mode=connection_mode,
            format_version="1.0",
            segments=segments
        )


# ============================================================
# TRANSCRIPT PIPELINE
# ============================================================

class TranscriptPipeline:

    def __init__(self):
        self.deepgram = DeepgramClient()
        self.normalizer = TranscriptNormalizer()

    def save_json(self, transcript: Transcript) -> Path:
        output_dir = Path(TRANSCRIPT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{transcript.meeting_id}.json"

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(
                transcript.model_dump(mode="json"),
                file,
                indent=2,
                ensure_ascii=False
            )

        return output_path

    def save_to_database(
        self,
        db: Session,
        transcript: Transcript,
        storage_ref: str
    ):
        meeting = db.query(Meeting).filter(
            Meeting.id == transcript.meeting_id
        ).first()

        if not meeting:
            raise TranscriptPipelineError(
                f"Meeting does not exist for ID {transcript.meeting_id}"
            )

        existing = db.query(TranscriptModel).filter(
            TranscriptModel.meeting_id == transcript.meeting_id
        ).first()

        if existing:
            raise TranscriptPipelineError(
                f"A transcript already exists for meeting {transcript.meeting_id}"
            )

        transcript_record = TranscriptModel(
            id=uuid.uuid4(),
            meeting_id=transcript.meeting_id,
            format="json",
            storage_ref=storage_ref
        )

        db.add(transcript_record)
        db.flush()

        for segment in transcript.segments:
            segment_record = TranscriptSegmentModel(
                id=segment.segment_id,
                transcript_id=transcript_record.id,
                speaker_role=segment.speaker_role.value,
                text=segment.text,
                start_ts=segment.start_ts,
                end_ts=segment.end_ts,
                confidence=segment.confidence
            )
            db.add(segment_record)

        db.commit()
        db.refresh(transcript_record)
        return transcript_record

    def process(
        self,
        audio_path: str,
        meeting_id: uuid.UUID,
        project_id: uuid.UUID,
        db: Session
    ):
        # Step 1: Deepgram API
        raw_response = self.deepgram.transcribe_file(audio_path)

        # Step 2: Normalization
        transcript = self.normalizer.normalize(
            raw_response=raw_response,
            meeting_id=meeting_id,
            project_id=project_id,
            connection_mode=ConnectionMode.CLOUD
        )

        # Step 3: Save JSON
        json_path = self.save_json(transcript)

        # Step 4: Save Database
        self.save_to_database(
            db=db,
            transcript=transcript,
            storage_ref=str(json_path)
        )

        return {
            "transcript": transcript,
            "json_path": str(json_path),
            "raw_response": raw_response
        }