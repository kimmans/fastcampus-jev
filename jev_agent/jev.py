"""Jev(TypeSafe System One 모델) 호출 클라이언트.

Jev 는 채팅 모델이 아니다. 텍스트를 생성하지 않고, 우리가 준 선택지 중에서
타입이 정해진 판단(choice / noul / score)과 probability 만 돌려준다.
그래서 ChatOpenAI 같은 채팅 래퍼를 쓰지 않고 Decisions 엔드포인트를 직접 호출한다.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

JEV_URL = "https://openrouter.ai/api/alpha/decisions"
JEV_MODEL = "typesafe/jev-1.13"


# --- 질문 빌더 -------------------------------------------------------------
def choice(instructions: str, options: dict[str, str]) -> dict[str, Any]:
    """여러 선택지 중 하나를 고르는 질문. options 는 {라벨: 설명}."""
    return {"type": "choice", "instructions": instructions, "criteria": options}


def noul(instructions: str, true: str | None = None, false: str | None = None) -> dict[str, Any]:
    """예/아니오 질문. 결과는 '예'일 probability(0~1) 하나다."""
    question: dict[str, Any] = {"type": "noul", "instructions": instructions}
    if true and false:
        question["criteria"] = {"true": true, "false": false}
    return question


def score(instructions: str, levels: list[str]) -> dict[str, Any]:
    """순서가 있는 척도 위의 위치를 묻는 질문. levels 는 낮은 단계부터 적는다."""
    return {"type": "score", "instructions": instructions, "criteria": levels}


# --- 결과 ------------------------------------------------------------------
@dataclass
class JevResult:
    answers: dict[str, dict[str, Any]]
    usage: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0

    def __getitem__(self, key: str) -> dict[str, Any]:
        return self.answers[key]

    @property
    def cost(self) -> float:
        return float(self.usage.get("cost", 0.0))


class JevError(RuntimeError):
    """Jev 호출 실패. 호출부가 안전한 쪽(차단/사람 확인)으로 처리하도록 예외로 알린다."""


class JevClient:
    """Decisions 엔드포인트의 얇은 래퍼. 동기(decide)와 비동기(adecide)를 모두 제공한다."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = JEV_MODEL,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
        async_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise JevError("OPENROUTER_API_KEY 가 설정되어 있지 않습니다. .env 를 확인하세요.")
        self.model = model
        self.timeout = timeout
        self._transport = transport
        self._async_transport = async_transport

    def _request(self, state: Any, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
        if not questions:
            raise JevError("questions 가 비어 있습니다.")
        return {
            "headers": {"Authorization": f"Bearer {self.api_key}"},
            "json": {"model": self.model, "state": state, "questions": questions},
        }

    @staticmethod
    def _parse(response: httpx.Response, started: float) -> JevResult:
        if response.status_code != 200:
            raise JevError(f"Jev 호출 실패 (HTTP {response.status_code}): {response.text[:200]}")
        body = response.json()
        if "answers" not in body:
            raise JevError(f"Jev 응답에 answers 가 없습니다: {str(body)[:200]}")
        return JevResult(
            answers=body["answers"],
            usage=body.get("usage", {}),
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    def decide(self, state: Any, questions: dict[str, dict[str, Any]]) -> JevResult:
        """state(문자열 또는 dict)와 질문 묶음을 보내고 판단을 받는다. 질문은 한 번에 병렬 평가된다."""
        request = self._request(state, questions)
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
                response = client.post(JEV_URL, **request)
        except httpx.HTTPError as exc:
            raise JevError(f"Jev 네트워크 오류: {exc}") from exc
        return self._parse(response, started)

    async def adecide(self, state: Any, questions: dict[str, dict[str, Any]]) -> JevResult:
        request = self._request(state, questions)
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, transport=self._async_transport
            ) as client:
                response = await client.post(JEV_URL, **request)
        except httpx.HTTPError as exc:
            raise JevError(f"Jev 네트워크 오류: {exc}") from exc
        return self._parse(response, started)
