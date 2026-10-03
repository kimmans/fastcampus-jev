"""라우팅: 질의 하나에 대해 어디서 찾고, 어떤 결과를 쓰고, 어떤 모델로 답할지를 한 번에 정한다.

jev-search(https://github.com/superagents-lab/jev-search)의 검색 소스 선택과 관련도 판정,
hermes-jev-skills(https://github.com/kerpopule/hermes-jev-skills)의 턴별 모델 라우팅을 따랐다.
질문이 여러 개여도 Jev 호출은 한 번이다.

- source      choice  어느 검색 소스에 물을 것인가
- time_range  choice  얼마나 최근 자료가 필요한가
- difficulty  score   이 질의에 답하는 데 필요한 모델 수준
- rel_N       score   후보 결과 N 이 질의에 얼마나 관련 있는가
"""

from __future__ import annotations

from typing import Any

from jev_agent.jev import JevResult, choice, score
from jev_agent.patterns.view import require_list, require_text, row, stat

SOURCES = {
    "web": "일반 웹 검색. 제품 정보, 사용법, 폭넓은 주제.",
    "news": "뉴스 검색. 최근 사건, 발표, 출시 소식.",
    "papers": "논문 검색(arXiv). 연구 방법, 실험 결과, 학술 개념.",
    "code": "코드 검색(GitHub). 라이브러리 사용 예, 오류 메시지, 구현 코드.",
    "community": "커뮤니티 검색(Reddit, Hacker News). 사용 후기, 경험담, 의견.",
    "encyclopedia": "백과사전(Wikipedia). 정의, 역사, 인물, 기본 사실.",
    "no_search": "검색이 필요 없다. 인사이거나 이미 아는 내용으로 답할 수 있다.",
}
TIME_RANGES = {
    "any": "시기와 무관하다.",
    "past_year": "최근 1년 안의 자료가 필요하다.",
    "past_week": "최근 일주일 안의 자료가 필요하다.",
}
DIFFICULTY_LEVELS = [
    "단순 조회나 한 줄 답변. 작은 모델로 충분하다.",
    "여러 사실을 정리해 설명해야 한다. 중간 모델이 적당하다.",
    "여러 단계의 추론, 설계, 긴 코드 작성이 필요하다. 큰 모델이 필요하다.",
]
MODEL_BY_LEVEL = ["작은 모델", "중간 모델", "큰 모델"]
RELEVANCE_LEVELS = ["질의와 무관하다", "주제는 같지만 답은 없다", "질의에 직접 답한다"]
RELEVANT_SCORE = 1.5

SAMPLE_RESULTS = [
    {
        "title": "LangGraph interrupt 공식 문서",
        "snippet": "interrupt() 로 그래프를 멈추고 Command(resume=...) 로 재개하는 방법",
    },
    {
        "title": "2026년 9월 TypeSafe, Jev 공개",
        "snippet": "판단 전용 System One 모델 Jev 출시 소식과 가격",
    },
    {"title": "파이썬 리스트 정렬 방법", "snippet": "sorted() 와 list.sort() 의 차이"},
    {
        "title": "langgraph GitHub 이슈: interrupt 가 두 번 실행됨",
        "snippet": "재개 시 노드가 처음부터 다시 실행되는 동작에 대한 논의",
    },
    {"title": "서울 맛집 추천 10선", "snippet": "주말에 가기 좋은 식당 모음"},
]
SAMPLE_QUERIES = [
    "LangGraph 에서 interrupt 후 재개하면 노드가 왜 다시 실행되나요?",
    "이번 주에 나온 Jev 관련 소식 알려줘",
    "트랜스포머 어텐션의 계산 복잡도를 줄이는 최근 연구는?",
    "안녕하세요",
]


def plan(payload: dict[str, Any]) -> tuple[Any, dict[str, dict[str, Any]]]:
    query = require_text(payload, "query")
    results = require_list(payload, "results")
    questions = {
        "source": choice("이 질의에 답하려면 어느 검색 소스에 물어야 하는가?", SOURCES),
        "time_range": choice("얼마나 최근 자료가 필요한가?", TIME_RANGES),
        "difficulty": score(
            "이 질의에 제대로 답하려면 어느 수준의 모델이 필요한가?", DIFFICULTY_LEVELS
        ),
    }
    for index in range(len(results)):
        questions[f"rel_{index}"] = score(
            f"candidate_results 의 {index}번 결과는 질의에 얼마나 관련 있는가?", RELEVANCE_LEVELS
        )
    candidates = [
        f"{index}: {item.get('title', '')} - {item.get('snippet', '')}"
        for index, item in enumerate(results)
    ]
    return {"query": query, "candidate_results": candidates}, questions


def view(payload: dict[str, Any], result: JevResult) -> dict[str, Any]:
    source, time_range, difficulty = result["source"], result["time_range"], result["difficulty"]
    level = min(round(difficulty["score"]), len(MODEL_BY_LEVEL) - 1)
    rows = [
        row(
            "검색 소스",
            source["choice"],
            "neutral",
            source.get("probabilities", {}),
            body=f"confidence {source.get('confidence', 0.0):.2f}",
        ),
        row("기간", time_range["choice"], "neutral", time_range.get("probabilities", {})),
        row(
            f"모델 수준 {difficulty['score']:.2f} / 2",
            MODEL_BY_LEVEL[level],
            "neutral",
            {f"level_{key}": value for key, value in difficulty.get("probabilities", {}).items()},
            body=DIFFICULTY_LEVELS[level],
        ),
    ]
    ranked = sorted(
        (
            (result[f"rel_{index}"]["score"], item.get("title", ""))
            for index, item in enumerate(payload["results"])
        ),
        reverse=True,
    )
    for relevance, title in ranked:
        is_relevant = relevance >= RELEVANT_SCORE
        rows.append(
            row(
                title,
                "사용" if is_relevant else "제외",
                "good" if is_relevant else "bad",
                {"relevance": relevance / (len(RELEVANCE_LEVELS) - 1)},
                {"relevance": RELEVANT_SCORE / (len(RELEVANCE_LEVELS) - 1)},
                f"관련도 {relevance:.2f} / 2",
            )
        )
    kept = [title for relevance, title in ranked if relevance >= RELEVANT_SCORE]
    return {
        "stats": [
            stat("검색 소스", source["choice"]),
            stat("기간", time_range["choice"]),
            stat("모델", MODEL_BY_LEVEL[level]),
            stat("쓸 결과", f"{len(kept)} / {len(ranked)}"),
        ],
        "rows": rows,
        "source": source["choice"],
        "model": MODEL_BY_LEVEL[level],
        "kept": kept,
    }
