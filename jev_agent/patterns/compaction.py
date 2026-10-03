"""메모리 압축: 긴 에이전트 대화에서 도구 호출별로 KEEP / TRUNCATE / DROP 을 정한다.

fast-jev-compaction(https://github.com/tamaratran/fast-jev-compaction)의 방식을 따랐다.
요약문을 새로 쓰지 않고 원문을 남길지 말지만 정하므로, 요약 과정에서 사실이 바뀔 일이 없다.

도구 호출마다 noul 질문 두 개를 던진다.
- keep_call:   이 호출이 있었다는 사실이 이후 작업에 필요한가
- keep_result: 결과 원문이 그대로 필요한가 (다시 실행해서는 대신할 수 없는가)

keep_result >= 기준  -> KEEP      호출과 결과를 그대로 둔다
keep_call   >= 기준  -> TRUNCATE  호출은 두고 결과는 앞부분만 남긴다
그 외                -> DROP      호출과 결과를 모두 지운다
"""

from __future__ import annotations

from typing import Any

from jev_agent.jev import JevResult, noul
from jev_agent.patterns.view import require_list, require_text, row, stat

KEEP_THRESHOLD = 0.5
TRUNCATE_HEAD_CHARS = 120
TONES = {"KEEP": "good", "TRUNCATE": "warn", "DROP": "bad"}

_LOG_LINE = "Collecting package metadata ... done. Resolving dependencies ... done. "
_CSS_LINE = ".btn { padding: 8px 12px; border-radius: 6px; } .card { margin: 16px; } "

SAMPLE_GOAL = "로그인 API 가 500 을 반환하는 버그를 고치고 테스트를 통과시킨다"
SAMPLE_TRANSCRIPT: list[dict[str, Any]] = [
    {"type": "text", "role": "user", "content": "로그인하면 500 이 나요. 고쳐 주세요."},
    {
        "type": "tool",
        "id": "t1",
        "name": "list_files",
        "args": {"path": "."},
        "result": "README.md  pyproject.toml  src/  tests/  static/  docs/  " * 6,
    },
    {
        "type": "tool",
        "id": "t2",
        "name": "read_file",
        "args": {"path": "static/theme.css"},
        "result": _CSS_LINE * 20,
    },
    {
        "type": "tool",
        "id": "t3",
        "name": "grep",
        "args": {"pattern": "def login", "path": "src/"},
        "result": "src/auth/routes.py:41:def login(payload: LoginRequest):",
    },
    {
        "type": "tool",
        "id": "t4",
        "name": "read_file",
        "args": {"path": "src/auth/routes.py"},
        "result": (
            "def login(payload: LoginRequest):\n"
            "    user = repo.find_by_email(payload.email)\n"
            "    if not verify(payload.password, user.password_hash):  # user 가 None 이면 여기서 터진다\n"
            "        raise HTTPException(401)\n"
            "    return issue_token(user.id)\n"
        ),
    },
    {
        "type": "tool",
        "id": "t5",
        "name": "run_shell",
        "args": {"command": "pip install -e ."},
        "result": _LOG_LINE * 25 + "Successfully installed app-0.1.0",
    },
    {
        "type": "tool",
        "id": "t6",
        "name": "run_tests",
        "args": {"path": "tests/test_login.py"},
        "result": (
            "FAILED tests/test_login.py::test_unknown_email_returns_401\n"
            "AttributeError: 'NoneType' object has no attribute 'password_hash'\n"
            "1 failed, 3 passed"
        ),
    },
    {"type": "text", "role": "assistant", "content": "user 가 None 일 때의 처리가 빠져 있습니다."},
    {
        "type": "tool",
        "id": "t7",
        "name": "edit_file",
        "args": {"path": "src/auth/routes.py", "change": "user 가 None 이면 401 반환"},
        "result": "1 file changed, 2 insertions(+)",
    },
]


def _render(transcript: list[dict[str, Any]]) -> list[str]:
    """Jev 에 보낼 대화. 도구 결과 원문은 길이만 남기고 뺀다."""
    lines = []
    for entry in transcript:
        if entry.get("type") == "tool":
            lines.append(
                f"[tool {entry['id']}] {entry['name']}({entry.get('args', {})}) "
                f"-> ok, {len(str(entry.get('result', '')))} chars (omitted)"
            )
        else:
            lines.append(f"[{entry.get('role', 'user')}] {entry.get('content', '')}")
    return lines


