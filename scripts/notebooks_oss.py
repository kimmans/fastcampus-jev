"""Notebook sources for the open-source pattern series (07-10). Imported by build_notebooks.py."""

from __future__ import annotations

SETUP = """import sys
sys.path.insert(0, "..")  # 프로젝트 루트의 jev_agent 패키지를 불러오기 위함

import pandas as pd
from dotenv import load_dotenv
load_dotenv("../.env")

from jev_agent.jev import JevClient, choice, noul, score
from jev_agent.patterns import run_pattern

pd.set_option("display.max_colwidth", 60)
jev = JevClient()"""

ROWS_HELPER = '''def rows_table(output: dict) -> pd.DataFrame:
    """패턴 결과의 rows 를 표로 바꾼다. probability 는 큰 순서로 세 개까지 한 칸에 적는다."""
    records = []
    for item in output["rows"]:
        top = sorted(item["probabilities"].items(), key=lambda pair: -pair[1])[:3]
        records.append({
            "항목": item["title"],
            "판정": item["verdict"],
            "probability": ", ".join(f"{name} {value:.2f}" for name, value in top),
        })
    return pd.DataFrame(records)'''

OSS_NOTEBOOKS: dict[str, list[tuple[str, str]]] = {}

# ---------------------------------------------------------------------------
OSS_NOTEBOOKS["07-메모리-압축.ipynb"] = [
    (
        "md",
        """# 07. 오픈소스에서 배우는 Jev 패턴 (1) 메모리 압축

## 이 시리즈에 대해

01~06번에서는 Jev 를 고객지원 에이전트 하나에 붙였습니다. 07~10번은 다른 사람들이 Jev 를 어디에 쓰고 있는지 살펴봅니다. 출발점은 블로그 글 [Jev 활용 프로젝트 정리](https://javaexpert.tistory.com/1840)에 소개된 오픈소스 8개입니다.

그 글의 주장은 한 줄로 줄일 수 있습니다. 에이전트가 하는 일을 **생성**과 **판단**으로 나누고, 큰 LLM 에는 계획과 추론만 맡기고, 반복되는 작은 판단은 판단 전용 모델에 맡기자는 것입니다.

| 프로젝트 | Jev 가 맡는 판단 | 이 튜토리얼에서 |
|---|---|---|
| [fast-jev-compaction](https://github.com/tamaratran/fast-jev-compaction) | 대화 기록에서 무엇을 남기고 지울지 | **07번 (이 노트북)** |
| [pi-jev](https://github.com/y0usaf/pi-jev) | 도구 실행 전 위험 판정, 실행 후 출력 판정 | 08번 |
| [jev-search](https://github.com/superagents-lab/jev-search) | 검색 소스 선택, 결과 관련도 | 09번 |
| [hermes-jev-skills](https://github.com/kerpopule/hermes-jev-skills) | 모델 라우팅, 메시지 분류 등 여러 판단 지점 | 09번 |
| [jev-browser](https://github.com/Ying-Kai-Liao/jev-browser) | 화면에서 어느 요소를 누를지, 단계가 끝났는지 | 10번 |
| [NanoJev](https://github.com/TianyuCodings/NanoJev) | 작은 모델(0.6B)로 probability 분포를 내는 판단 모델 구현 | 10번 끝에서 소개만 |
| [open-alternative-jev](https://github.com/ikermoel/open-alternative-jev) | 공개 가중치 모델로 같은 방식 재현 | 10번 끝에서 소개만 |
| [Reticle](https://github.com/reticlehq/reticle) | 에이전트가 만든 코드의 실행 중 검증 (Jev 연동은 계획 단계) | 10번 끝에서 소개만 |

각 노트북의 코드는 해당 프로젝트의 README 에 적힌 방식을 **참고해서 이 저장소에 새로 작성한 것**입니다. 원 프로젝트의 코드를 가져온 것이 아니고, 기준값 같은 숫자를 인용할 때는 출처가 README 임을 밝힙니다.

같은 내용을 화면에서 눌러 볼 수 있습니다. 앱 왼쪽의 "오픈소스 패턴" 탭들이 이 노트북들과 같은 모듈(`jev_agent/patterns/`)을 씁니다.""",
    ),
    (
        "md",
        """## 배경

Claude Code 같은 코딩 에이전트는 오래 실행됩니다. 파일을 읽고, 명령을 실행하고, 그 결과가 전부 대화 기록에 쌓입니다. 기록이 컨텍스트 한도에 가까워지면 줄여야 합니다.

흔한 방법은 LLM 에게 요약을 시키는 것입니다. 이 방법은 느리고, 요약문이 원문과 달라질 수 있습니다. 파일 경로가 바뀌거나 오류 메시지의 숫자가 틀리게 옮겨지면 에이전트는 틀린 기억으로 일하게 됩니다.

fast-jev-compaction 은 요약하지 않습니다. 도구 호출마다 **남길지, 줄일지, 지울지**만 정합니다. 남은 것은 원문 그대로입니다.

## 직관

이삿짐을 쌀 때와 같습니다. 물건마다 설명서를 새로 쓰지 않습니다. 상자에 넣을지, 일부만 챙길지, 버릴지만 정합니다.

도구 호출 하나에 예/아니오 질문 두 개를 던집니다.

| 질문 | 뜻 |
|---|---|
| `keep_call` | 이 호출이 있었다는 사실을 알아야 하는가 |
| `keep_result` | 결과 원문을 그대로 다시 봐야 하는가 |

| 답 | 처리 |
|---|---|
| `keep_result` 가 기준 이상 | **KEEP** 호출과 결과를 그대로 둔다 |
| `keep_call` 만 기준 이상 | **TRUNCATE** 호출은 두고 결과는 앞부분만 남긴다 |
| 둘 다 기준 미만 | **DROP** 호출과 결과를 모두 지운다 |

기준값은 0.5 입니다 (원 프로젝트 README 의 기본값).""",
    ),
    ("code", SETUP),
    ("code", ROWS_HELPER),
    (
        "md",
        """## 예시 대화

로그인 버그를 고치는 코딩 에이전트의 기록입니다. 도구 호출이 7번 있고, 그중에는 목표와 무관한 CSS 파일 읽기와 긴 설치 로그가 섞여 있습니다.""",
    ),
    (
        "code",
        """from jev_agent.patterns import compaction

print("목표:", compaction.SAMPLE_GOAL, "\\n")
for entry in compaction.SAMPLE_TRANSCRIPT:
    if entry["type"] == "tool":
        print(f"[도구 {entry['id']}] {entry['name']}({entry['args']})  → 결과 {len(entry['result']):,}자")
    else:
        print(f"[{entry['role']}] {entry['content']}")""",
    ),
    (
        "md",
        """## Jev 에 무엇을 보내는가

`plan()` 이 Jev 에 보낼 `state` 와 `questions` 를 만듭니다. 눈여겨볼 점은 **도구 결과 원문을 보내지 않는다**는 것입니다. 결과는 길이만 적은 한 줄로 바뀝니다. 그래서 대화가 아무리 길어도 Jev 에 보내는 양은 작습니다.""",
    ),
    (
        "code",
        """payload = {"goal": compaction.SAMPLE_GOAL, "transcript": compaction.SAMPLE_TRANSCRIPT}
state, questions = compaction.plan(payload)

print("state['conversation']:")
for line in state["conversation"]:
    print("  ", line)
print(f"\\n질문 {len(questions)}개 (도구 호출 {len(questions) // 2}개 × 2). 예:")
print("  call_t4  :", questions["call_t4"]["instructions"])
print("  result_t4:", questions["result_t4"]["instructions"])""",
    ),
    (
        "md",
        """## 실행

질문 14개가 호출 한 번에 처리됩니다.""",
    ),
    (
        "code",
        """output = run_pattern(jev, "compaction", payload)

print({item["label"]: item["value"] for item in output["stats"]}, f"| {output['latency_ms']}ms | ${output['cost']:.6f}")
pd.DataFrame([
    {"도구 호출": item["title"], "판정": item["verdict"],
     "keep_call": round(item["probabilities"]["keep_call"], 2),
     "keep_result": round(item["probabilities"]["keep_result"], 2)}
    for item in output["rows"]
])""",
    ),
    (
        "md",
        """## 실제로 줄이기

판단대로 대화를 줄입니다. KEEP 은 그대로, TRUNCATE 는 결과 앞 120자만, DROP 은 통째로 사라집니다.""",
    ),
    (
        "code",
        """compacted = compaction.compact(compaction.SAMPLE_TRANSCRIPT, output["decisions"])

for entry in compacted:
    if entry["type"] == "tool":
        print(f"[도구 {entry['id']}] {entry['name']} → {entry['result'][:150]!r}")
    else:
        print(f"[{entry['role']}] {entry['content']}")""",
    ),
    (
        "md",
        """## 목표가 바뀌면 판단도 바뀐다

같은 대화에 목표만 "CSS 여백 정리"로 바꿉니다. 앞에서 버렸던 CSS 파일 읽기가 이번에는 중요해지는지 확인합니다.""",
    ),
    (
        "code",
        """css_output = run_pattern(
    jev, "compaction", {"goal": "버튼과 카드의 CSS 여백을 정리한다", "transcript": compaction.SAMPLE_TRANSCRIPT}
)
pd.DataFrame({
    "도구 호출": [item["title"] for item in output["rows"]],
    "목표: 로그인 버그": [item["verdict"] for item in output["rows"]],
    "목표: CSS 정리": [item["verdict"] for item in css_output["rows"]],
})""",
    ),
    (
        "md",
        """## 정리

- 요약문을 쓰지 않고 원문을 남길지 말지만 정합니다. 남은 내용은 원문 그대로라 사실이 바뀌지 않습니다.
- Jev 는 도구 결과 원문을 보지 않고, 호출의 이름과 인자, 결과 길이, 대화 흐름만 보고 판단합니다. 그래서 입력이 작고 빠릅니다.
- 같은 이유로 한계도 있습니다. 결과 안에 무엇이 들어 있는지 모르므로, 이름만 봐서는 중요해 보이지 않는 호출의 결과를 버릴 수 있습니다. 위 표에서 KEEP 으로 나온 항목들의 `keep_result` 가 0.5 를 크게 넘지 못한다면 경계에 가까운 판단이라는 뜻입니다.
- 실제로 쓸 때는 사용자의 첫 요청이나 최근 몇 턴처럼 무조건 남길 항목을 따로 고정해 둡니다. 원 프로젝트도 고정 항목은 질문에서 빼 둡니다.""",
    ),
]

