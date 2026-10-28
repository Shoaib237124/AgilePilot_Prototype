
import uuid
from pathlib import Path

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.database.database import (
    Base,
    engine,
    get_db,
)
from app.database import models
from app.database.models import Meeting

from app.graph.service import run_document_generation
from app.transcript_pipeline import (
    TranscriptPipeline,
    TranscriptPipelineError,
    DeepgramError,
)

# Module 8: Live Meeting Bot
from app.live_meeting import router as live_meeting_router


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="AgilePilot",
    description=(
        "AgilePilot - Meeting Intelligence Pipeline "
        "with Live Meeting Transcription and "
        "Automated Document Generation"
    ),
    version="0.2.0",
)


# ============================================================
# REGISTER MODULE 8 ROUTES
# ============================================================

app.include_router(live_meeting_router)


# ============================================================
# DIRECTORIES
# ============================================================

AUDIO_DIR = Path("data/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "project": "AgilePilot",
        "phase": "Phase 1",
        "modules": [
            "Module 1 - Project Setup",
            "Module 2 - Speech Pipeline",
            "Modules 3-7 - Document Generation Workflow",
            "Module 8 - Live Meeting Bot",
        ],
        "status": "running",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {"status": "healthy"}


# ============================================================
# PROCESS MEETING AUDIO
# ============================================================

@app.post("/meetings/process-audio")
async def process_meeting_audio(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Validate project UUID
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="project_id must be a valid UUID.",
        )

    # Validate uploaded file
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No audio file provided.",
        )

    allowed_extensions = {
        ".wav",
        ".mp3",
        ".mp4",
        ".m4a",
        ".webm",
        ".ogg",
        ".flac",
    }

    extension = Path(file.filename).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported audio format. "
                f"Supported formats: {sorted(allowed_extensions)}"
            ),
        )

    meeting_id = uuid.uuid4()

    safe_filename = Path(file.filename).name
    audio_path = AUDIO_DIR / f"{meeting_id}_{safe_filename}"

    try:
        # Save uploaded audio
        contents = await file.read()

        with open(audio_path, "wb") as audio_file:
            audio_file.write(contents)

        # Create meeting record
        meeting = Meeting(
            id=meeting_id,
            project_id=project_uuid,
            connection_mode="cloud",
        )

        db.add(meeting)
        db.commit()

        # Run existing transcription pipeline
        pipeline = TranscriptPipeline()

        result = pipeline.process(
            audio_path=str(audio_path),
            meeting_id=meeting_id,
            project_id=project_uuid,
            db=db,
        )

        transcript = result["transcript"]

        return {
            "success": True,
            "meeting_id": str(meeting_id),
            "project_id": str(project_uuid),
            "audio_file": str(audio_path),
            "transcript_file": result["json_path"],
            "segment_count": len(transcript.segments),
            "transcript": transcript.model_dump(mode="json"),
        }

    except DeepgramError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc))

    except TranscriptPipelineError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected server error: {str(exc)}",
        )

    finally:
        await file.close()


# ============================================================
# GENERATE DOCUMENTS FROM AN EXISTING MEETING TRANSCRIPT
# ============================================================

@app.post("/meetings/{meeting_id}/generate-documents")
def generate_documents(
    meeting_id: str,
    project_id: str,
):
    # Validate both UUIDs
    try:
        meeting_uuid = uuid.UUID(meeting_id)
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="meeting_id and project_id must be valid UUIDs.",
        )

    try:
        result = run_document_generation(
            meeting_id=str(meeting_uuid),
            project_id=str(project_uuid),
        )

        return {
            "status": "completed",
            "meeting_id": str(meeting_uuid),
            "project_id": str(project_uuid),
            "brd": result.get("brd"),
            "srs": result.get("srs"),
            "consistency_report": result.get("consistency_report"),
            "notion": {
                "status": result.get("notion_status"),
                "page_id": result.get("notion_page_id"),
                "page_url": result.get("notion_page_url"),
                "errors": result.get("errors", []),
            },
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )
