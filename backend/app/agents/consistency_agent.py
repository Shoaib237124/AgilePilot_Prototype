from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from app.schemas.consistency import ConsistencyReport
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """
You are an expert requirements consistency analyst.

You are given:

1. A Business Requirements Document (BRD)
2. A Software Requirements Specification (SRS)

Compare them carefully.

Identify:

- contradictions
- business requirements missing from SRS
- SRS requirements unsupported by BRD
- scope mismatches
- actor mismatches
- feature mismatches
- conflicting assumptions
- conflicting constraints
- ambiguous requirements

Do not report something as inconsistent merely because
the BRD and SRS use different wording.

Use semantic comparison.

The consistency score must be between 0 and 1.

1.0 means fully consistent.
0.0 means severely inconsistent.

Return a structured consistency report.
"""


def check_consistency(
    brd: dict,
    srs: dict
) -> dict:

    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash")

    structured_llm = llm.with_structured_output(
        ConsistencyReport
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                """
BRD:

{brd}

SRS:

{srs}

Analyze the consistency between them.
"""
            ),
        ]
    )

    chain = prompt | structured_llm

    result = chain.invoke(
        {
            "brd": brd,
            "srs": srs
        }
    )

    return result.model_dump()