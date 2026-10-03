"""패턴 결과를 화면과 노트북이 함께 쓰는 형태로 만드는 작은 도우미."""

from __future__ import annotations

from typing import Any

MAX_TEXT_CHARS = 4000
MAX_LIST_ITEMS = 30


def stat(label: str, value: Any) -> dict[str, Any]:
    return {"label": label, "value": value}


def row(
    title: str,
    verdict: str,
    tone: str,
    probabilities: dict[str, float] | None = None,
    thresholds: dict[str, float] | None = None,
    body: str = "",
) -> dict[str, Any]:
    """결과 카드 한 장. tone 은 good / warn / bad / neutral 중 하나다."""
    return {
        "title": title,
        "verdict": verdict,
        "tone": tone,
        "probabilities": probabilities or {},
        "thresholds": thresholds or {},
        "body": body,
    }


def require_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' 는 비어 있지 않은 문자열이어야 합니다.")
    if len(value) > MAX_TEXT_CHARS:
        raise ValueError(f"'{key}' 는 {MAX_TEXT_CHARS}자 이하여야 합니다.")
    return value.strip()


def require_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(v, dict) for v in value):
        raise ValueError(f"'{key}' 는 비어 있지 않은 객체 목록이어야 합니다.")
    if len(value) > MAX_LIST_ITEMS:
        raise ValueError(f"'{key}' 는 {MAX_LIST_ITEMS}개 이하여야 합니다.")
    return value
