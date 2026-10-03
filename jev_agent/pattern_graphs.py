"""패턴 하나를 노드 하나짜리 LangGraph 그래프로 감싼다. 프론트엔드 탭이 이 그래프를 호출한다.

Jev 호출은 서버에서만 한다. API 키가 브라우저로 나가면 안 되기 때문이다.
"""

from __future__ import annotations

from typing import Any

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from jev_agent.guardrail_compare import acompare
from jev_agent.jev import JevClient, JevError
from jev_agent.patterns import PATTERNS, arun_pattern


class PatternState(TypedDict, total=False):
    payload: dict[str, Any]  # 패턴 입력. 각 패턴의 plan() 이 검증한다.
    output: dict[str, Any] | None
    error: str | None


def build_pattern_graph(name: str, jev: JevClient | None = None):
    """PATTERNS 에 등록된 패턴 하나를 실행하는 그래프를 만든다."""
    if name not in PATTERNS:
        raise ValueError(f"알 수 없는 패턴: {name}")
    load_dotenv()
    client = jev or JevClient()

    async def run_pattern_node(state: PatternState) -> PatternState:
        try:
            output = await arun_pattern(client, name, state.get("payload") or {})
        except (ValueError, JevError) as exc:
            return {"output": None, "error": str(exc)}
        return {"output": output, "error": None}

    graph = StateGraph(PatternState)
    graph.add_node("run_pattern", run_pattern_node)
    graph.add_edge(START, "run_pattern")
    graph.add_edge("run_pattern", END)
    return graph.compile(name=f"jev-pattern-{name}")


def build_guardrail_lab_graph(jev: JevClient | None = None, llm: Any = None):
    """같은 글을 Jev 와 LLM 에 동시에 판정시켜 confidence 와 시간을 비교하는 그래프."""
    load_dotenv()
    client = jev or JevClient()
    if llm is None:
        from jev_agent.agent import build_chat_model  # 순환 import 를 피하려고 여기서 불러온다.

        llm = build_chat_model()

    async def compare_guardrails(state: PatternState) -> PatternState:
        try:
            output = await acompare(client, llm, state.get("payload") or {})
        except (ValueError, JevError) as exc:
            return {"output": None, "error": str(exc)}
        return {"output": output, "error": None}

    graph = StateGraph(PatternState)
    graph.add_node("compare_guardrails", compare_guardrails)
    graph.add_edge(START, "compare_guardrails")
    graph.add_edge("compare_guardrails", END)
    return graph.compile(name="jev-guardrail-lab")


def make_guardrail_lab():
    return build_guardrail_lab_graph()


def make_compaction():
    return build_pattern_graph("compaction")


def make_tool_gate():
    return build_pattern_graph("tool_gate")


def make_routing():
    return build_pattern_graph("routing")


def make_browser_action():
    return build_pattern_graph("browser_action")
