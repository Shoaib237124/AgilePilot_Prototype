from langchain_core.prompts import ChatPromptTemplate
from app.schemas.srs import SRS
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """
You are an expert Software Requirements Engineer.

You are given a meeting transcript from a software project discussion.

Create a Software Requirements Specification (SRS).

Extract ONLY information supported by the transcript.

Do not invent technical requirements.

If information is ambiguous or missing, put it in open_questions.

Focus on:

- system purpose
- actors
- functional requirements
- non-functional requirements
- system features
- external interfaces
- data requirements
- security
- performance
- constraints
- assumptions

Functional requirements must be clear and testable.

Return a structured SRS.
"""


def generate_srs(transcript: dict) -> dict:
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")

    structured_llm = llm.with_structured_output(SRS)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                """
Meeting transcript:

{transcript}

Generate the SRS.
"""
            ),
        ]
    )

    chain = prompt | structured_llm

    result = chain.invoke(
        {
            "transcript": transcript
        }
    )

    return result.model_dump()