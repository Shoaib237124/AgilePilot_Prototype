from app.graph.checkpointer import create_checkpointer
from app.graph.workflow import build_graph


def run_document_generation(
    meeting_id: str,
    project_id: str
):

    with create_checkpointer() as checkpointer:

        graph = build_graph(checkpointer)

        config = {
            "configurable": {
                "thread_id": f"{meeting_id}-test"
            }
        }

        initial_state = {
            "meeting_id": meeting_id,
            "project_id": project_id,
            "brd": None,
            "srs": None,
            "consistency_report": None,
            "notion_page_id": None,
            "notion_page_url": None,
            "notion_status": "pending",
            "errors": [],
            "status": ["started"],
        }

        result = graph.invoke(
            initial_state,
            config=config
        )

        return result