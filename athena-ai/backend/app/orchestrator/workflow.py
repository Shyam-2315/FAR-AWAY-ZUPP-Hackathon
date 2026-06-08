"""LangGraph workflow definition for the Athena AI multi-agent pipeline.

The compiled graph is built once at module import time and reused across
all requests — LangGraph graphs are thread/coroutine safe for invocation.

Graph topology:
    START → observer → investigation → prediction → strategy
          → decision → reporting → END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.decision import decision_agent
from app.agents.investigation import investigation_agent
from app.agents.observer import observer_agent
from app.agents.prediction import prediction_agent
from app.agents.reporting import reporting_agent
from app.agents.state import AgentState
from app.agents.strategy import strategy_agent


def _build_workflow() -> StateGraph:  # type: ignore[type-arg]
    """Construct and wire the LangGraph StateGraph."""
    builder: StateGraph = StateGraph(AgentState)  # type: ignore[type-arg]

    # Register nodes — each is a plain synchronous callable.
    builder.add_node("observer", observer_agent)
    builder.add_node("investigation", investigation_agent)
    builder.add_node("prediction", prediction_agent)
    builder.add_node("strategy", strategy_agent)
    builder.add_node("decision", decision_agent)
    builder.add_node("reporting", reporting_agent)

    # Wire the linear pipeline.
    builder.add_edge(START, "observer")
    builder.add_edge("observer", "investigation")
    builder.add_edge("investigation", "prediction")
    builder.add_edge("prediction", "strategy")
    builder.add_edge("strategy", "decision")
    builder.add_edge("decision", "reporting")
    builder.add_edge("reporting", END)

    return builder


# Compiled once — safe to import and invoke from async contexts.
_workflow = _build_workflow().compile()


def get_workflow() -> object:
    """Return the compiled LangGraph workflow."""
    return _workflow
