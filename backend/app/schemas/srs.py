from typing import List, Optional
from pydantic import BaseModel, Field


class FunctionalRequirement(BaseModel):
    """Specific technical behavior, operation, or automated action the system must perform."""

    id: str = Field(
        ...,
        description="Unique requirement code for traceability matrix (typically formatted as FR-XXX).",
        examples=["FR-101", "FR-102"],
    )
    description: str = Field(
        ...,
        description="Detailed, unambiguous statement detailing the action, input, and expected system output.",
        examples=[
            "The system shall authenticate users via OAuth 2.0 with MFA enforcement."
        ],
    )
    priority: str = Field(
        default="medium",
        description="Implementation priority. Recommended: 'low', 'medium', 'high', or 'critical'.",
        examples=["high", "critical"],
    )
    actors: List[str] = Field(
        default_factory=list,
        description="List of primary system actors or API clients initiating or interacting with this specific function.",
        examples=["Registered Customer", "System Administrator", "Payment Gateway"],
    )


class NonFunctionalRequirement(BaseModel):
    """Quality attribute, system constraint, or operational performance metric."""

    id: str = Field(
        ...,
        description="Unique NFR tracking identifier (typically formatted as NFR-XXX).",
        examples=["NFR-001", "NFR-002"],
    )
    category: str = Field(
        ...,
        description="Classification domain for the non-functional metric.",
        examples=[
            "Performance",
            "Security",
            "Scalability",
            "Usability",
            "Reliability",
            "Maintainability",
        ],
    )
    description: str = Field(
        ...,
        description="Quantifiable standard or operational threshold the system must meet.",
        examples=[
            "The API endpoint must maintain response times under 200ms at p95 under standard load."
        ],
    )
    priority: str = Field(
        default="medium",
        description="Implementation or operational priority designation.",
        examples=["high"],
    )


class SRS(BaseModel):
    """Software Requirements Specification document outlining concrete system architecture, interfaces, and technical criteria."""

    document_type: str = Field(
        default="SRS",
        description="Document taxonomy type identifier. Keep constant as 'SRS'.",
    )
    version: str = Field(
        default="1.0",
        description="Software architecture specification version.",
        examples=["1.0", "1.0.1"],
    )

    project_name: str = Field(
        ...,
        description="Official software application or system release module name.",
        examples=["Core Settlement Engine v2.0"],
    )
    system_purpose: str = Field(
        ...,
        description="Technical scope, architectural context, and concrete goals of the software product.",
    )

    functional_requirements: List[FunctionalRequirement] = Field(
        default_factory=list,
        description="Complete list of explicit behavioral and algorithmic functional specifications.",
    )

    non_functional_requirements: List[NonFunctionalRequirement] = Field(
        default_factory=list,
        description="System architectural quality attributes (performance, reliability, security thresholds).",
    )

    system_features: List[str] = Field(
        default_factory=list,
        description="High-level logical feature groupings or capability modules implemented in this software.",
        examples=[
            "User Session Management",
            "Real-time Notification Engine",
            "Automated PDF Invoicing",
        ],
    )

    actors: List[str] = Field(
        default_factory=list,
        description="Complete catalog of human roles, background job agents, or third-party systems that interact with the system.",
        examples=["Guest User", "Database Daemon", "Stripe Webhook Listener"],
    )

    external_interfaces: List[str] = Field(
        default_factory=list,
        description="Protocols, external APIs, messaging queues, or UI standards for third-party system interaction.",
        examples=[
            "REST API v1 over HTTPS with Bearer Token auth",
            "Kafka Event Stream 'order-events'",
        ],
    )

    data_requirements: List[str] = Field(
        default_factory=list,
        description="Data models, storage constraints, retention policies, privacy requirements, and schema conventions.",
        examples=[
            "User credentials must be hashed using bcrypt (cost factor >= 12).",
            "Audit logs must be retained in cold storage for 7 years.",
        ],
    )

    security_requirements: List[str] = Field(
        default_factory=list,
        description="Authentication models, authorization policies (RBAC/ABAC), data encryption standards, and vulnerability protections.",
        examples=[
            "All data in transit must enforce TLS 1.3.",
            "Database fields containing PII must be encrypted using AES-256.",
        ],
    )

    performance_requirements: List[str] = Field(
        default_factory=list,
        description="Target throughput, concurrency limits, system resource consumption, and latency benchmarks.",
        examples=[
            "System must sustain 5,000 write operations per second at peak usage.",
            "Page load completion time under 1.5 seconds on 4G networks.",
        ],
    )

    system_constraints: List[str] = Field(
        default_factory=list,
        description="Hard technical limitations imposed by hardware, cloud platform choices, compiler limits, or target deployment environment.",
        examples=[
            "Must be deployed entirely within AWS us-east-1 region.",
            "Backend services must run inside Docker containers with memory ceiling < 2GB per replica.",
        ],
    )

    assumptions: List[str] = Field(
        default_factory=list,
        description="Technical premises or environment settings assumed true during architecture planning.",
        examples=[
            "PostgreSQL 16 database server will be provisioned with high availability replication."
        ],
    )

    open_questions: List[str] = Field(
        default_factory=list,
        description="Unresolved architectural decisions or technical ambiguities needing resolution before sprint breakdown.",
        examples=[
            "Should we leverage AWS Redis ElastiCache or self-host Valkey for session state management?"
        ],
    )