def _tool_entries(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tools = [entry for entry in transcript if entry.get("type") == "tool"]
    if not tools:
        raise ValueError("transcript 에 도구 호출(type='tool')이 하나 이상 있어야 합니다.")
    for entry in tools:
        if not entry.get("id") or not entry.get("name"):
            raise ValueError("도구 호출에는 id 와 name 이 있어야 합니다.")
    return tools


def plan(payload: dict[str, Any]) -> tuple[Any, dict[str, dict[str, Any]]]:
    goal = require_text(payload, "goal")
    transcript = require_list(payload, "transcript")
    questions: dict[str, dict[str, Any]] = {}
    for entry in _tool_entries(transcript):
        questions[f"call_{entry['id']}"] = noul(
            f"goal 에 적힌 목표를 이루려면 도구 호출 {entry['id']} 이 있었다는 사실을 알아야 하는가?",
            true="goal 과 관련된 파일이나 명령을 다룬 호출이라, 무엇을 했는지 알아야 한다.",
            false="goal 과 무관한 파일이나 명령을 다룬 호출이다.",
        )
        questions[f"result_{entry['id']}"] = noul(
            f"goal 에 적힌 목표를 이루려면 도구 호출 {entry['id']} 의 결과 원문을 다시 읽어야 하는가?",
            true="goal 에서 고치려는 바로 그 파일의 내용이거나, goal 과 직접 관련된 오류 메시지다.",
            false="설치 로그, 파일 목록, goal 과 무관한 파일처럼 다시 볼 일이 없는 내용이다.",
        )
    return {"goal": goal, "conversation": _render(transcript)}, questions


def decide(keep_call: float, keep_result: float) -> str:
    if keep_result >= KEEP_THRESHOLD:
        return "KEEP"
    return "TRUNCATE" if keep_call >= KEEP_THRESHOLD else "DROP"


def compact(transcript: list[dict[str, Any]], decisions: dict[str, str]) -> list[dict[str, Any]]:
    """판단대로 대화를 줄인다. 원본 리스트는 바꾸지 않는다."""
    compacted = []
    for entry in transcript:
        decision = decisions.get(entry.get("id", ""), "KEEP")
        if entry.get("type") != "tool" or decision == "KEEP":
            compacted.append(entry)
        elif decision == "TRUNCATE":
            result = str(entry.get("result", ""))
            if len(result) > TRUNCATE_HEAD_CHARS:  # 이미 짧은 결과는 자를 것이 없다.
                note = f" …(이하 {len(result) - TRUNCATE_HEAD_CHARS}자 생략)"
                result = result[:TRUNCATE_HEAD_CHARS] + note
            compacted.append({**entry, "result": result})
    return compacted


def _size(transcript: list[dict[str, Any]]) -> int:
    return sum(len(str(e.get("result", ""))) + len(str(e.get("content", ""))) for e in transcript)


def view(payload: dict[str, Any], result: JevResult) -> dict[str, Any]:
    transcript = payload["transcript"]
    rows, decisions = [], {}
    for entry in _tool_entries(transcript):
        keep_call = result[f"call_{entry['id']}"]["noul"]
        keep_result = result[f"result_{entry['id']}"]["noul"]
        decision = decide(keep_call, keep_result)
        decisions[entry["id"]] = decision
        rows.append(
            row(
                f"{entry['name']}({entry.get('args', {})})",
                decision,
                TONES[decision],
                {"keep_call": keep_call, "keep_result": keep_result},
                {"keep_call": KEEP_THRESHOLD, "keep_result": KEEP_THRESHOLD},
                f"결과 {len(str(entry.get('result', ''))):,}자",
            )
        )
    before, after = _size(transcript), _size(compact(transcript, decisions))
    saved = round((1 - after / before) * 100) if before else 0
    return {
        "stats": [
            stat("압축 전", f"{before:,}자"),
            stat("압축 후", f"{after:,}자"),
            stat("절감", f"{saved}%"),
            stat("질문 수", len(rows) * 2),
        ],
        "rows": rows,
        "decisions": decisions,
    }