# ---------------------------------------------------------------------------
OSS_NOTEBOOKS["08-도구-게이트와-출력-판정.ipynb"] = [
    (
        "md",
        """# 08. 오픈소스에서 배우는 Jev 패턴 (2) 도구 게이트와 출력 판정

참고 프로젝트: [pi-jev](https://github.com/y0usaf/pi-jev)

## 배경

03번에서 만든 위험 게이트는 질문이 하나였습니다. "사용자가 이 작업을 직접 요청했는가." 환불이나 취소처럼 도구가 정해져 있을 때는 이걸로 충분합니다.

코딩 에이전트는 사정이 다릅니다. 셸 명령은 무엇이든 될 수 있습니다. `pytest` 일 수도 있고 `rm -rf` 일 수도 있고 `.env` 를 외부로 보내는 `curl` 일 수도 있습니다. 위험의 종류가 여러 가지라 질문 하나로는 가릴 수 없습니다.

pi-jev 는 코딩 에이전트 Pi 의 도구 실행 앞뒤에 판단 층을 둡니다.

```
LLM ──▶ [실행 전 게이트] ──▶ 도구 실행 ──▶ [실행 후 판정] ──▶ LLM
         질문 4개, 1회 호출                    질문 2개, 1회 호출
```

## 직관

공항 보안 검색과 같습니다. 검색대는 "위험한가" 하나만 묻지 않습니다. 금속이 있는지, 액체가 있는지, 금지 품목이 있는지를 각각 확인하고 항목마다 기준이 다릅니다.

실행 전 게이트의 질문과 기준값입니다 (pi-jev README 에 적힌 값).

| 질문 | 타입 | 기준 |
|---|---|---|
| 파괴적인 작업인가 | noul | 0.90 |
| 로컬 데이터나 비밀값을 밖으로 보내는가 | noul | 0.70 |
| 사용자가 요청한 범위를 벗어나는가 | noul | 0.85 |
| 원하지 않았다면 피해가 얼마나 큰가 | score (0~3) | 2.50 |

기준이 질문마다 다른 데는 이유가 있습니다. 비밀값 유출은 한 번 일어나면 돌이킬 수 없으니 낮은 probability 에도 경고하고(0.70), 파괴적 작업은 `rm build/` 처럼 흔하고 의도된 경우가 많으니 확신이 높을 때만 경고합니다(0.90).""",
    ),
    ("code", SETUP),
    ("code", ROWS_HELPER),
    (
        "md",
        """## 실행 전 게이트

명령 하나에 질문 네 개가 한 번에 나갑니다.""",
    ),
    (
        "code",
        """from jev_agent.patterns import gates

state, questions = gates.plan({"user_request": "빌드 폴더 정리해 줘", "command": "rm -rf build/"})
print("state:", state)
for name, question in questions.items():
    print(f"  {name:13s} [{question['type']}] {question['instructions']}")""",
    ),
    (
        "code",
        """records = []
for sample in gates.GATE_SAMPLES:
    output = run_pattern(jev, "tool_gate", sample)
    probabilities = {item["title"]: list(item["probabilities"].values())[0] for item in output["rows"][:3]}
    records.append({
        "사용자 요청": sample["user_request"],
        "명령": sample["command"],
        **{name: round(value, 2) for name, value in probabilities.items()},
        "피해(0~3)": output["rows"][3]["title"].split()[2],
        "경고": ", ".join(output["flags"]) or "없음",
    })
pd.DataFrame(records)""",
    ),
    (
        "md",
        """표에서 볼 것이 두 가지 있습니다.

- `rm -rf build/` 는 사용자가 정리를 요청했는데도 "파괴적 작업"으로 경고가 뜹니다. 이 게이트는 요청 여부가 아니라 명령 자체의 성질을 봅니다. 요청 범위를 벗어났는지는 별도 질문이 따로 답합니다.
- 같은 "테스트 돌려 줘" 요청에 `git push --force` 가 나오면 범위 초과로 잡힙니다.""",
    ),
    (
        "md",
        """## 실행 후 판정

도구가 끝난 뒤에는 출력을 봅니다. 질문은 두 개입니다.

| 질문 | 타입 | 기준 | 판정 후 처리 |
|---|---|---|---|
| 출력에 비밀값이 있는가 | noul | 0.90 | "값을 옮겨 적지 말라"는 안내를 붙임 |
| 어떤 종류의 실패인가 | choice (6종) | confidence 0.60 | 실패 유형별 조언을 붙임 |

실패 유형을 가리는 이유는 대응이 다르기 때문입니다. 시간 초과는 다시 시도하면 되지만, 코드 결함은 다시 시도해 봐야 같은 결과가 나옵니다. LLM 이 같은 명령을 계속 재시도하는 흔한 실패를 여기서 끊습니다.""",
    ),
    (
        "code",
        """records = []
for sample in gates.OUTPUT_SAMPLES:
    output = run_pattern(jev, "tool_gate", sample)
    shown = sample["output"] if not output["has_secret"] else sample["output"][:24] + "…(가림)"
    records.append({
        "도구 출력": shown.replace("\\n", " "),
        "비밀값 probability": round(output["rows"][0]["probabilities"]["secret"], 2),
        "실패 유형": output["failure_class"],
        "LLM 에 붙일 조언": output["advice"] or "(없음)",
    })
pd.DataFrame(records)""",
    ),
    (
        "md",
        """## 에이전트에 붙이기

출력 판정을 DeepAgents 미들웨어로 붙입니다. 도구가 끝나면 `wrap_tool_call` 에서 출력을 판정하고, 조언이 있으면 도구 결과 뒤에 덧붙입니다. LLM 은 다음 턴에 이 조언을 읽습니다.

아래 에이전트에는 일부러 실패하는 도구를 하나 줍니다.""",
    ),
    (
        "code",
        '''from deepagents import create_deep_agent
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from jev_agent.agent import build_chat_model
from jev_agent.jev import JevError


@tool
def run_tests(path: str) -> str:
    """주어진 경로의 테스트를 실행하고 결과를 돌려준다."""
    return "ModuleNotFoundError: No module named 'httpx'"


@wrap_tool_call
def judge_tool_output(request, handler):
    output = handler(request)
    if not isinstance(output, ToolMessage):
        return output
    try:
        verdict = run_pattern(jev, "tool_gate", {"output": str(output.content)})
    except (JevError, ValueError):
        return output  # 판정에 실패하면 원래 결과를 그대로 돌려준다
    if not verdict["advice"]:
        return output
    return output.model_copy(update={"content": f"{output.content}\\n\\n[판정 조언] {verdict['advice']}"})


agent = create_deep_agent(
    model=build_chat_model(),
    tools=[run_tests],
    system_prompt="당신은 코딩 도우미입니다. 요청을 받으면 파일을 찾아보지 말고 바로 run_tests 도구를 한 번 호출한 뒤, 결과를 한국어로 짧게 보고합니다. 같은 명령을 반복해서 실행하지 않습니다.",
    middleware=[judge_tool_output],
)
state = agent.invoke(
    {"messages": [{"role": "user", "content": "tests/ 의 테스트를 돌려 주세요."}]},
    {"recursion_limit": 12},
)
for message in state["messages"]:
    if message.type == "tool":
        print("도구 결과:\\n", message.content, "\\n")
print("답변:", state["messages"][-1].content)''',
    ),
    (
        "md",
        """## 03번 게이트와 무엇이 다른가

| | 03번 위험 게이트 | 이 노트북의 게이트 |
|---|---|---|
| 대상 | 미리 정해 둔 위험 도구 (환불, 취소) | 무엇이든 될 수 있는 명령 |
| 질문 | 1개: 사용자가 요청했는가 | 4개: 파괴성, 유출, 범위, 피해 크기 |
| 애매할 때 | `interrupt()` 로 사람에게 | 경고를 붙이고, 설정에 따라 확인 요청 |
| Jev 장애 시 | 사람 확인으로 넘김 (닫힘) | 통과시킴 (열림) |

마지막 행이 설계 차이입니다. pi-jev 는 README 에서 모든 오류를 통과로 처리한다고 밝힙니다. 개발자의 작업 흐름을 막지 않는 것을 우선한 선택입니다. 환불처럼 돈이 나가는 작업이라면 03번처럼 닫히는 쪽이 맞습니다. 어느 쪽이 옳은지는 잘못 통과시켰을 때의 비용이 정합니다.

## 정리

- 위험의 종류가 여러 가지면 질문을 나누고 기준을 따로 둡니다. 질문이 늘어도 호출은 한 번입니다.
- 실행 후 판정은 LLM 이 실패를 어떻게 받아들일지를 바꿉니다. 같은 명령의 무한 재시도를 줄입니다.
- 장애가 났을 때 열 것인지 닫을 것인지는 미리 정해야 하는 설계 결정입니다.""",
    ),
]

