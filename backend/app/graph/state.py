import operator
from typing import Annotated, Any, TypedDict, Optional


class ProjectState(TypedDict, total=False):
    meeting_id: str
    project_id: str

    transcript: dict[str, Any]

    brd: dict[str, Any] | None
    srs: dict[str, Any] | None
    consistency_report: dict[str, Any] | None

    status: Annotated[list[str], operator.add]

    errors: Annotated[list[str], operator.add]

    notion_page_id: Optional[str]
    notion_page_url: Optional[str]
    notion_status: Optional[str]