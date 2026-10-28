import json
from pathlib import Path

from app.agents.brd_agent import generate_brd
from app.agents.srs_agent import generate_srs
from app.agents.consistency_agent import check_consistency
from app.graph.state import ProjectState
from app.config import TRANSCRIPT_DIR
from app.notion.client import (
    NotionClient,
    NotionError
)
from app.notion.blocks import (
    heading_block,
    text_block,
    divider_block,
    document_to_blocks,
)


def load_transcript_node(state: ProjectState) -> dict:
    meeting_id = state["meeting_id"]

    transcript_path = (
        Path(TRANSCRIPT_DIR)
        / f"{meeting_id}.json"
    )

    if not transcript_path.exists():
        raise FileNotFoundError(
            f"Transcript not found: {transcript_path}"
        )

    with open(
        transcript_path,
        "r",
        encoding="utf-8"
    ) as file:
        transcript = json.load(file)

    return {
        "transcript": transcript,
        "status": ["transcript_loaded"]
    }


def brd_node(state: ProjectState) -> dict:
    brd = generate_brd(state["transcript"])

    return {
        "brd": brd,
        "status": ["brd_generated"]
    }


def srs_node(state: ProjectState) -> dict:
    srs = generate_srs(state["transcript"])

    return {
        "srs": srs,
        "status": ["srs_generated"]
    }


def consistency_node(state: ProjectState) -> dict:
    report = check_consistency(
        state["brd"],
        state["srs"]
    )

    return {
        "consistency_report": report,
        "status": ["completed"]
    }


def notion_node(state: ProjectState) -> dict:
    try:
        meeting_id = state["meeting_id"]
        project_id = state["project_id"]

        brd = state.get("brd")
        srs = state.get("srs")
        consistency_report = state.get("consistency_report")

        notion = NotionClient()

        title = f"AgilePilot Meeting - {meeting_id}"

        blocks = [
            heading_block(
                "AgilePilot Meeting Documentation",
                level=1
            ),
            text_block(f"Meeting ID: {meeting_id}"),
            text_block(f"Project ID: {project_id}"),
            divider_block(),
        ]

        blocks.extend(
            document_to_blocks(
                "Business Requirements Document",
                brd
            )
        )

        blocks.append(divider_block())

        blocks.extend(
            document_to_blocks(
                "Software Requirements Specification",
                srs
            )
        )

        blocks.append(divider_block())

        blocks.extend(
            document_to_blocks(
                "Consistency Report",
                consistency_report
            )
        )

        page = notion.create_page(
            title=title,
            blocks=blocks
        )

        return {
            "notion_page_id": page.get("id"),
            "notion_page_url": page.get("url"),
            "notion_status": "published",
            "status": ["notion_published"],
        }

    except NotionError as exc:
        return {
            "notion_page_id": None,
            "notion_page_url": None,
            "notion_status": "failed",
            "status": ["notion_failed"],
            "errors": [str(exc)],
        }