"""Notebook source for 00 (how Jev works: principle and structure, from the official TypeSafe docs).

Imported by build_notebooks.py. Prose that states measured numbers was written after executing
the notebook; use sync_notebook_markdown.py for prose-only edits so saved outputs survive.
"""

from __future__ import annotations

PRINCIPLES_SETUP = """import sys
sys.path.insert(0, "..")  # 프로젝트 루트의 jev_agent 패키지를 불러오기 위함

import json, statistics
import pandas as pd
from dotenv import load_dotenv
load_dotenv("../.env")

from jev_agent.jev import JevClient, choice, noul, score

pd.set_option("display.max_colwidth", 70)
jev = JevClient()"""

PRINCIPLES_NOTEBOOK: list[tuple[str, str]] = [
    (
        "md",
        """# 00. Jev 의 원리와 구조

**비법노트 주주총회 · 테디노트**

이 노트북은 시리즈의 출발점입니다. 01번부터는 Jev 를 "어떻게 쓰는가"를 다루고, 여기서는 그 전에 "Jev 가 무엇이고 왜 그렇게 동작하는가"를 정리합니다.

내용은 TypeSafe 의 공식 자료([typesafe.ai](https://typesafe.ai/), [docs.typesafe.ai](https://docs.typesafe.ai/))에서 가져왔습니다. 공식 문서가 말한 것을 옮기는 데서 그치지 않고, 확인할 수 있는 것은 실제 API 를 호출해 직접 확인합니다.

## 배경: LLM 에게 판단을 시킬 때 생기는 일

에이전트를 만들다 보면 글을 쓰는 일보다 고르는 일이 훨씬 많습니다.

- 이 요청에 어떤 도구를 쓸까
- 이 입력은 공격인가
- 이 환불을 자동으로 처리해도 되나
- 검색 결과 다섯 개 중 어느 것이 관련 있나

지금은 이런 판단도 LLM 에게 시킵니다. 그러면 글을 쓰도록 만든 모델에게 판단을 글로 쓰게 하고, 그 글을 다시 읽어 판단으로 되돌리는 과정이 생깁니다. 공식 문서는 이것을 이렇게 표현합니다.

> you are coercing a text-generation system into outputting structured decisions, then parsing the results back into something your code can depend on.
> (글을 생성하는 시스템에게 억지로 구조화된 판단을 출력하게 하고, 그 결과를 다시 코드가 믿고 쓸 수 있는 형태로 파싱하고 있다.)

이 과정에서 세 가지 비용이 생깁니다.

| 비용 | 왜 생기나 |
|---|---|
| 느립니다 | 답을 토큰 하나씩 차례로 만듭니다. "refund" 한 단어를 얻으려 해도 JSON 괄호와 따옴표까지 생성합니다 |
| 형식이 깨질 수 있습니다 | option 에 없는 답을 쓰거나 JSON 을 잘못 닫을 수 있어, 검증과 재시도 코드가 붙습니다 |
| 얼마나 확신하는지 알 수 없습니다 | "confidence 를 적어 줘"라고 하면 숫자를 적어 주지만, 그 숫자가 실제 정답률과 맞는다는 보장이 없습니다 (11번에서 직접 확인합니다) |

## System One 이라는 이름

Jev 는 TypeSafe 가 "System One 모델"이라고 부르는 종류의 첫 모델입니다. 이름은 대니얼 카너먼의 책 『생각에 관한 생각』에서 왔습니다.

| | 시스템 1 | 시스템 2 |
|---|---|---|
| 생각의 방식 | 빠르고 직관적 | 느리고 신중함 |
| 사람의 예 | 얼굴을 보고 화났는지 알아채기 | 17 × 24 를 암산하기 |
| AI 에서 | Jev: 정해진 option 안에서 즉시 판단 | LLM: 추론하고, 계획하고, 글을 씀 |

Jev 는 LLM 을 대체하지 않습니다. 에이전트 안에서 빠른 판단이 필요한 지점만 맡습니다. 이 시리즈의 부제가 "판단은 Jev 에게, 말은 LLM 에게"인 이유입니다.

## 직관: 서술형 시험과 객관식 채점기

같은 질문을 두 방식으로 물어 봅니다.

**서술형 (LLM)**: "이 고객 글의 의도가 무엇인지 쓰시오."
학생은 답안을 한 글자씩 씁니다. 답이 길어질 수 있고, 문제에서 묻지 않은 내용을 쓸 수 있고, 채점자가 답안을 읽고 해석해야 합니다.

**객관식 (Jev)**: "이 고객 글의 의도는? ① 환불 ② 배송 ③ 칭찬"
답은 반드시 ①②③ 중 하나입니다. 여기에 더해 Jev 는 "①일 가능성 90%, ②일 가능성 8%, ③일 가능성 2%"처럼 option 마다 probability 를 함께 냅니다.

```
LLM   글 ─▶ [토큰 1] ─▶ [토큰 2] ─▶ ... ─▶ [토큰 N] ─▶ 문자열 ─▶ 파싱 ─▶ 검증 ─▶ 판단
            (앞 토큰을 보고 다음 토큰을 만든다. 차례로 N 번)

Jev   state + 질문들 ─▶ [한 번의 계산] ─▶ 타입이 정해진 답 + option 별 probability
```

아래에서 이 그림의 각 부분을 실제 호출로 확인합니다.""",
    ),
    ("code", PRINCIPLES_SETUP),
    (
        "md",
        """## 구조 1. 입력은 `state` 와 `questions`, 출력은 타입이 정해진 답

Jev 호출에는 두 가지가 들어갑니다.

- **`state`**: 판단의 근거가 되는 내용입니다. 글 한 줄일 수도 있고 JSON 객체일 수도 있습니다.
- **`questions`**: 그 `state` 에 대해 묻고 싶은 질문들입니다. 질문마다 타입이 있습니다.

질문 타입은 세 가지뿐입니다. 공식 문서는 이것을 primitive라고 부릅니다.

| 타입 | 묻는 것 | 돌려주는 것 |
|---|---|---|
| `choice` | 이 option 들 중 어느 것인가 | 고른 option, option 별 probability, confidence |
| `score` | 순서가 있는 단계 중 어디쯤인가 | probability 로 가중 평균한 점수, 단계별 probability, confidence |
| `noul` | 이 조건이 성립하는가 | 0~1 사이 숫자 하나 (예일 probability) |

세 타입을 한 번에 보내고 응답을 그대로 출력해 봅니다.""",
    ),
    (
        "code",
        """state = "배송이 늦긴 했는데 물건은 마음에 드네요. 다음엔 좀 빨리 보내 주세요."

questions = {
    "intent": choice("이 글의 주된 의도는 무엇인가?", {
        "complaint": "불만 제기",
        "praise": "칭찬",
        "request": "요청",
        "question": "질문",
    }),
    "anger": score("글쓴이가 화난 정도", ["차분함", "약간 불만", "불만", "매우 화남"]),
    "needs_reply": noul("상담원이 답장해야 하는 글인가?"),
}

result = jev.decide(state, questions)
print(json.dumps(result.answers, ensure_ascii=False, indent=2))
print(f"\\n걸린 시간 {result.latency_ms:.0f}ms, 사용량 {result.usage}")""",
    ),
    (
        "md",
        """응답에서 볼 것이 세 가지 있습니다.

- 응답에 문장이 없습니다. 값은 option 이름, 숫자, probability 뿐입니다. 파싱할 글이 없으므로 코드에서 `result["intent"]["choice"]` 를 바로 `if` 문에 쓸 수 있습니다.
- 이유도 없습니다. Jev 는 왜 그렇게 판단했는지 설명하지 않습니다. 공식 문서도 "추론 과정, 설명, 자유 형식 글을 만들지 않는다"고 적고 있습니다.
- `usage` 의 출력 토큰은 요금에 들어가지 않습니다. 요금은 입력 토큰에만 붙습니다 (100만 토큰당 $0.042).

`usage` 에 `output_tokens` 가 찍혀 있는 것이 이상하게 보일 수 있습니다. 글을 생성하지 않는 모델이라고 했기 때문입니다. 이 숫자는 질문을 늘리면 함께 늘어나므로 응답에 담긴 답의 양을 세는 값으로 보입니다. 다만 내부에서 정확히 무엇을 세는지는 공식 문서에 설명이 없습니다. 확실한 것은 두 가지입니다. 응답에 문장이 없다는 것, 그리고 이 토큰에는 요금이 붙지 않는다는 것입니다.""",
    ),
    (
        "md",
        """## 세 primitive 자세히 보기: Choice, Score, Noul

공식 문서는 세 질문 타입을 Choice, Score, Noul 이라고 부릅니다. 이 시리즈도 이 이름을 그대로 씁니다. 요청 JSON 안에서는 소문자 `"choice"`, `"score"`, `"noul"` 로 적습니다.

### 질문 하나의 모양

타입이 무엇이든 question 하나는 같은 세 필드로 이루어집니다.

| 필드 | 뜻 |
|---|---|
| `type` | `"choice"`, `"score"`, `"noul"` 중 하나 |
| `instructions` | 모델이 답할 질문 그 자체 |
| `criteria` | 답의 범위. 타입마다 모양이 다릅니다 (아래에서 하나씩 봅니다) |

`questions` 는 "question id → question" 의 map 입니다. id 는 우리가 정하고, 답도 같은 id 아래에 돌아옵니다. 여기서 놓치기 쉬운 점이 있습니다.

> Question IDs are for your code. They are not sent to the model. Write the complete question in `instructions`, even when the ID seems self-explanatory.
> (question id 는 여러분의 코드를 위한 것이다. 모델에 전달되지 않는다. id 만 봐도 뜻이 분명해 보이더라도 `instructions` 에 완전한 질문을 써라.)

id 를 `is_refund_request` 라고 지어도 모델은 그 이름을 보지 못합니다. 질문은 `instructions` 에 온전히 써야 합니다.

### 어느 타입을 고를까

문서의 기준은 "필요한 답의 모양"입니다.

| 답의 모양 | 타입 | 예 |
|---|---|---|
| 순서가 없는 option 들 중 하나 | Choice | 티켓을 어느 팀에 보낼까, 문서 종류가 무엇인가 |
| 단계로 설명할 수 있는 spectrum 위의 위치 | Score | 버그가 얼마나 심각한가, 고객이 얼마나 화났나 |
| yes / no | Noul | 환불을 요청하는 글인가, 개인정보가 들어 있는가 |

이 프로젝트의 `jev_agent/jev.py` 에는 세 타입의 question 을 만드는 작은 함수 `choice()`, `score()`, `noul()` 이 있습니다. 아래에서 이 함수가 만드는 JSON 을 그대로 출력해 봅니다.

### Choice: option 들 중 하나를 고른다

**요청.** `criteria` 는 option 의 map 입니다. key 가 option 이름, value 가 그 option 의 설명입니다.

**응답.**

| 필드 | 뜻 |
|---|---|
| `choice` | probability 가 가장 높은 option 의 이름 |
| `probabilities` | 모든 option 에 대한 probability 분포. 전부 더하면 1 |
| `confidence` | `probabilities` 가 얼마나 한 option 에 몰려 있는지를 0~1 로 요약한 값 |

option 이름과 설명은 둘 다 모델에 전달됩니다. 문서는 "option 들을 서로 구분해 주는 설명을 쓰라"고 권합니다. 그리고 목록이 모든 입력을 덮지 못할 수 있으면 `other` 나 `none of the above` option 을 넣으라고 합니다 (바로 아래 구조 2 에서 왜 필요한지 확인합니다).""",
    ),
    (
        "code",
        """department = choice("이 문의를 어느 팀이 처리해야 하는가?", {
    "returns": "교환, 반품, 잘못 오거나 파손된 상품",
    "shipping": "배송 상태, 지연, 분실",
    "billing": "결제, 청구서, 환불 금액 문제",
})
print("요청에 들어가는 question:")
print(json.dumps(department, ensure_ascii=False, indent=2))

tickets = [
    "운동화가 다른 사이즈로 왔어요. 270 으로 바꿀 수 있나요?",
    "사이즈가 잘못 와서 반품했는데 환불 금액이 아직 안 들어왔어요.",
]
rows = []
for ticket in tickets:
    answer = jev.decide(ticket, {"department": department})["department"]
    rows.append({"state": ticket, "choice": answer["choice"], "probabilities": answer["probabilities"], "confidence": answer["confidence"]})
pd.DataFrame(rows)""",
    ),
    (
        "md",
        """첫 문의는 한 팀이 분명하므로 probability 가 한 option 에 몰리고 confidence 가 높습니다. 두 번째 문의는 반품과 결제 문제가 함께 있어 probability 가 두 option 으로 나뉘고 confidence 가 내려갑니다. `choice` 필드만 보면 두 경우가 똑같이 "답 하나"로 보이지만, `probabilities` 와 `confidence` 를 함께 보면 두 번째가 애매한 건이라는 것을 코드가 알 수 있습니다.

### Score: 순서가 있는 level 위의 위치를 잰다

**요청.** `criteria` 는 level 설명의 배열입니다. 낮은 쪽에서 높은 쪽 순서로 적습니다. level 은 최소 2개, 최대 10개입니다. level 의 번호는 배열에서의 위치이고 0 부터 시작합니다.

**응답.**

| 필드 | 뜻 |
|---|---|
| `probabilities` | level 마다의 probability. key 는 level 번호(문자열). 전부 더하면 1 |
| `score` | level 번호 선 위의 위치. 각 level 번호에 그 probability 를 곱해 더한 값 |
| `legend` | level 번호를 다시 설명 글로 이어 주는 표 |
| `confidence` | probability 가 가장 높은 level 주위에 얼마나 모여 있는지 |

`score` 는 두 level 사이에 떨어질 수 있습니다. 문서의 예는 이렇습니다. level 이 셋이고 probability 가 (0.0, 0.57, 0.43) 이면

```
score = 0 x 0.0 + 1 x 0.57 + 2 x 0.43 = 1.43
```

"level 1 과 2 사이인데 1 쪽에 조금 더 가깝다"는 뜻입니다. Choice 로 "낮음/중간/높음"을 물으면 하나만 고르게 되지만, Score 는 이 중간 위치를 숫자로 줍니다. 그래서 정렬하거나 기준값을 걸기 좋습니다.""",
    ),
    (
        "code",
        """severity = score("이 버그는 얼마나 심각한가?", [
    "사소함: 오타나 눈에만 거슬리는 문제",
    "보통: 기능 일부가 불편하지만 우회할 수 있음",
    "심각: 데이터가 사라지거나 서비스를 쓸 수 없음",
])
print("요청에 들어가는 question:")
print(json.dumps(severity, ensure_ascii=False, indent=2))

reports = [
    "설정 화면의 '저장' 버튼 글자가 한 픽셀 아래로 내려가 있어요.",
    "CSV 내보내기가 가끔 실패해요. 다시 누르면 됩니다.",
    "결제 후 주문 내역이 전부 사라졌습니다. 고객 300명이 영향을 받았어요.",
]
rows = []
for report in reports:
    answer = jev.decide(report, {"severity": severity})["severity"]
    rows.append({"state": report, "score": answer["score"], "probabilities": answer["probabilities"], "confidence": answer["confidence"]})
print("\\nlegend:", jev.decide(reports[0], {"severity": severity})["severity"]["legend"])
pd.DataFrame(rows)""",
    ),
    (
        "md",
        """`score` 가 0 에서 2 사이의 숫자로 나오고, 심각한 보고일수록 값이 큽니다. 이 세 보고는 모두 분명한 사례라 probability 가 한 level 에 몰렸고 `score` 가 0.01, 1.00, 2.00 으로 level 번호와 거의 같게 나왔습니다. level 사이에 떨어지는 예는 맨 처음 응답의 `anger` 입니다. probability 가 (0.03, 0.96, 0.01, 0) 이라 `score` 가 0.98 이었습니다. `probabilities` 의 key 가 "0", "1", "2" 인 것은 level 번호이고, `legend` 가 그 번호를 우리가 쓴 설명으로 다시 이어 줍니다.

### Noul: yes 일 probability 를 숫자 하나로 준다

**요청.** `instructions` 에 yes/no 질문(또는 참인지 판단할 문장)을 씁니다. `criteria` 는 선택 사항이고, 쓴다면 `true` 와 `false` 가 각각 무엇을 뜻하는지 적은 객체입니다.

**응답.** 필드가 `noul` 하나뿐입니다. 0 은 no, 1 은 yes 이고 그 사이의 값은 yes 일 probability 입니다.

Noul 에는 `confidence` 필드가 없습니다. 문서는 그 이유를 한 문장으로 말합니다.

> The number is the answer and the certainty in one.
> (이 숫자 하나가 답이면서 동시에 확실한 정도다.)

1 에 가까우면 강한 yes, 0 에 가까우면 강한 no, 0.5 근처면 모델이 yes 와 no 에 비슷한 probability 를 준 것입니다. 그래서 true/false 로 바꿔 쓰지 말고 숫자에 기준값을 직접 거는 것이 Noul 의 쓰임새입니다. boolean 이 아니라 Noul 이라는 별도 이름을 쓰는 이유가 여기 있습니다.

공식 문서에는 "고객이 사람 상담원을 원하는가"라는 Noul 에 대해 `jev-1.13.0` 이 실제로 낸 값이 표로 실려 있습니다. 같은 영어 문장 여섯 개를 직접 넣어 문서의 값과 나란히 봅니다. 문서가 쓴 `instructions` 원문은 공개되어 있지 않아 질문은 제가 썼습니다. 값이 완전히 같을 수는 없고, 순서와 대략의 위치가 같은지를 봅니다.""",
    ),
    (
        "code",
        """is_human_escalation = noul("Is the customer asking to talk to a human?")
is_repeat_contact = noul(
    "Has the customer contacted support about this before?",
    true="The message says or implies earlier attempts, such as asking again or following up.",
    false="Nothing in the message suggests an earlier contact.",
)
print("criteria 없는 Noul:", json.dumps(is_human_escalation, ensure_ascii=False))
print("criteria 있는 Noul:", json.dumps(is_repeat_contact, ensure_ascii=False))

documented = {   # docs.typesafe.ai/primitives/noul 에 실린 값
    "Thanks, that fixed it!": 0.02,
    "How do I reset my password?": 0.07,
    "I need this sorted today, whatever it takes.": 0.26,
    "Are you a bot?": 0.40,
    "Is there any way to speak to someone about my invoice?": 0.84,
    "I have asked three times now. Can I please just talk to a real person?": 0.99,
}
rows = []
for message, documented_value in documented.items():
    answers = jev.decide(message, {"is_human_escalation": is_human_escalation, "is_repeat_contact": is_repeat_contact})
    rows.append({
        "state": message,
        "문서의 noul": documented_value,
        "직접 호출한 noul": answers["is_human_escalation"]["noul"],
        "is_repeat_contact": answers["is_repeat_contact"]["noul"],
    })
pd.DataFrame(rows)""",
    ),
    (
        "md",
        """직접 호출한 값은 0.03, 0.04, 0.25, 0.31, 0.89, 0.99 로, 문서의 0.02, 0.07, 0.26, 0.40, 0.84, 0.99 와 순서가 같고 값도 가깝습니다. 질문 문장이 달라도 같은 모양이 나온다는 점에서 문서의 표가 실제 동작을 보여 준다고 볼 수 있습니다. 옆 열의 `is_repeat_contact` 는 같은 호출에 함께 넣은 두 번째 Noul 이고, "three times"라고 쓴 마지막 문장에서만 높게 나옵니다.

문서가 가운데 두 줄을 따로 설명합니다. "I need this sorted today"는 급하다고는 하지만 사람을 찾지는 않았고, "Are you a bot?"은 사람을 원한다는 눈치를 주지만 요청하지는 않았습니다. Noul 은 이런 글에 0 이나 1 을 억지로 주지 않고 중간 값을 줍니다. 이 중간 값이 "애매하다"는 정보이고, 코드에서 따로 처리할 수 있는 신호입니다.

정리하면 세 타입은 이렇게 다릅니다.

| | Choice | Score | Noul |
|---|---|---|---|
| `criteria` | option 의 map (이름 → 설명) | level 설명의 배열 (낮음 → 높음, 2~10개) | 선택. `true` / `false` 설명 |
| 답 필드 | `choice` | `score` | `noul` |
| `probabilities` | option 마다 | level 마다 | 없음 (`noul` 이 곧 probability) |
| `confidence` | 있음 | 있음 | 없음. 필요하면 \\|2p - 1\\| |
| 코드에서 쓰는 법 | `choice` 로 분기, `confidence` 로 넘길지 결정 | `score` 로 정렬하거나 기준값 | `noul` 에 기준값 |""",
    ),
    (
        "md",
        """## 구조 2. 답은 option 밖으로 나갈 수 없다

`choice` 의 답은 우리가 준 option 중 하나입니다. 공식 블로그는 그 이유를 이렇게 설명합니다.

> Jev outputs all probabilities in parallel instead of autoregressively generating by token.
> (Jev 는 토큰을 하나씩 차례로 생성하는 대신 모든 probability 를 병렬로 출력한다.)

> Possible outputs and structure are defined in advance. The model never makes type errors.
> (가능한 출력과 구조가 미리 정해져 있다. 모델은 타입 오류를 내지 않는다.)

글자를 써 내려가지 않고 미리 정해진 option 마다 probability 를 매긴다는 설명입니다. 내부를 들여다볼 수는 없으므로, 이 노트북에서 직접 확인할 수 있는 것은 "답이 option 밖으로 나가지 않는다"는 바깥 동작까지입니다.

이 성질에는 주의할 점이 있습니다. 형식이 틀리지 않는다는 뜻이고, 내용이 틀리지 않는다는 뜻은 아닙니다. option 어디에도 맞지 않는 글을 넣어 확인합니다.""",
    ),
    (
        "code",
        """unrelated_state = "오늘 점심은 김치찌개였다."

forced = jev.decide(unrelated_state, {
    "intent": choice("이 글의 의도는?", {"refund": "환불 요청", "shipping": "배송 문의", "praise": "칭찬"}),
})["intent"]

with_escape = jev.decide(unrelated_state, {
    "intent": choice("이 글의 의도는?", {
        "refund": "환불 요청", "shipping": "배송 문의", "praise": "칭찬",
        "none": "위 어느 것에도 해당하지 않는다",
    }),
})["intent"]

pd.DataFrame([
    {"option 구성": "해당 없음 option 이 없을 때", "고른 답": forced["choice"], "confidence": forced["confidence"], "probability": forced["probabilities"]},
    {"option 구성": "해당 없음 option 을 넣었을 때", "고른 답": with_escape["choice"], "confidence": with_escape["confidence"], "probability": with_escape["probabilities"]},
])""",
    ),
    (
        "md",
        """첫 행을 보면 점심 메뉴 이야기를 "칭찬"으로 골랐고 confidence 가 0.98 입니다. option 안에서만 답할 수 있으니 그중 가장 가까운 것을 고른 것입니다. 두 번째 행처럼 "해당 없음" option 을 넣어야 제대로 빠져나옵니다.

"Jev 는 환각이 없다"는 말은 이렇게 읽어야 합니다.

- **없는 것**: option 에 없는 답, 깨진 형식, 지어낸 문장
- **여전히 있는 것**: option 중에서 틀린 것을 고르는 일

그래서 option 을 설계하는 일이 중요합니다. 02번 노트북의 도구 선택에서 `no_tool` option 을 넣는 것도 같은 이유입니다.

### Choice 는 상대 평가, Noul 은 절대 평가

공식 문서는 두 타입의 차이를 이렇게 설명합니다.

> the Choice is relative, settling *which* option, while each Noul is absolute and can be low for all of them.
> (Choice 는 상대적이어서 "어느" option 인지를 정한다. 반면 각 Noul 은 절대적이어서 전부 낮게 나올 수 있다.)

Choice 의 probability 는 option 들끼리 나눠 갖는 값이라 합이 항상 1 입니다. 어느 것도 맞지 않아도 누군가는 큰 몫을 가져갑니다. Noul 은 질문마다 따로 0~1 을 매기므로 전부 낮을 수 있습니다. 같은 점심 메뉴 글에 option 마다 Noul 을 하나씩 물어 확인합니다.""",
    ),
    (
        "code",
        """absolute = jev.decide(unrelated_state, {
    "refund": noul("이 글은 환불을 요청하는 글인가?"),
    "shipping": noul("이 글은 배송에 대해 묻는 글인가?"),
    "praise": noul("이 글은 쇼핑몰이나 상품을 칭찬하는 글인가?"),
})
pd.DataFrame([
    {"option": name, "Choice 의 probability (합 1)": forced["probabilities"][name], "Noul (각자 0~1)": absolute[name]["noul"]}
    for name in ("refund", "shipping", "praise")
])""",
    ),
    (
        "md",
        """Choice 에서는 `praise` 가 probability 0.99 를 가져갔지만, 같은 것을 Noul 로 물으면 0.02 입니다. 세 Noul 모두 0.01~0.02 입니다. "어느 것인가"와 "이것이 맞는가"는 다른 질문입니다. 문서는 둘을 함께 쓰는 방식도 소개합니다. Choice 로 후보를 고르고, Noul 로 그 후보를 실제로 제안할 만한지 확인하는 방식입니다.

## 구조 3. probability 와 confidence 는 어떻게 만들어지나

Jev 응답에는 숫자가 두 종류 있습니다.

- **probability(`probabilities`)**: option(또는 level)마다 붙는 값입니다. 모델이 직접 낸 값입니다.
- **confidence(`confidence`)**: probability 분포를 숫자 하나로 요약한 값입니다. 모델이 따로 내는 값이 아니고, probability 에서 계산한 통계량입니다.

공식 문서의 표현은 이렇습니다.

> a statistic computed from the probability distribution the answer already gives you
> (답에 이미 들어 있는 probability 분포로부터 계산한 통계량)

타입별 공식이 문서에 공개되어 있습니다.

**choice**: 가장 높은 probability 가 "똑같이 나눈 값"보다 얼마나 위에 있는가

$$\\text{confidence} = \\frac{p_{\\max} - \\frac{1}{n}}{1 - \\frac{1}{n}}$$

option 이 4개면 똑같이 나눈 값은 0.25 입니다. 가장 높은 probability 가 0.25 면 confidence 0, 1.0 이면 confidence 1 입니다.

**score**: probability 가 가장 높은 단계에서 얼마나 멀리 퍼져 있는가

$$\\text{confidence} = \\max\\left(0,\\ 1 - \\frac{\\sum_i p_i\\,|i - m|}{\\text{MAD}_{\\text{unif}}}\\right)$$

$m$ 은 probability 가 가장 높은 단계, $\\text{MAD}_{\\text{unif}}$ 는 probability 가 모든 단계에 똑같이 퍼졌을 때의 평균 거리입니다. choice 와 달리 거리를 봅니다. 바로 옆 단계에 probability 가 있으면 confidence 가 조금 깎이고, 먼 단계에 있으면 많이 깎입니다.

**noul**: 응답에 confidence 가 없습니다. 필요하면 $|2p - 1|$ 로 계산합니다. 문서는 confidence 를 거치지 말고 probability 에 기준값을 바로 걸라고 권합니다.

이 공식으로 직접 계산한 값이 API 가 돌려준 값과 같은지 확인합니다.""",
    ),
    (
        "code",
        """def choice_confidence(probabilities: dict) -> float:
    n, p_max = len(probabilities), max(probabilities.values())
    return (p_max - 1 / n) / (1 - 1 / n)

def score_confidence(probabilities: dict) -> float:
    levels = sorted(probabilities, key=int)
    values = [probabilities[level] for level in levels]
    n, peak = len(values), max(range(len(values)), key=lambda index: values[index])
    spread = sum(p * abs(index - peak) for index, p in enumerate(values))
    uniform_spread = sum(abs(index - (n - 1) / 2) for index in range(n)) / n
    return max(0.0, 1 - spread / uniform_spread)

def score_value(probabilities: dict) -> float:
    return sum(int(level) * p for level, p in probabilities.items())

intent, anger, needs_reply = result["intent"], result["anger"], result["needs_reply"]
pd.DataFrame([
    {"값": "choice confidence", "probability 분포": intent["probabilities"], "공식으로 계산": round(choice_confidence(intent["probabilities"]), 2), "API 응답": intent["confidence"]},
    {"값": "score confidence", "probability 분포": anger["probabilities"], "공식으로 계산": round(score_confidence(anger["probabilities"]), 2), "API 응답": anger["confidence"]},
    {"값": "score 점수 (가중 평균)", "probability 분포": anger["probabilities"], "공식으로 계산": round(score_value(anger["probabilities"]), 2), "API 응답": anger["score"]},
    {"값": "noul confidence |2p-1|", "probability 분포": needs_reply["noul"], "공식으로 계산": round(abs(2 * needs_reply["noul"] - 1), 2), "API 응답": "(없음)"},
])""",
    ),
    (
        "md",
        """계산한 값과 API 응답이 맞습니다. choice confidence 는 0.41 로 같고, score confidence 만 0.96 과 0.97 로 0.01 다른데, 응답의 probability 가 소수 둘째 자리로 반올림되어 있어서 생기는 차이입니다. confidence 는 숨은 값이 아니고 probability 를 요약한 숫자입니다.

여기서 실용적인 결론이 하나 나옵니다. choice confidence 는 가장 높은 probability 하나만 봅니다. 문서의 예로, (0.6, 0.3, 0.1) 과 (0.6, 0.2, 0.2) 는 confidence 가 똑같이 0.4 입니다. 1등과 2등의 차이가 중요한 상황이라면 confidence 대신 probability 를 직접 보는 편이 낫습니다. 02번에서 상위 두 개 도구를 LLM 에 넘길 때 probability 를 직접 쓰는 이유입니다.

## 구조 4. 질문 여러 개는 한 번에, 서로 독립으로

공식 문서는 질문 처리 방식을 이렇게 설명합니다.

> Every question is evaluated in parallel and in isolation against the same state in one go. Adding questions barely changes the response time.
> (모든 질문은 같은 state 에 대해 한 번에, 병렬로, 서로 격리되어 평가된다. 질문을 추가해도 응답 시간은 거의 달라지지 않는다.)

> Jev ingests the `state` once and evaluates every question against it in parallel.
> (Jev 는 state 를 한 번 읽고 모든 질문을 그에 대해 병렬로 평가한다.)

이 설명에서 확인할 수 있는 것이 세 가지입니다.

1. **state 를 한 번만 읽는다면** 질문을 늘려도 입력 토큰이 state 길이만큼씩 늘지 않아야 합니다.
2. **병렬이라면** 질문을 늘려도 시간이 거의 늘지 않아야 합니다.
3. **격리되어 있다면** 같은 질문을 혼자 물을 때와 다른 질문들 사이에 끼워 물을 때 답이 같아야 합니다.""",
    ),
    (
        "code",
        """long_state = "주문 A1001 배송 문의입니다. 3주째 도착하지 않았습니다. " * 40   # 긴 state

def run_with(question_count: int, repeats: int = 5) -> dict:
    question_set = {f"q{index}": noul(f"이 글은 배송 지연에 대한 글인가? (질문 {index})") for index in range(question_count)}
    runs = [jev.decide(long_state, question_set) for _ in range(repeats)]
    return {
        "질문 수": question_count,
        "입력 토큰": runs[0].usage["input_tokens"],
        "시간 중앙값(ms)": round(statistics.median(run.latency_ms for run in runs)),
        "비용($)": f"{runs[0].cost:.7f}",
    }

jev.decide(long_state, {"warmup": noul("배송 글인가?")})   # 첫 호출은 연결을 맺느라 느리므로 버린다
scaling = pd.DataFrame([run_with(count) for count in (1, 2, 4, 8, 16)])
scaling""",
    ),
    (
        "code",
        """first, last = scaling.iloc[0], scaling.iloc[-1]
added_questions = last["질문 수"] - first["질문 수"]
print(f"질문 1개일 때 입력 토큰: {first['입력 토큰']}")
print(f"질문 {last['질문 수']}개일 때 입력 토큰: {last['입력 토큰']}  (질문 하나당 +{(last['입력 토큰'] - first['입력 토큰']) / added_questions:.0f} 토큰)")
print(f"state 를 질문마다 다시 읽었다면: 약 {first['입력 토큰'] * last['질문 수']} 토큰")""",
    ),
    (
        "md",
        """질문을 1개에서 16개로 늘리는 동안 입력 토큰은 1,366 에서 1,747 로, 질문 하나당 약 25 토큰씩만 늘었습니다. state 를 질문마다 다시 읽었다면 약 21,900 토큰이 됐을 것입니다. 시간 중앙값은 261~272ms 사이에서 움직였고 질문 수를 따라 늘지 않았습니다. 비용은 질문이 16배가 되는 동안 1.3배가 됐습니다. 문서의 "state 를 한 번 읽고 병렬로 평가한다"는 설명과 맞습니다.

이 성질이 설계에 주는 의미가 큽니다. LLM 에서는 판단 하나를 더 시키면 호출이 하나 늘거나 출력이 길어집니다. Jev 에서는 같은 state 에 대한 판단이라면 질문을 더 붙이는 비용이 거의 없습니다. 11번의 가드레일이 네 범주를 한 번에 판정하고, 08번의 도구 게이트가 위험 네 가지를 한 번에 묻는 근거입니다.

이제 격리를 확인합니다. 같은 질문을 혼자 물을 때와, 성격이 전혀 다른 질문 일곱 개 사이에 끼워 물을 때를 비교합니다.""",
    ),
    (
        "code",
        """target = noul("상담원이 답장해야 하는 글인가?")
distractors = {
    "is_english": noul("이 글은 영어로 쓰였는가?"),
    "has_number": noul("이 글에 숫자가 들어 있는가?"),
    "is_spam": noul("이 글은 광고인가?"),
    "is_poem": noul("이 글은 시인가?"),
    "mood": choice("글의 분위기는?", {"bright": "밝음", "dark": "어두움", "neutral": "중립"}),
    "length": score("글의 길이", ["매우 짧음", "짧음", "보통", "김"]),
    "is_threat": noul("이 글은 협박인가?"),
}

alone = [jev.decide(state, {"needs_reply": target})["needs_reply"]["noul"] for _ in range(6)]
first_among = [jev.decide(state, {"needs_reply": target, **distractors})["needs_reply"]["noul"] for _ in range(6)]
last_among = [jev.decide(state, {**distractors, "needs_reply": target})["needs_reply"]["noul"] for _ in range(6)]

pd.DataFrame([
    {"조건": "혼자 물을 때", "값들": alone, "최소": min(alone), "최대": max(alone)},
    {"조건": "다른 질문 7개와 함께 (맨 앞)", "값들": first_among, "최소": min(first_among), "최대": max(first_among)},
    {"조건": "다른 질문 7개와 함께 (맨 뒤)", "값들": last_among, "최소": min(last_among), "최대": max(last_among)},
])""",
    ),
    (
        "md",
        """세 조건의 값이 모두 0.83~0.86 안에 있습니다. 다른 질문이 옆에 있어도, 질문 순서를 바꿔도 답이 끌려가지 않습니다. 조건 사이의 차이가 같은 조건 안에서 호출마다 생기는 흔들림보다 크지 않습니다.

LLM 에게 질문 여러 개를 한 프롬프트로 물으면 앞 질문의 답이 뒤 질문의 답에 영향을 줍니다. 앞에서 생성한 토큰이 뒤 토큰의 입력이 되기 때문입니다. Jev 는 질문끼리 서로를 보지 않습니다.

격리에는 대가도 있습니다. 질문끼리 서로를 보지 못하므로 "1번 질문의 답이 예라면 2번은..." 같은 조건부 질문은 한 번의 호출로 할 수 없습니다. 그런 연결은 코드에서 `if` 로 잇습니다.

## 구조 5. 같은 호출도 값이 조금씩 다르다

위 표에서 같은 조건의 값들이 완전히 같지는 않았을 수 있습니다. 같은 요청을 여러 번 보내 흔들림의 크기를 봅니다.""",
    ),
    (
        "code",
        """repeated = [jev.decide(state, questions) for _ in range(10)]
pd.DataFrame([
    {"값": "needs_reply (noul)", "최소": min(r["needs_reply"]["noul"] for r in repeated), "최대": max(r["needs_reply"]["noul"] for r in repeated)},
    {"값": "anger (score)", "최소": min(r["anger"]["score"] for r in repeated), "최대": max(r["anger"]["score"] for r in repeated)},
    {"값": "intent 최고 probability", "최소": min(max(r["intent"]["probabilities"].values()) for r in repeated), "최대": max(max(r["intent"]["probabilities"].values()) for r in repeated)},
    {"값": "intent 고른 답", "최소": ", ".join(sorted({r["intent"]["choice"] for r in repeated})), "최대": ""},
])""",
    ),
    (
        "md",
        """값이 호출마다 조금씩 움직입니다. `noul` 은 0.84~0.86, `choice` 의 최고 probability 는 0.54~0.58 였습니다. 열 번 모두 같은 option 을 골랐지만, 1등과 2등이 0.56 대 0.43 으로 붙어 있는 이런 글은 더 여러 번 부르면 답이 바뀔 수 있습니다. confidence 0.41 이 바로 그 상태를 알려 주는 값입니다.

그래서 기준값을 `p == 0.8` 처럼 정확한 값에 걸면 안 되고, 구간으로 나눠야 합니다. 03번 노트북의 위험 게이트가 "0.93 이상이면 실행, 0.15 미만이면 차단, 그 사이는 사람에게"처럼 세 구간으로 나누는 이유입니다. 구간의 경계 근처에 있는 요청은 호출마다 다른 쪽으로 떨어질 수 있다는 점도 함께 기억해야 합니다.

공식 문서는 기준값을 이렇게 잡으라고 권합니다.

> Start with conservative thresholds, test with your own data, and adjust as you observe results.
> (보수적인 기준값으로 시작해, 자기 데이터로 시험하고, 결과를 보면서 조정하라.)

## 학습 방식: 무엇에 맞춰 훈련했는가

Jev 의 가중치와 논문은 공개되지 않았습니다. 공개된 것은 훈련의 목표입니다. TypeSafe 는 모델을 사전 학습 뒤에 다듬는 방식을 셋으로 나눠 설명합니다.

| 방식 | 무엇을 보상하나 | 만들어지는 모델 |
|---|---|---|
| RLHF (사람 피드백 강화학습) | 사람 평가자가 더 좋아하는 답 | 채팅 모델 |
| RLVR (검증 가능한 보상 강화학습) | 검증할 수 있는 정답 (수학, 코드) | 추론 모델 |
| RLCD (calibrated 판단 강화학습) | probability 가 실제 결과와 맞는 정도 | System One 모델 (Jev) |

RLHF 에 대한 TypeSafe 의 지적은 이렇습니다.

> An output can be compelling to a person without being reliable enough for unattended automation.
> (어떤 출력은 사람에게는 설득력이 있으면서도, 사람 없이 돌아가는 자동화에 쓸 만큼 믿을 만하지는 않을 수 있다.)

공식 문서는 RLHF 의 부작용으로 두 가지를 듭니다. 하나는 아첨과 "자신 있게 들리는 환각"에 보상이 갈 수 있다는 것이고, 다른 하나는 모드 드로핑(mode dropping)입니다. 모델이 특정한 답변 스타일을 선호하게 되면서 다른 가능한 출력의 probability 를 줄여 버리는 현상입니다. 블로그는 여기에 "confidence 를 물어도 모델은 과신하고 일관되지 않는 경향이 있다"고 덧붙입니다.

제 식으로 풀면 이렇습니다. 사람 평가자는 "잘 모르겠습니다"보다 단정적인 답에 점수를 더 주기 쉽습니다. 그런 평가에 맞춰 훈련된 모델은 자신 있어 보이는 답 쪽으로 쏠리고, 그 모델이 말하는 확신은 실제 정답률과 멀어집니다. (이 문단은 문서의 설명을 제가 해석한 것입니다.)

RLCD 가 맞추려는 것은 **calibration**입니다.

> Outcomes assigned a probability of 0.2 should occur about 20% of the time.
> (probability 0.2 를 받은 결과는 실제로 약 20% 일어나야 한다.)

일기예보에 비유할 수 있습니다. "비 올 probability 70%"라고 예보한 날을 100일 모았을 때 실제로 70일쯤 비가 왔다면 그 예보는 calibration 이 잘 된 것입니다. 한 번의 예보가 맞았는지로는 알 수 없고, 많이 모아야 드러나는 성질입니다.

calibration 이 중요한 이유는 probability 를 코드에서 쓸 수 있게 되기 때문입니다. probability 가 실제 정답률과 맞는다면 "0.9 이상은 자동 처리, 그 아래는 사람에게"라는 규칙이 뜻을 가집니다.

이 주장은 이 노트북에서 검증하지 않습니다. calibration 을 확인하려면 라벨이 붙은 데이터가 많이 필요합니다. 11번 노트북에서 40건으로 작게 확인하는데, Jev 의 confidence 0.9 이상 판정은 모두 맞았고 틀린 판정은 confidence 가 낮은 쪽에 몰려 있었습니다.

## 공개된 것과 공개되지 않은 것

공식 자료가 말하는 것과 말하지 않는 것을 나눠 둡니다.

| 항목 | 공식 자료의 내용 |
|---|---|
| 입출력 구조 | `state` + `questions` → 타입이 정해진 답, probability, confidence |
| 질문 타입 | `choice`, `score`, `noul` 세 가지 |
| 처리 방식 | state 를 한 번 읽고 모든 질문을 병렬로, 서로 격리해 평가. "모든 출력을 한 번의 질의로 생성" |
| confidence 공식 | 공개됨 (위에서 확인) |
| 훈련 목표 | RLCD: probability 가 실제 결과와 맞도록 |
| 입력 한도 | TypeSafe 직접 API: 요청당 64k 토큰, 그중 state 와 가장 긴 질문을 합쳐 32k 토큰. OpenRouter 모델 페이지: 32,000 토큰. **이 시리즈는 OpenRouter 로 호출하므로 32k 를 기준으로 삼습니다** |
| 언어 | 주 학습 언어는 영어. 한국어를 포함한 다른 언어는 처리하지만 정확도가 같은 수준은 아니라고 명시 (아래 참고) |
| 입력 형식 | 글만 가능 (문자열, JSON, 글의 배열). 이미지, 음성, 영상은 불가 |
| 맞춤 학습 | 없음. "모든 계정이 같은 가중치를 쓴다". 도메인 지식은 state 와 질문 글로 전달 |
| 가격 | 입력 100만 토큰당 $0.042, 출력 무료 |
| **모델 내부 구조** | **공개되지 않음.** 가중치, 파라미터 수, 논문 모두 없음 |

마지막 행이 중요합니다. TypeSafe 가 밝힌 것은 "토큰을 차례로 생성하지 않고 모든 probability 를 병렬로 낸다"는 동작 방식까지입니다. 신경망이 구체적으로 어떻게 생겼는지, 크기가 얼마인지는 밝힌 적이 없습니다. 인터넷의 해설 글 가운데에는 내부 구조를 단정적으로 설명하는 것도 있는데, 공식 자료로 뒷받침되지 않는 내용입니다. 이 노트북은 공식 자료가 말한 것과 밖에서 관찰할 수 있는 동작까지만 다룹니다.

### 한국어로 쓸 때 알아 둘 것

이 시리즈는 질문과 state 를 모두 한국어로 씁니다. 공식 문서는 언어에 대해 이렇게 적습니다.

> English is the primary training language and where accuracy is currently best. Other languages, including CJK scripts, are handled but not equally well; test on your own content before relying on Jev for a non-English workload, and pay close attention to Confidence when routing.
> (영어가 주 학습 언어이고 현재 정확도가 가장 높다. CJK 문자를 포함한 다른 언어도 처리하지만 같은 수준은 아니다. 영어가 아닌 작업에 Jev 를 쓰기 전에 자기 데이터로 시험하고, 분기할 때 confidence 를 주의 깊게 보라.)

그래서 이 시리즈의 평가 결과(02번, 05번, 11번)는 "한국어 고객지원 글에서 이 정도였다"로 읽어야 합니다. 영어 데이터에서의 성능이나 공식 벤치마크와 바로 견줄 수 없습니다. 한국어 서비스에 쓴다면 문서의 권고대로 자기 데이터로 먼저 평가하고, confidence 가 낮은 판단을 넘길 경로(03번)를 꼭 두는 편이 안전합니다.

## 공식 성능 수치를 읽는 법

공식 사이트에는 눈에 띄는 숫자가 있습니다.

- 응답 시간 70~500ms (LLM 은 3~329초)
- System One 형태의 질의에서 40~200배 빠름
- System One 과제 워크플로 기준 193.6배 빠르고 444.6배 저렴 (홈페이지 문구)

이 숫자를 읽을 때 알아 둘 것이 있습니다.

- 비교 대상은 가장 크고 비싼 모델들입니다. 블로그는 GPT-6 Astra 와 Fable 5.1 의 평균을 기준 답으로 삼았다고 적습니다.
- TypeSafe 스스로 단서를 달았습니다. 193.6배, 444.6배라는 숫자에 대해 "we expect that these are on the higher end of real world gains"(실제 환경에서 얻을 이득의 높은 쪽일 것으로 본다)라고 적었고, 워크플로를 자사 모델 팀이 만들었으므로 "some bias could exist"(편향이 있을 수 있다)라고 적었습니다.

이 시리즈에서 직접 잰 값은 다릅니다. 작고 빠른 LLM(gpt-5.4-mini)과 비교하면 판정 시간은 약 4배, 비용은 약 14~17배 차이였습니다 (05번, 11번). 이 노트북에서 잰 Jev 응답 시간은 첫 호출 559ms, 그 뒤 261~272ms 로 공식 범위 안에 있습니다. 배율은 무엇과 비교하느냐에 따라 크게 달라지므로, 자기 서비스에서 지금 쓰는 모델과 직접 비교해 봐야 합니다.

## Jev 에게 맡기면 안 되는 일

구조에서 한계가 바로 나옵니다.

| 한계 | 구조상의 이유 |
|---|---|
| 글을 쓰지 못합니다 | 출력이 option 이름과 숫자뿐입니다 |
| 이유를 설명하지 못합니다 | 추론 과정을 출력하지 않습니다 |
| 여러 단계 계획을 세우지 못합니다 | 한 번의 계산으로 끝납니다. 도구를 부르지도 않습니다 |
| 정확한 계산, 날짜 계산, 숫자 비교에 약합니다 | 패턴으로 직관하는 모델입니다. 이런 일은 코드가 합니다 |
| 조건부로 이어지는 질문을 한 번에 못 합니다 | 질문끼리 격리되어 있습니다 |
| 한국어에서는 영어보다 정확도가 낮을 수 있습니다 | 주 학습 언어가 영어입니다 |

06번 노트북에서 산술과 날짜 문제를 직접 틀리게 해 봅니다.

## 정리

| 구조 | 뜻 | 이 시리즈에서 쓰이는 곳 |
|---|---|---|
| 출력이 타입으로 고정됨 | 파싱과 재시도가 필요 없음. 대신 option 설계가 중요 | 02번 도구 선택의 `no_tool` option |
| probability 가 함께 나옴 | 기준값으로 분기할 수 있음 | 03번 confidence 캐스케이드, 위험 게이트 |
| confidence 는 probability 의 요약 | 1등과 2등 차이가 중요하면 probability 를 직접 볼 것 | 02번 상위 2개 도구 노출 |
| state 를 한 번 읽고 질문은 병렬 | 질문을 더 붙이는 비용이 거의 없음 | 08번 도구 게이트, 11번 가드레일 |
| 질문끼리 격리 | 서로 영향을 주지 않음. 조건부 연결은 코드에서 | 09번 라우팅 |
| 값이 호출마다 조금 흔들림 | 기준은 구간으로 | 03번 세 구간 게이트 |
| 글, 이유, 계산은 못 함 | LLM, 코드와 역할을 나눔 | 06번 한계 |

다음 노트북(01번)에서는 세 질문 타입을 하나씩 써 보고, 질문을 잘 쓰는 방법을 다룹니다.

## 참고한 공식 자료

- [TypeSafe 홈페이지](https://typesafe.ai/)
- [Introducing System One Models & Jev (TypeSafe 블로그)](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- [TypeSafe 문서](https://docs.typesafe.ai/)
- [System One 개념](https://docs.typesafe.ai/concepts/system-one)
- [confidence (Confidence)](https://docs.typesafe.ai/confidence)
- [모델 사양](https://docs.typesafe.ai/models) (입력 한도, 언어 지원)
- [AI Primer](https://docs.typesafe.ai/introduction/machine-learning-primer)
- [What Is Jev? (OpenRouter 블로그)](https://openrouter.ai/blog/insights/what-is-jev/)""",
    ),
]
