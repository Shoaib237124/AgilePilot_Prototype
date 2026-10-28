from langchain_core.prompts import ChatPromptTemplate
from app.schemas.brd import BRD
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """
You are an expert Business Requirements Analyst.

You are given a meeting transcript from a software project discussion.

Your task is to create a Business Requirements Document (BRD).

Extract ONLY information that is supported by the transcript.

Do not invent requirements.

If something is unclear, place it in open_questions.

Focus on:

- business problem
- business vision
- business objectives
- stakeholders
- target users
- business requirements
- project scope
- assumptions
- constraints
- success criteria

Business requirements must describe WHAT the business needs,
not detailed technical implementation.

Return a structured BRD.
"""


def generate_brd(transcript: dict) -> dict:
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

    structured_llm = llm.with_structured_output(BRD)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                """
Meeting transcript:

{transcript}

Generate the BRD.
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