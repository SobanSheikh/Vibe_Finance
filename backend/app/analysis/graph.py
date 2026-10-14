from dataclasses import dataclass
from typing import Any, Protocol

from langgraph.graph import END, START, StateGraph

from app.analysis.state import AnalysisState


class AnalysisNode(Protocol):
    def __call__(self, state: AnalysisState) -> dict[str, Any]: ...


@dataclass(frozen=True)
class AnalysisGraphNodes:
    """Dependencies for the workflow, kept injectable for tests and providers."""

    market_agent: AnalysisNode
    filing_agent: AnalysisNode
    portfolio_agent: AnalysisNode
    validate_evidence: AnalysisNode
    resolve_conflicts: AnalysisNode
    compose_recommendation: AnalysisNode
    collect_metrics: AnalysisNode


def build_analysis_graph(nodes: AnalysisGraphNodes):  # type: ignore[no-untyped-def]
    """Compile the mandatory fan-out/fan-in multi-agent workflow."""

    builder = StateGraph(AnalysisState)
    builder.add_node("market_agent", nodes.market_agent)
    builder.add_node("filing_agent", nodes.filing_agent)
    builder.add_node("portfolio_agent", nodes.portfolio_agent)
    builder.add_node("validate_evidence", nodes.validate_evidence)
    builder.add_node("resolve_conflicts", nodes.resolve_conflicts)
    builder.add_node("compose_recommendation", nodes.compose_recommendation)
    builder.add_node("collect_metrics", nodes.collect_metrics)

    specialist_nodes = ["market_agent", "filing_agent", "portfolio_agent"]
    for node_name in specialist_nodes:
        builder.add_edge(START, node_name)

    builder.add_edge(specialist_nodes, "validate_evidence")
    builder.add_edge("validate_evidence", "resolve_conflicts")
    builder.add_edge("resolve_conflicts", "compose_recommendation")
    builder.add_edge("compose_recommendation", "collect_metrics")
    builder.add_edge("collect_metrics", END)

    return builder.compile(name="vibefinance-analysis")
