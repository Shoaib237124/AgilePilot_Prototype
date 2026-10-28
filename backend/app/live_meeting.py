
import asyncio
import json
import logging
import uuid
from pathlib import Path
from urllib.parse import urlencode

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from app.config import DEEPGRAM_API_KEY
from app.database.database import SessionLocal
from app.database.models import Meeting
from app.schemas.transcript import (
    Transcript,
    TranscriptSegment,
    SpeakerRole,
    ConnectionMode,
)
from app.transcript_pipeline import TranscriptPipeline


router = APIRouter()
logger = logging.getLogger(__name__)

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"

LIVE_PARAMS = {
    "model": "nova-3",
    "language": "en",
    "encoding": "linear16",
    "sample_rate": 16000,
    "channels": 1,
    "interim_results": "true",
    "diarize_model": "latest",
    "smart_format": "true",
    "punctuate": "true",
    "endpointing": 300,
    "utterance_end_ms": 1000,
}


def make_deepgram_url() -> str:
    return f"{DEEPGRAM_WS_URL}?{urlencode(LIVE_PARAMS)}"


def get_speaker_role(speaker_id):
    """
    Map diarization IDs to the application's two role labels.

    Important: Deepgram speaker IDs do not identify real people.
    Confirm the role mapping for your own meeting workflow.
    """
    if speaker_id == 1:
        return SpeakerRole.CLIENT

    return SpeakerRole.PROJECT_MANAGER


def get_channel_and_alternatives(data: dict):
    """
    Safely extract Deepgram alternatives.

    Normally channel is a dictionary containing alternatives.
    This also tolerates a list-shaped channel value.
    """
    channel = data.get("channel", {})

    if isinstance(channel, list):
        if not channel:
            return {}, []

        # Support a list containing channel dictionaries.
        first_channel = channel[0]

        if isinstance(first_channel, dict):
            channel = first_channel
        else:
            return {}, []

    if not isinstance(channel, dict):
        return {}, []

    alternatives = channel.get("alternatives", [])

    if not isinstance(alternatives, list):
        return channel, []

    return channel, alternatives


def build_segment(result: dict):
    """Convert a finalized Deepgram result into TranscriptSegment."""
    _, alternatives = get_channel_and_alternatives(result)

    if not alternatives or not isinstance(alternatives[0], dict):
        return None

    alternative = alternatives[0]
    text = (alternative.get("transcript") or "").strip()

    if not text:
        return None

    words = alternative.get("words", [])
    if not isinstance(words, list):
        words = []

    valid_words = [
        word for word in words
        if isinstance(word, dict)
    ]

    speaker_id = None
    if valid_words:
        speaker_id = valid_words[0].get("speaker")

    start_ts = float(result.get("start") or 0.0)
    duration = float(result.get("duration") or 0.0)
    end_ts = start_ts + duration

    if valid_words:
        start_ts = float(valid_words[0].get("start", start_ts))
        end_ts = float(valid_words[-1].get("end", end_ts))

    confidence = alternative.get("confidence")
    if confidence is not None:
        confidence = float(confidence)

    return TranscriptSegment(
        segment_id=uuid.uuid4(),
        speaker_role=get_speaker_role(speaker_id),
        text=text,
        start_ts=start_ts,
        end_ts=end_ts,
        confidence=confidence,
    )


async def safe_send_json(websocket: WebSocket, payload: dict):
    """Return False if the browser is no longer connected."""
    try:
        await websocket.send_json(payload)
        return True
    except Exception:
        return False


@router.get("/live-meeting")
async def live_meeting_page():
    html_path = (
        Path(__file__).parent
        / "static"
        / "live_meeting.html"
    )
    return FileResponse(html_path, media_type="text/html")


