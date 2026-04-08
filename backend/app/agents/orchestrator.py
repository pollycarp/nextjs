"""
Multi-agent orchestrator — Phase 4.

State machine: research → critique → [revise (max 2×) | write] → done

Uses plain Python instead of LangGraph to avoid Python-3.14 incompatibility.
The design mirrors LangGraph's node/edge pattern exactly.
"""

import asyncio
from typing import TypedDict, Callable, Optional

from app.agents.researcher import run_researcher
from app.agents.critic import run_critic
from app.agents.writer import run_writer

MAX_REVISIONS = 2


class ResearchState(TypedDict):
    query: str
    research_output: str
    critique_output: str
    revision_count: int
    final_report: str
    sources: list
    flagged_claims: list


# ── Nodes ─────────────────────────────────────────────────────────────────── #

def _research_node(state: ResearchState) -> ResearchState:
    result = run_researcher(state["query"])
    return {**state, "research_output": result["research_output"], "sources": result["sources"]}


def _critique_node(state: ResearchState) -> ResearchState:
    result = run_critic(state["research_output"])
    return {**state, "critique_output": result["critique_output"], "flagged_claims": result["flagged_claims"]}


def _revise_node(state: ResearchState) -> ResearchState:
    revised_query = f"{state['query']}\n\nAddress the following critique:\n{state['critique_output']}"
    result = run_researcher(revised_query)
    return {
        **state,
        "research_output": result["research_output"],
        "sources": result["sources"],
        "revision_count": state["revision_count"] + 1,
    }


def _write_node(state: ResearchState) -> ResearchState:
    result = run_writer(
        state["query"],
        state["research_output"],
        state["critique_output"],
        state["sources"],
    )
    return {**state, "final_report": result["final_report"]}


# ── Pipeline ──────────────────────────────────────────────────────────────── #

def run_pipeline(
    query: str,
    event_callback: Optional[Callable[[str, str], None]] = None,
) -> ResearchState:
    """Run the full multi-agent pipeline synchronously."""
    state: ResearchState = {
        "query": query,
        "research_output": "",
        "critique_output": "",
        "revision_count": 0,
        "final_report": "",
        "sources": [],
        "flagged_claims": [],
    }

    def _emit(agent: str, status: str):
        if event_callback:
            event_callback(agent, status)

    _emit("researcher", "working")
    state = _research_node(state)
    _emit("researcher", "done")

    while True:
        _emit("critic", "working")
        state = _critique_node(state)
        _emit("critic", "done")

        if len(state["flagged_claims"]) > 2 and state["revision_count"] < MAX_REVISIONS:
            _emit("researcher", "revising")
            state = _revise_node(state)
            _emit("researcher", "revised")
        else:
            break

    _emit("writer", "working")
    state = _write_node(state)
    _emit("writer", "done")

    return state


async def run_pipeline_async(
    query: str,
    event_callback: Optional[Callable[[str, str], None]] = None,
) -> ResearchState:
    """Async wrapper — runs the pipeline in a thread pool."""
    return await asyncio.to_thread(run_pipeline, query, event_callback)
