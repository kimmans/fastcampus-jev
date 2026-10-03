"""오픈소스 프로젝트에서 가져온 Jev 활용 패턴 모음.

각 패턴 모듈은 같은 모양의 함수 두 개를 제공한다.

- plan(payload)  -> (state, questions)   Jev 에 보낼 내용을 만든다. 입력 검증도 여기서 한다.
- view(payload, result) -> dict          Jev 답을 화면과 노트북이 함께 쓰는 형태로 정리한다.

Jev 호출은 이 두 함수 사이에 한 번뿐이라, 동기(노트북)와 비동기(서버)가 같은 로직을 쓴다.
"""

from __future__ import annotations

from typing import Any

from jev_agent.jev import JevClient, JevResult
from jev_agent.patterns import actions, compaction, gates, routing

PATTERNS = {
    "compaction": compaction,
    "tool_gate": gates,
    "routing": routing,
    "browser_action": actions,
}


def _finish(view: dict[str, Any], result: JevResult) -> dict[str, Any]:
    return {**view, "latency_ms": round(result.latency_ms), "cost": result.cost}


def run_pattern(jev: JevClient, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """패턴 하나를 동기로 실행한다. 잘못된 입력은 ValueError 로 알린다."""
    pattern = PATTERNS[name]
    result = jev.decide(*pattern.plan(payload))
    return _finish(pattern.view(payload, result), result)


async def arun_pattern(jev: JevClient, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    pattern = PATTERNS[name]
    result = await jev.adecide(*pattern.plan(payload))
    return _finish(pattern.view(payload, result), result)