@router.websocket("/ws/live-meeting/{meeting_id}")
async def live_meeting_socket(
    websocket: WebSocket,
    meeting_id: str,
):
    await websocket.accept()

    reader_task = None
    finalized_segments = []
    transcript_saved = False
    stop_requested = False

    try:
        # ----------------------------------------------------
        # Validate Deepgram configuration
        # ----------------------------------------------------
        if not DEEPGRAM_API_KEY:
            await safe_send_json(
                websocket,
                {
                    "type": "error",
                    "message": "Deepgram API key is not configured.",
                },
            )
            await websocket.close(code=1011)
            return

        # ----------------------------------------------------
        # Validate meeting UUID
        # ----------------------------------------------------
        try:
            meeting_uuid = uuid.UUID(meeting_id)
        except (ValueError, TypeError, AttributeError):
            await safe_send_json(
                websocket,
                {
                    "type": "error",
                    "message": "meeting_id must be a valid UUID.",
                },
            )
            await websocket.close(code=1008)
            return

        # ----------------------------------------------------
        # Receive start message
        # ----------------------------------------------------
        start_message = await websocket.receive_json()

        if not isinstance(start_message, dict):
            await safe_send_json(
                websocket,
                {
                    "type": "error",
                    "message:": "Invalid start message.",
                },
            )
            await websocket.close(code=1008)
            return

        if start_message.get("type") != "start":
            await safe_send_json(
                websocket,
                {
                    "type": "error",
                    "message": "Send a start message first.",
                },
            )
            await websocket.close(code=1008)
            return

        try:
            project_uuid = uuid.UUID(start_message["project_id"])
        except (KeyError, ValueError, TypeError, AttributeError):
            await safe_send_json(
                websocket,
                {
                    "type": "error",
                    "message": "A valid project_id UUID is required.",
                },
            )
            await websocket.close(code=1008)
            return

        # ----------------------------------------------------
        # Verify meeting exists and belongs to supplied project
        # ----------------------------------------------------
        db = SessionLocal()

        try:
            meeting = (
                db.query(Meeting)
                .filter(Meeting.id == meeting_uuid)
                .first()
            )

            if not meeting:
                await safe_send_json(
                    websocket,
                    {
                        "type": "error",
                        "message": (
                            "Meeting not found. Create the meeting "
                            "using your existing meeting API first."
                        ),
                    },
                )
                await websocket.close(code=1008)
                return

            if meeting.project_id != project_uuid:
                await safe_send_json(
                    websocket,
                    {
                        "type": "error",
                        "message": (
                            "The supplied project_id does not match "
                            "the selected meeting."
                        ),
                    },
                )
                await websocket.close(code=1008)
                return
        finally:
            db.close()

        # ----------------------------------------------------
        # Connect to Deepgram streaming API
        # ----------------------------------------------------
        async with websockets.connect(
            make_deepgram_url(),
            additional_headers={
                "Authorization": f"Token {DEEPGRAM_API_KEY}"
            },
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
            max_size=None,
        ) as deepgram_socket:

            await safe_send_json(
                websocket,
                {
                    "type": "ready",
                    "meeting_id": str(meeting_uuid),
                    "message": "Live transcription is ready.",
                },
            )

            # ------------------------------------------------
            # Read Deepgram responses concurrently
            # ------------------------------------------------
            async def read_deepgram_results():
                try:
                    async for raw_message in deepgram_socket:
                        try:
                            data = json.loads(raw_message)
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(
                                "Ignoring invalid Deepgram JSON response."
                            )
                            continue

                        if not isinstance(data, dict):
                            continue

                        if data.get("type") == "Error":
                            await safe_send_json(
                                websocket,
                                {
                                    "type": "error",
                                    "message": data.get(
                                        "description",
                                        "Deepgram transcription error.",
                                    ),
                                },
                            )
                            continue

                        # Metadata and other event types may not contain
                        # transcript channels.
                        _, alternatives = get_channel_and_alternatives(data)

                        if not alternatives:
                            continue

                        alternative = alternatives[0]
                        if not isinstance(alternative, dict):
                            continue

                        text = (
                            alternative.get("transcript") or ""
                        ).strip()

                        is_final = bool(data.get("is_final", False))

                        words = alternative.get("words", [])
                        if not isinstance(words, list):
                            words = []

                        valid_words = [
                            word for word in words
                            if isinstance(word, dict)
                        ]

                        speaker_id = (
                            valid_words[0].get("speaker")
                            if valid_words
                            else None
                        )

                        # Send partial and finalized transcript text
                        # to the browser for display.
                        if text:
                            await safe_send_json(
                                websocket,
                                {
                                    "type": "transcript",
                                    "text": text,
                                    "is_final": is_final,
                                    "speaker_id": speaker_id,
                                    "start": data.get("start"),
                                    "duration": data.get("duration"),
                                },
                            )

                        # Persist only finalized results.
                        if is_final:
                            segment = build_segment(data)

                            if segment is not None:
                                finalized_segments.append(segment)

                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception(
                        "Error while reading Deepgram results."
                    )
                    raise

            reader_task = asyncio.create_task(
                read_deepgram_results()
            )

            # ------------------------------------------------
            # Forward browser audio until Stop or disconnect
            # ------------------------------------------------
            while True:
                message = await websocket.receive()

                if message["type"] == "websocket.disconnect":
                    break

                audio_bytes = message.get("bytes")

                if audio_bytes is not None:
                    await deepgram_socket.send(audio_bytes)
                    continue

                text_message = message.get("text")

                if not text_message:
                    continue

                try:
                    control = json.loads(text_message)
                except json.JSONDecodeError:
                    continue

                if not isinstance(control, dict):
                    continue

                if control.get("type") == "stop":
                    stop_requested = True
                    break

            # ------------------------------------------------
            # Ask Deepgram to flush pending results
            # ------------------------------------------------
            try:
                await deepgram_socket.send(
                    json.dumps({"type": "CloseStream"})
                )
            except Exception:
                logger.warning(
                    "Could not send Deepgram CloseStream."
                )

            # Wait for Deepgram's final messages.
            if reader_task:
                try:
                    await asyncio.wait_for(
                        asyncio.shield(reader_task),
                        timeout=8,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "Timed out waiting for final Deepgram results."
                    )
                    reader_task.cancel()
                    await asyncio.gather(
                        reader_task,
                        return_exceptions=True,
                    )
                except Exception:
                    logger.exception(
                        "Deepgram result reader terminated with an error."
                    )

            reader_task = None

        # ----------------------------------------------------
        # Save transcript to JSON and Supabase
        # ----------------------------------------------------
        if not finalized_segments:
            await safe_send_json(
                websocket,
                {
                    "type": "error",
                    "message": (
                        "No finalized speech segments were received. "
                        "Check microphone permission, audio input, "
                        "and the Deepgram connection."
                    ),
                },
            )
            return

        transcript = Transcript(
            meeting_id=meeting_uuid,
            project_id=project_uuid,
            connection_mode=ConnectionMode.CLOUD,
            format_version="1.0",
            segments=finalized_segments,
        )

        pipeline = TranscriptPipeline()

        json_path = pipeline.save_json(transcript)

        db = SessionLocal()

        try:
            pipeline.save_to_database(
                db=db,
                transcript=transcript,
                storage_ref=str(json_path),
            )
            transcript_saved = True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        await safe_send_json(
            websocket,
            {
                "type": "transcript_saved",
                "meeting_id": str(meeting_uuid),
                "segment_count": len(finalized_segments),
                "json_path": str(json_path),
                "message": "Transcript saved successfully.",
            },
        )

        # ----------------------------------------------------
        # Run existing Modules 4-7 after a normal Stop
        # ----------------------------------------------------
        if transcript_saved and stop_requested:
            try:
                result = await asyncio.to_thread(
                    run_document_generation_wrapper,
                    str(meeting_uuid),
                    str(project_uuid),
                )

                report = result.get("consistency_report") or {}

                await safe_send_json(
                    websocket,
                    {
                        "type": "documents_generated",
                        "meeting_id": str(meeting_uuid),
                        "notion_status": result.get("notion_status"),
                        "notion_page_url": result.get("notion_page_url"),
                        "consistency_score": report.get(
                            "consistency_score"
                        ),
                        "message": (
                            "Document generation workflow finished."
                        ),
                    },
                )

            except Exception:
                logger.exception(
                    "Document generation failed for meeting %s",
                    meeting_uuid,
                )

                await safe_send_json(
                    websocket,
                    {
                        "type": "documents_failed",
                        "message": (
                            "Transcript was saved, but document "
                            "generation failed. Check the backend log."
                        ),
                    },
                )

        await safe_send_json(
            websocket,
            {
                "type": "meeting_finished",
                "message": "Live meeting session finished.",
            },
        )

    except WebSocketDisconnect:
        logger.info("Browser disconnected from live meeting.")

    except Exception:
        logger.exception("Live meeting processing failed.")

        await safe_send_json(
            websocket,
            {
                "type": "error",
                "message": (
                    "Live meeting processing failed. "
                    "Check the backend terminal for details."
                ),
            },
        )

    finally:
        if reader_task and not reader_task.done():
            reader_task.cancel()
            await asyncio.gather(
                reader_task,
                return_exceptions=True,
            )


def run_document_generation_wrapper(
    meeting_id: str,
    project_id: str,
):
    """
    Import the workflow service only when document generation is needed.
    """
    from app.graph.service import run_document_generation

    return run_document_generation(
        meeting_id=meeting_id,
        project_id=project_id,
    )