# ---------------------------------------------------------------------------
OSS_NOTEBOOKS["09-검색과-모델-라우팅.ipynb"] = [
    (
        "md",
        """# 09. 오픈소스에서 배우는 Jev 패턴 (3) 검색과 모델 라우팅

참고 프로젝트: [jev-search](https://github.com/superagents-lab/jev-search), [hermes-jev-skills](https://github.com/kerpopule/hermes-jev-skills)

## 배경

질문이 하나 들어왔을 때 답을 쓰기 전에 정해야 할 것들이 있습니다.

- 검색이 필요한가, 필요하면 어디서 찾을 것인가
- 얼마나 최근 자료가 필요한가
- 찾아온 결과 중 무엇을 읽을 것인가
- 어느 모델로 답할 것인가

이 결정들은 모두 정해진 option 중 하나를 고르는 일입니다. 그런데 보통은 큰 LLM 이 이것까지 다 합니다. jev-search 는 검색 소스 선택과 결과 관련도 판정을 Jev 에 맡기고, hermes-jev-skills 는 턴마다 어느 모델을 쓸지를 Jev 에 맡깁니다.

## 직관

도서관 안내 데스크입니다. 사서는 질문을 듣고 "그건 3층 논문 서가", "그건 신문 열람실"이라고 안내합니다. 책 내용을 설명해 주지는 않습니다. 어디로 갈지만 빠르게 정해 줍니다.

```
질의 ──▶ Jev 1회 호출 ─┬─ source      어느 소스에서 찾을까
                       ├─ time_range  얼마나 최근 자료가 필요한가
                       ├─ difficulty  어느 모델로 답할까
                       └─ rel_0..N    후보 결과 각각의 관련도
                       ▼
        고른 결과만 고른 모델에 넘겨 답변 작성 (LLM)
```

여기서는 실제 검색 엔진을 붙이지 않고, 후보 결과 다섯 개를 미리 정해 둡니다. 판단 부분만 보기 위해서입니다.""",
    ),
    ("code", SETUP),
    ("code", ROWS_HELPER),
    (
        "md",
        """## option 구성

검색 소스 option 은 일곱 개입니다. `no_search` 가 들어 있어서 검색이 필요 없다는 판단도 같은 질문으로 받습니다. jev-search 는 README 기준으로 12개 소스를 다루는데, 여기서는 종류별로 하나씩 묶어 단순하게 했습니다.""",
    ),
    (
        "code",
        """from jev_agent.patterns import routing

for name, description in routing.SOURCES.items():
    print(f"{name:13s} {description}")
print()
for index, item in enumerate(routing.SAMPLE_RESULTS):
    print(f"후보 {index}: {item['title']}")""",
    ),
    ("md", """## 질의 하나 자세히 보기"""),
    (
        "code",
        """query = routing.SAMPLE_QUERIES[0]
output = run_pattern(jev, "routing", {"query": query, "results": routing.SAMPLE_RESULTS})

print("질의:", query)
print({item["label"]: item["value"] for item in output["stats"]}, f"| {output['latency_ms']}ms | ${output['cost']:.6f}")
rows_table(output)""",
    ),
    (
        "md",
        """질문 여덟 개(소스, 기간, 난이도, 후보 다섯 개의 관련도)가 호출 한 번으로 끝났습니다. 관련도는 `score` 질문이라 0~2 사이 값이 나오고, 1.5 이상인 결과만 씁니다.""",
    ),
    ("md", """## 여러 질의 비교"""),
    (
        "code",
        """records = []
for query in routing.SAMPLE_QUERIES:
    output = run_pattern(jev, "routing", {"query": query, "results": routing.SAMPLE_RESULTS})
    records.append({
        "질의": query,
        "소스": output["source"],
        "기간": output["stats"][1]["value"],
        "모델": output["model"],
        "쓸 결과": ", ".join(output["kept"]) or "(없음)",
        "지연(ms)": output["latency_ms"],
    })
pd.DataFrame(records)""",
    ),
    (
        "md",
        """## 모델 라우팅을 실제로 적용하기

난이도 판정으로 채팅 모델을 고릅니다. 쉬운 질문에 큰 모델을 쓰지 않는 것만으로 비용이 크게 줄어듭니다. 아래에서는 세 단계에 OpenRouter 모델을 하나씩 대응시킵니다.""",
    ),
    (
        "code",
        """import time
from jev_agent.agent import build_chat_model

MODEL_IDS = {
    "작은 모델": "openai/gpt-5.4-nano",
    "중간 모델": "openai/gpt-5.4-mini",
    "큰 모델": "openai/gpt-5.4",
}

def answer_with_routing(query: str) -> dict:
    routed = run_pattern(jev, "routing", {"query": query, "results": routing.SAMPLE_RESULTS})
    model_id = MODEL_IDS[routed["model"]]
    started = time.perf_counter()
    reply = build_chat_model(model_id).invoke(query + "\\n\\n두 문장 이내로 답하세요.")
    return {
        "질의": query,
        "고른 모델": model_id,
        "Jev 지연(ms)": routed["latency_ms"],
        "LLM 지연(ms)": round((time.perf_counter() - started) * 1000),
        "답변": reply.content,
    }

pd.DataFrame([
    answer_with_routing("안녕하세요"),
    answer_with_routing("파이썬에서 리스트를 정렬하는 방법은?"),
    answer_with_routing("분산 락을 Redis 로 구현할 때 생기는 문제와 대안을 설계 관점에서 비교해 줘"),
])""",
    ),
    (
        "md",
        """## 메시지 분류도 같은 방식

hermes-jev-skills 는 들어온 메시지를 분류하는 데도 Jev 를 씁니다. 얼마나 급한지, 어떤 종류인지, 사람이 봐야 하는지를 한 번에 묻습니다. 패턴 모듈 없이 `jev.decide` 로 바로 써 봅니다.""",
    ),
    (
        "code",
        """TRIAGE_QUESTIONS = {
    "urgency": score("이 메시지는 얼마나 급한가?", ["나중에 봐도 된다", "오늘 안에 봐야 한다", "지금 바로 봐야 한다"]),
    "kind": choice("이 메시지는 어떤 종류인가?", {
        "incident": "서비스 장애나 오류 보고",
        "question": "사용법이나 정보에 대한 질문",
        "request": "작업이나 변경 요청",
        "fyi": "참고용 공지나 공유",
    }),
    "needs_human": noul("사람이 직접 확인하고 결정해야 하는 메시지인가?"),
}
messages = [
    "결제 API 가 5분째 500 을 반환하고 있습니다. 주문이 전부 실패 중입니다.",
    "다음 주 수요일 팀 회식 장소 투표 부탁드려요.",
    "스테이징 DB 비밀번호 좀 바꿔 주실 수 있나요?",
    "참고로 어제 배포한 버전 릴리스 노트 공유합니다.",
]
records = []
for message in messages:
    result = jev.decide(message, TRIAGE_QUESTIONS)
    records.append({
        "메시지": message,
        "긴급도(0~2)": round(result["urgency"]["score"], 2),
        "종류": result["kind"]["choice"],
        "사람 확인": round(result["needs_human"]["noul"], 2),
        "지연(ms)": round(result.latency_ms),
    })
pd.DataFrame(records)""",
    ),
    (
        "md",
        """## 정리

- 답을 쓰기 전의 결정(어디서 찾을지, 무엇을 읽을지, 어느 모델로 답할지)은 option 중 하나를 고르는 판단이라 Jev 에 맡길 수 있습니다.
- 질문이 여럿이어도 호출은 한 번이라, 라우팅을 추가해도 지연이 수백 ms 수준에 머뭅니다.
- 관련도 숫자는 모델의 판단이지 검증된 정확도가 아닙니다. jev-search README 도 이 점을 명시합니다. 중요한 용도라면 05번처럼 라벨 데이터로 직접 측정해야 합니다.
- 난이도 판정이 틀리면 어려운 질문이 작은 모델로 갑니다. 처음에는 기준을 보수적으로(큰 모델 쪽으로) 잡고, 로그를 보며 조정하는 것이 안전합니다.""",
    ),
]

