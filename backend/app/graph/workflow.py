from langgraph.graph import StateGraph, START, END

from app.graph.state import ProjectState
from app.graph.nodes import (
    load_transcript_node,
    brd_node,
    srs_node,
    consistency_node,
    notion_node
)


def build_graph(checkpointer):

    builder = StateGraph(ProjectState)

    builder.add_node(
        "load_transcript",
        load_transcript_node
    )

    builder.add_node(
        "brd_agent",
        brd_node
    )

    builder.add_node(
        "srs_agent",
        srs_node
    )

    builder.add_node(
        "consistency_checker",
        consistency_node
    )
    
    builder.add_node(
        "notion_publisher",
        notion_node
    )
    
## Edges

    builder.add_edge(
        START,
        "load_transcript"
    )

    # Parallel branches
    builder.add_edge(
        "load_transcript",
        "brd_agent"
    )

    builder.add_edge(
        "load_transcript",
        "srs_agent"
    )

    # Both must complete before consistency checker
    builder.add_edge(
        "brd_agent",
        "consistency_checker"
    )

    builder.add_edge(
        "srs_agent",
        "consistency_checker"
    )

    builder.add_edge(
        "consistency_checker",
        "notion_publisher"
    )
    
    builder.add_edge(
        "notion_publisher",
        END
    )
    return builder.compile(
        checkpointer=checkpointer
    )