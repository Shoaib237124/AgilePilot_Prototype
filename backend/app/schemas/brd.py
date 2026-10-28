from typing import List, Optional
from pydantic import BaseModel, Field


class Stakeholder(BaseModel):
    """Represents an internal or external stakeholder involved in or impacted by the project."""

    name: str = Field(
        ...,
        description="Full name or team/group designation of the stakeholder (e.g., 'Jane Doe' or 'Finance Ops Team').",
        examples=["Jane Doe", "Operations Department"],
    )
    role: str = Field(
        ...,
        description="Official title or functional responsibility relative to the project.",
        examples=["Executive Sponsor", "Compliance Officer"],
    )
    needs: List[str] = Field(
        default_factory=list,
        description="High-level business expectations, pain points, or deliverables required by this stakeholder.",
        examples=[
            "Real-time transaction reporting",
            "Automated audit trail generation",
        ],
    )


class BusinessRequirement(BaseModel):
    """High-level requirement explaining WHAT business outcome is needed and WHY."""

    id: str = Field(
        ...,
        description="Unique identifier for requirement tracing (typically formatted as BR-XXX).",
        examples=["BR-001", "BR-002"],
    )
    description: str = Field(
        ...,
        description="Clear, declarative statement defining the business requirement in non-technical terms.",
        examples=[
            "The system must reduce manual loan approval processing time by at least 40%."
        ],
    )
    priority: str = Field(
        default="medium",
        description="Relative business importance. Recommended values: 'low', 'medium', 'high', or 'critical'.",
        examples=["critical", "high"],
    )


class BusinessObjective(BaseModel):
    """Measurable business goal directly linked to organizational strategy."""

    id: str = Field(
        ...,
        description="Unique identifier for the objective (typically formatted as OBJ-XXX).",
        examples=["OBJ-001"],
    )
    description: str = Field(
        ...,
        description="Specific, measurable business target or outcome expected from this initiative.",
        examples=[
            "Achieve 99.9% billing accuracy within 3 months of deployment."
        ],
    )


class BRD(BaseModel):
    """Business Requirements Document defining high-level business goals, target audience, scope boundaries, and core objectives."""

    document_type: str = Field(
        default="BRD",
        description="Type designation for document taxonomy. Keep constant as 'BRD'.",
    )
    version: str = Field(
        default="1.0",
        description="Semantic document versioning string.",
        examples=["1.0", "1.1"],
    )

    project_name: str = Field(
        ...,
        description="Official title of the project or initiative.",
        examples=["Enterprise Portal Modernization"],
    )
    executive_summary: str = Field(
        ...,
        description="High-level overview summarizing the project's background, purpose, key deliverables, and anticipated ROI.",
    )

    business_problem: str = Field(
        ...,
        description="Detailed description of the current operational friction, customer pain points, or revenue bottlenecks driving this effort.",
    )
    business_vision: str = Field(
        ...,
        description="Aspirational future state of the business once this initiative is fully operationalized.",
    )

    objectives: List[BusinessObjective] = Field(
        default_factory=list,
        description="List of strategic business objectives aligned with corporate goals.",
    )

    stakeholders: List[Stakeholder] = Field(
        default_factory=list,
        description="Key individuals or groups involved in, influencing, or impacted by this solution.",
    )

    target_users: List[str] = Field(
        default_factory=list,
        description="Primary end-user personas or groups who will interact with the solution.",
        examples=[
            "Customer Support Agents",
            "Tier-1 Financial Auditors",
            "External Vendors",
        ],
    )

    business_requirements: List[BusinessRequirement] = Field(
        default_factory=list,
        description="Core functional business requirements driving product development.",
    )

    scope_in: List[str] = Field(
        default_factory=list,
        description="Explicit list of features, process steps, integrations, or workflows included in this project phase.",
        examples=[
            "Automated PDF export",
            "Integration with Stripe payment gateway",
        ],
    )
    scope_out: List[str] = Field(
        default_factory=list,
        description="Explicit list of capabilities or features explicitly deferred to future releases or completely excluded.",
        examples=[
            "Custom iOS native app development",
            "Multi-currency reconciliation",
        ],
    )

    assumptions: List[str] = Field(
        default_factory=list,
        description="Conditions or facts considered true without immediate proof for planning purposes.",
        examples=[
            "Existing database infrastructure supports up to 10k concurrent reads."
        ],
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="External restrictions (budget, timeline, regulatory compliance, technology stack) limiting project options.",
        examples=["GDPR compliance required", "System launch targeted for Q3"],
    )

    success_criteria: List[str] = Field(
        default_factory=list,
        description="Measurable KPIs or condition definitions required to declare project success.",
        examples=["Zero critical security flaws detected in final security audit."],
    )

    open_questions: List[str] = Field(
        default_factory=list,
        description="Unresolved operational, legal, or technical questions requiring stakeholder decision before baseline sign-off.",
        examples=[
            "Will the legacy database API support real-time webhooks or require batch sync?"
        ],
    )