# ---------------------------------------------------------------------------
OSS_NOTEBOOKS["10-브라우저-액션-선택.ipynb"] = [
    (
        "md",
        """# 10. 오픈소스에서 배우는 Jev 패턴 (4) 브라우저 액션 선택

참고 프로젝트: [jev-browser](https://github.com/Ying-Kai-Liao/jev-browser)

## 배경

브라우저를 조작하는 에이전트는 보통 한 단계마다 큰 LLM 에 화면 전체를 보여 주고 "다음에 뭘 누를까"를 묻습니다. 화면 하나가 수천 토큰이고 작업 하나에 수십 단계가 걸리니 느리고 비쌉니다.

그런데 "다음에 뭘 누를까"는 화면에 있는 요소 중 하나를 고르는 일입니다. option 이 정해져 있습니다.

jev-browser 는 역할을 이렇게 나눕니다.

| | 하는 일 |
|---|---|
| LLM | 이루고 싶은 결과를 한 단계씩 말한다. 입력할 글자를 넘겨준다. |
| 코드 | 화면을 요소 목록으로 정리한다 (역할, 라벨, 상태, 보이는 글). |
| Jev | 어느 요소를 조작할지, 단계가 끝났는지, 오류가 났는지, 되돌릴 수 없는 조작인지 답한다. |

README 에 따르면 Jev 호출 한 번이 약 300ms 이고 한 단계에 2~4번 호출합니다.

## 직관

택시와 같습니다. 승객(LLM)은 "서울역 가 주세요"라고 목적지만 말합니다. 어느 차선으로 갈지, 지금 좌회전할지는 기사(Jev)가 매 순간 정합니다. 승객이 교차로마다 지시하지 않습니다.

```
LLM: "로그인한다" ──▶ 화면 요소 목록 ──▶ Jev ─┬─ target        어느 요소?
                                              ├─ done          이미 끝났나?
                                              ├─ has_error     오류가 보이나?
                                              └─ irreversible  되돌릴 수 없나?
```

네 판단을 합쳐 상태 하나를 만듭니다.

| 상태 | 조건 | 다음 행동 |
|---|---|---|
| `done` | 이미 끝남 (또는 누를 요소가 없고 끝났을 probability 가 절반 이상) | 다음 단계로 |
| `stuck` | 오류가 보이거나, 누를 요소가 없거나, 확신이 낮음 | LLM 에 다시 계획 요청 |
| `needs_confirmation` | 되돌릴 수 없는 조작 | 사람 확인 |
| `act` | 그 외 | 바로 실행 |

이 노트북은 실제 브라우저 없이 화면을 요소 목록으로 흉내 냅니다.""",
    ),
    ("code", SETUP),
    ("code", ROWS_HELPER),
    (
        "md",
        """## Jev 에 무엇을 보내는가

화면 요소가 그대로 `choice` 의 option 이 됩니다. option 에 없는 요소는 고를 수 없으므로, 없는 버튼을 누르려는 일이 생기지 않습니다. 누를 것이 없을 때를 위한 `none` option 이 하나 더 있습니다.""",
    ),
    (
        "code",
        """from jev_agent.patterns import actions

page = actions.SAMPLE_PAGES[0]
state, questions = actions.plan(page)

print("step_goal:", state["step_goal"])
print("elements :", state["elements"])
print("target option:", list(questions["target"]["criteria"]))""",
    ),
    ("md", """## 화면 네 개에서 실행"""),
    (
        "code",
        """records = []
for page in actions.SAMPLE_PAGES:
    output = run_pattern(jev, "browser_action", page)
    by_title = {item["title"]: list(item["probabilities"].values())[0] for item in output["rows"][1:]}
    records.append({
        "단계 목표": page["step_goal"],
        "화면": page["page_title"],
        "고른 요소": output["rows"][0]["verdict"],
        "완료": round(by_title["이미 완료됨"], 2),
        "오류": round(by_title["오류 표시"], 2),
        "비가역": round(by_title["되돌릴 수 없음"], 2),
        "상태": output["status"],
        "지연(ms)": output["latency_ms"],
    })
pd.DataFrame(records)""",
    ),
    (
        "md",
        """네 화면이 네 가지 상태를 하나씩 보여 주는지 확인하세요. 결제 버튼은 고를 요소가 분명하더라도 바로 누르지 않고 `needs_confirmation` 으로 멈춰야 합니다.""",
    ),
    (
        "md",
        """## 작은 루프로 묶기

이제 LLM 과 Jev 를 묶어 봅니다. LLM 은 처음에 한 번만 호출해서 단계를 나누고, 그 뒤 화면 조작은 전부 Jev 가 정합니다.

화면은 아래처럼 흉내 냅니다. `next` 는 그 요소를 누르면 어느 화면으로 가는지입니다.""",
    ),
    (
        "code",
        """SITE = {
    "login": {
        "page_title": "로그인",
        "visible_text": "이메일: teddy@example.com  비밀번호: ********",
        "elements": [
            {"id": "e1", "role": "button", "label": "로그인"},
            {"id": "e2", "role": "link", "label": "비밀번호 찾기"},
        ],
        "next": {"e1": "home"},
    },
    "home": {
        "page_title": "마이페이지",
        "visible_text": "테디님, 환영합니다.  적립금 3,200P",
        "elements": [
            {"id": "e1", "role": "link", "label": "주문 내역"},
            {"id": "e2", "role": "link", "label": "장바구니 (1)"},
            {"id": "e3", "role": "button", "label": "로그아웃"},
        ],
        "next": {"e2": "cart"},
    },
    "cart": {
        "page_title": "장바구니",
        "visible_text": "러닝화 270mm 1개  합계 89,000원  결제 수단: 신용카드",
        "elements": [
            {"id": "e1", "role": "button", "label": "쿠폰 적용"},
            {"id": "e2", "role": "button", "label": "89,000원 결제하기"},
        ],
        "next": {},
    },
}""",
    ),
    (
        "code",
        """from pydantic import BaseModel, Field
from jev_agent.agent import build_chat_model


class BrowserPlan(BaseModel):
    steps: list[str] = Field(description="각 단계에서 이루려는 결과를 한 문장씩. 어느 버튼을 누를지는 적지 않는다.")


planner = build_chat_model().with_structured_output(BrowserPlan)
plan = planner.invoke(
    "쇼핑몰 웹사이트에서 '로그인한 뒤 장바구니에 담긴 상품을 결제'하려고 합니다. "
    "지금은 로그인 화면이고 이메일과 비밀번호는 이미 입력되어 있습니다. "
    "이 작업을 정확히 3단계로 나누어 주세요. 각 단계는 '~한다'로 끝나는 15자 안팎의 짧은 문장 하나로, "
    "이루려는 일 하나만 적습니다. 어떤 버튼을 누르는지나 확인 절차는 적지 않습니다. "
    "형식 예: '로그인한다', '장바구니 화면으로 이동한다', '장바구니의 상품을 결제한다'."
)
plan.steps""",
    ),
    (
        "code",
        """MAX_ACTIONS_PER_STEP = 3  # 한 단계에서 조작을 반복할 수 있는 횟수의 상한

current = "login"
jev_calls, jev_ms = 0, 0
for step in plan.steps:
    print(f"\\n단계: {step}")
    for _ in range(MAX_ACTIONS_PER_STEP):
        screen = SITE[current]
        output = run_pattern(jev, "browser_action", {"step_goal": step, **screen})
        jev_calls, jev_ms = jev_calls + 1, jev_ms + output["latency_ms"]
        print(f"  [{screen['page_title']}] 상태={output['status']}  대상={output['rows'][0]['verdict']}")
        if output["status"] != "act":
            break
        current = screen["next"].get(output["target"], current)
    if output["status"] in ("stuck", "needs_confirmation"):
        print(f"  → 여기서 멈춥니다: {output['stats'][1]['value']}")
        break

print(f"\\nLLM 호출 1회(계획), Jev 호출 {jev_calls}회, Jev 지연 합계 {jev_ms}ms")""",
    ),
    (
        "md",
        """LLM 이 적은 단계 문장은 실행마다 조금씩 달라지므로 위 출력도 달라질 수 있습니다.

단계 문장의 모양이 Jev 판단에 영향을 줍니다. 이 노트북을 만들면서 확인한 바로는 "로그인한다"처럼 짧게 할 일을 적으면 요소 선택 confidence 가 0.99 였고, "로그인이 완료되어 계정에 접속한 상태다"처럼 도달 상태를 길게 적으면 0.49 로 떨어져 `stuck` 이 됐습니다. 그래서 위 프롬프트는 LLM 에 문장 형식을 정해 줍니다. Jev 에 넘기는 글은 사람이 읽기 좋은 문장보다 판단하기 쉬운 문장이어야 합니다.

확인할 것은 두 가지입니다. 화면 이동은 Jev 판단만으로 이뤄졌는지, 그리고 결제 버튼 앞에서 멈췄는지입니다.

## 정리

- LLM 은 목표를 말하고 Jev 는 조작을 고릅니다. LLM 호출 횟수가 단계 수와 무관해집니다.
- 화면 요소가 그대로 option 이 되므로 없는 요소를 누르려는 일이 생기지 않습니다.
- 완료 판정을 따로 묻는 것이 중요합니다. 에이전트가 끝나지 않았는데 끝났다고 하는 것이 가장 위험한 실패이기 때문입니다. jev-browser README 는 실제 작업 42건 중 40건 성공, 잘못된 완료 선언 0건이라고 적고 있습니다 (README 에 적힌 수치이며 이 튜토리얼에서 재현하지 않았습니다).
- 한계도 분명합니다. 화면을 요소 목록으로 잘 정리하는 코드가 먼저 있어야 하고, 글자를 입력하는 일은 여전히 LLM 이 값을 줘야 합니다.

---

## 시리즈를 마치며: 나머지 세 프로젝트

블로그 글의 8개 중 세 개는 노트북으로 만들지 않았습니다.

**[NanoJev](https://github.com/TianyuCodings/NanoJev), [open-alternative-jev](https://github.com/ikermoel/open-alternative-jev).** Jev 같은 판단 모델을 직접 만들거나 공개 가중치 모델(Qwen 등)로 재현하는 프로젝트입니다. 핵심 생각은 같습니다. 텍스트를 생성하지 않고, option 각각에 대한 probability 를 바로 읽어 냅니다. 로컬 GPU 와 모델 가중치가 필요해 이 튜토리얼에서는 실행하지 않았습니다. API 에 데이터를 보낼 수 없는 환경이라면 이쪽이 대안입니다.

**[Reticle](https://github.com/reticlehq/reticle).** 에이전트가 만든 코드를 실제로 실행하면서 화면, 네트워크, 콘솔을 관찰해 검증하는 도구입니다. 블로그 글에 따르면 Jev 연동은 아직 계획 단계입니다. 판단 모델과는 별개로, "에이전트의 말이 아니라 실제 동작으로 확인한다"는 방향이 이 시리즈의 주제와 닿아 있습니다.

## 네 가지 패턴에 공통된 것

| | Jev 에 보내는 것 | 받는 판단 | LLM 이 여전히 하는 일 |
|---|---|---|---|
| 07 메모리 압축 | 결과를 뺀 대화 요약 | 호출별 keep probability 2개 | 줄어든 대화로 작업 계속 |
| 08 도구 게이트 | 명령 또는 출력 | 위험 4종, 실패 유형 | 명령 작성, 조언 읽고 대응 |
| 09 라우팅 | 질의와 후보 결과 | 소스, 기간, 난이도, 관련도 | 고른 결과로 답변 작성 |
| 10 브라우저 액션 | 단계 목표와 요소 목록 | 대상, 완료, 오류, 비가역 | 단계 계획, 입력값 작성 |

모두 같은 구조입니다. **option 을 코드로 만들고, Jev 가 고르고, probability 와 기준값으로 분기합니다.** 문장을 쓰는 일만 LLM 에 남깁니다.""",
    ),
]
