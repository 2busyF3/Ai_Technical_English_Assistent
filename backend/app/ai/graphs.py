from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class WorkflowState(TypedDict, total=False):
    learner_state: dict[str, Any]
    objective: str
    knowledge: list[dict[str, Any]]
    context: str
    response: dict[str, Any]
    evaluation: dict[str, Any]
    state_update_proposal: dict[str, Any]
    plan: list[dict[str, Any]]


def _load_learner(state: WorkflowState) -> WorkflowState:
    return {"learner_state": state.get("learner_state", {})}


def _retrieve(state: WorkflowState) -> WorkflowState:
    return {"knowledge": state.get("knowledge", [])[:5]}


def _context(state: WorkflowState) -> WorkflowState:
    learner = state.get("learner_state", {})
    return {"context": f"Level={learner.get('cefr', 'B1')}; objective={state.get('objective', '')}"}


def _response(state: WorkflowState) -> WorkflowState:
    return {"response": {"operation": "provider_generate", "context": state.get("context", "")}}


def _placement_update(state: WorkflowState) -> WorkflowState:
    return {"state_update_proposal": {"operation": "validate_placement_evidence"}}


def _lesson_evaluate(state: WorkflowState) -> WorkflowState:
    return {"evaluation": state.get("evaluation", {"operation": "evaluator"})}


def _plan(state: WorkflowState) -> WorkflowState:
    return {"plan": state.get("plan", [])}


def _linear_graph(*nodes: tuple[str, Any]):
    graph = StateGraph(WorkflowState)
    for name, function in nodes:
        graph.add_node(name, function)
    graph.add_edge(START, nodes[0][0])
    for left, right in zip(nodes, nodes[1:], strict=False):
        graph.add_edge(left[0], right[0])
    graph.add_edge(nodes[-1][0], END)
    return graph.compile()


def placement_graph():
    """Adaptive assessment orchestration; deterministic service applies proposals."""
    return _linear_graph(("load_learner", _load_learner), ("evaluate_evidence", _lesson_evaluate), ("propose_update", _placement_update))


def tutor_graph():
    """Bounded tutor-context workflow with provider generation as the final node."""
    return _linear_graph(("load_learner", _load_learner), ("retrieve", _retrieve), ("build_context", _context), ("generate", _response))


def lesson_graph():
    """Multi-skill lesson workflow; persistence remains outside the graph."""
    return _linear_graph(("load_learner", _load_learner), ("retrieve", _retrieve), ("build_context", _context), ("generate_exercise", _response), ("evaluate", _lesson_evaluate), ("propose_update", _placement_update))


def planner_graph():
    """Transforms a deterministic objective set into a persisted-plan proposal."""
    return _linear_graph(("load_learner", _load_learner), ("create_plan", _plan))

