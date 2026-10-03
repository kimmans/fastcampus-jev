"""브라우저 액션 선택: LLM 이 세운 한 단계 목표를 받아, 화면의 어느 요소를 누를지 Jev 가 고른다.

jev-browser(https://github.com/Ying-Kai-Liao/jev-browser)의 역할 분담을 따랐다.
LLM 은 "무엇을 이루고 싶은지"만 말하고, 요소 선택과 완료 판정은 Jev 가 한다.
여기서는 실제 브라우저 없이 화면을 요소 목록으로 표현한다.

- target        choice  이 단계를 위해 조작할 요소 (또는 none)
- done          noul    이 단계의 목표가 이미 이뤄졌는가
- has_error     noul    화면에 오류 메시지가 보이는가
- irreversible  noul    고른 조작이 결제, 삭제, 전송처럼 되돌릴 수 없는가
"""

from __future__ import annotations

from typing import Any

from jev_agent.jev import JevResult, choice, noul
from jev_agent.patterns.view import require_list, require_text, row, stat

NO_TARGET = "none"
DONE_THRESHOLD = 0.8
LIKELY_DONE_THRESHOLD = 0.5
ERROR_THRESHOLD = 0.7
IRREVERSIBLE_THRESHOLD = 0.7
MIN_TARGET_CONFIDENCE = 0.5

SAMPLE_PAGES = [
    {
        "step_goal": "이메일과 비밀번호를 입력했으니 로그인한다",
        "page_title": "로그인",
        "visible_text": "이메일: teddy@example.com  비밀번호: ********",
        "elements": [
            {"id": "e1", "role": "textbox", "label": "이메일"},
            {"id": "e2", "role": "textbox", "label": "비밀번호"},
            {"id": "e3", "role": "button", "label": "로그인"},
            {"id": "e4", "role": "link", "label": "비밀번호 찾기"},
            {"id": "e5", "role": "button", "label": "회원가입"},
        ],
    },
    {
        "step_goal": "장바구니의 상품을 주문한다",
        "page_title": "주문/결제",
        "visible_text": "러닝화 270mm 1개  합계 89,000원  결제 수단: 신용카드",
        "elements": [
            {"id": "e1", "role": "button", "label": "쿠폰 적용"},
            {"id": "e2", "role": "button", "label": "89,000원 결제하기"},
            {"id": "e3", "role": "link", "label": "장바구니로 돌아가기"},
        ],
    },
    {
        "step_goal": "로그인한다",
        "page_title": "마이페이지",
        "visible_text": "테디님, 환영합니다.  주문 내역  적립금 3,200P",
        "elements": [
            {"id": "e1", "role": "link", "label": "주문 내역"},
            {"id": "e2", "role": "button", "label": "로그아웃"},
        ],
    },
    {
        "step_goal": "로그인한다",
        "page_title": "로그인",
        "visible_text": "비밀번호가 올바르지 않습니다. 5회 실패 시 계정이 잠깁니다.",
        "elements": [
            {"id": "e1", "role": "textbox", "label": "비밀번호"},
            {"id": "e2", "role": "button", "label": "로그인"},
        ],
    },
]


def _elements(payload: dict[str, Any]) -> list[dict[str, Any]]:
    elements = require_list(payload, "elements")
    for element in elements:
        if not element.get("id") or not element.get("label"):
            raise ValueError("요소에는 id 와 label 이 있어야 합니다.")
        if element["id"] == NO_TARGET:
            raise ValueError(f"요소 id 로 '{NO_TARGET}' 은 쓸 수 없습니다.")
    return elements


