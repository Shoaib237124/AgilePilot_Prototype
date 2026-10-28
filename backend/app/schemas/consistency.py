from typing import List
from pydantic import BaseModel, Field


class ConsistencyIssue(BaseModel):
    issue_id: str

    issue_type: str

    severity: str

    brd_reference: str | None = None

    srs_reference: str | None = None

    description: str

    recommendation: str


class ConsistencyReport(BaseModel):
    document_type: str = "CONSISTENCY_REPORT"
    version: str = "1.0"

    overall_consistent: bool

    consistency_score: float = Field(
        ge=0.0,
        le=1.0
    )

    summary: str

    issues: List[ConsistencyIssue] = Field(
        default_factory=list
    )

    recommendations: List[str] = Field(
        default_factory=list
    )