def plan(payload: dict[str, Any]) -> tuple[Any, dict[str, dict[str, Any]]]:
    goal = require_text(payload, "step_goal")
    elements = _elements(payload)
    options = {
        element["id"]: f"{element.get('role', 'element')} '{element['label']}'"
        for element in elements
    }
    options[NO_TARGET] = "조작할 요소가 없다. 목표가 이미 이뤄졌거나 이 화면에서는 진행할 수 없다."
    state = {
        "step_goal": goal,
        "page_title": str(payload.get("page_title", "")),
        "visible_text": str(payload.get("visible_text", "")),
        "elements": [f"{key}: {label}" for key, label in options.items() if key != NO_TARGET],
    }
    return state, {
        "target": choice("이 단계의 목표를 이루려면 지금 어느 요소를 조작해야 하는가?", options),
        "done": noul("현재 화면을 보면 이 단계의 목표가 이미 이뤄졌는가?"),
        "has_error": noul("현재 화면에 오류나 실패를 알리는 메시지가 보이는가?"),
        "irreversible": noul(
            "target 으로 고를 요소를 조작하면 결제, 삭제, 전송처럼 되돌릴 수 없는 일이 일어나는가?",
            true="누르는 순간 돈이 결제되거나, 데이터가 지워지거나, 메시지가 발송된다.",
            false="입력, 이동, 로그인, 조회처럼 다시 되돌리거나 다시 시도할 수 있다.",
        ),
    }


def status_of(target: dict[str, Any], done: float, has_error: float, irreversible: float) -> str:
    """판단 네 개를 에이전트가 따를 상태 하나로 합친다. 순서가 곧 우선순위다."""
    if done >= DONE_THRESHOLD:
        return "done"
    if has_error >= ERROR_THRESHOLD:
        return "stuck"
    if target["choice"] == NO_TARGET and done >= LIKELY_DONE_THRESHOLD:
        return "done"  # 누를 것이 없고 끝났을 가능성이 절반을 넘으면 끝난 것으로 본다.
    if target["choice"] == NO_TARGET or target.get("confidence", 0.0) < MIN_TARGET_CONFIDENCE:
        return "stuck"
    if irreversible >= IRREVERSIBLE_THRESHOLD:
        return "needs_confirmation"
    return "act"


STATUS_TEXT = {
    "done": ("단계 완료, 다음 단계로", "good"),
    "stuck": ("진행 불가, LLM 에 다시 계획 요청", "bad"),
    "needs_confirmation": ("되돌릴 수 없는 조작, 사람 확인 필요", "warn"),
    "act": ("바로 실행", "good"),
}


def view(payload: dict[str, Any], result: JevResult) -> dict[str, Any]:
    target = result["target"]
    done, has_error = result["done"]["noul"], result["has_error"]["noul"]
    irreversible = result["irreversible"]["noul"]
    status = status_of(target, done, has_error, irreversible)
    labels = {element["id"]: element["label"] for element in payload["elements"]}
    target_label = labels.get(target["choice"], "없음")
    text, tone = STATUS_TEXT[status]
    rows = [
        row(
            "조작할 요소",
            f"{target['choice']} · {target_label}",
            "neutral",
            target.get("probabilities", {}),
            body=f"confidence {target.get('confidence', 0.0):.2f} (기준 {MIN_TARGET_CONFIDENCE})",
        ),
        row(
            "이미 완료됨",
            "예" if done >= DONE_THRESHOLD else "아니오",
            "neutral",
            {"done": done},
            {"done": DONE_THRESHOLD},
        ),
        row(
            "오류 표시",
            "있음" if has_error >= ERROR_THRESHOLD else "없음",
            "bad" if has_error >= ERROR_THRESHOLD else "good",
            {"has_error": has_error},
            {"has_error": ERROR_THRESHOLD},
        ),
        row(
            "되돌릴 수 없음",
            "예" if irreversible >= IRREVERSIBLE_THRESHOLD else "아니오",
            "warn" if irreversible >= IRREVERSIBLE_THRESHOLD else "good",
            {"irreversible": irreversible},
            {"irreversible": IRREVERSIBLE_THRESHOLD},
        ),
    ]
    return {
        "stats": [stat("상태", status), stat("다음 행동", text), stat("대상", target_label)],
        "rows": rows,
        "status": status,
        "tone": tone,
        "target": target["choice"],
    }
