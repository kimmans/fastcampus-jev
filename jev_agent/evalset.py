"""도구 선택 정확도 평가용 라벨 데이터. (질의, 정답 도구) 30건.

일부러 헷갈리는 쌍을 섞었다: search_order vs track_shipping, cancel_order vs request_refund,
search_products vs check_stock, 그리고 도구가 필요 없는 질의(no_tool).
"""

from __future__ import annotations

from jev_agent.middleware import NO_TOOL

EVAL_CASES: list[tuple[str, str]] = [
    ("A1001 지금 어디쯤 왔어요?", "track_shipping"),
    ("A1003 언제 도착하나요?", "track_shipping"),
    ("택배가 아직도 안 왔어요. 주문번호 A1001 이에요.", "track_shipping"),
    ("A1002 제가 뭘 샀었죠?", "search_order"),
    ("A1001 결제 금액이 얼마였는지 확인해 주세요.", "search_order"),
    ("주문 A1003 내역 좀 보여주세요.", "search_order"),
    ("A1003 아직 안 보냈으면 주문 취소해 주세요.", "cancel_order"),
    ("방금 결제한 A1003 잘못 샀어요. 없던 걸로 해주세요.", "cancel_order"),
    ("A1003 주문 철회하고 싶습니다.", "cancel_order"),
    ("A1002 받았는데 소리가 안 나요. 돈 돌려주세요.", "request_refund"),
    ("이어폰 A1002 불량이라 환불 접수 부탁드립니다.", "request_refund"),
    ("A1002 받은 상품이 마음에 안 들어서 반품하고 환불받고 싶어요.", "request_refund"),
    ("A1003 배송지를 서울시 강남구로 바꿔 주세요.", "change_address"),
    ("이사해서 주소가 바뀌었어요. A1003 받는 곳 수정해 주세요.", "change_address"),
    (
        "A1001 다른 주소로 받고 싶은데 변경 가능할까요? 새 주소는 인천시 연수구입니다.",
        "change_address",
    ),
    ("C001 적립금 얼마나 남았나요?", "check_points"),
    ("제 포인트 잔액 알려주세요. 고객번호는 C002 입니다.", "check_points"),
    ("C001 쌓인 마일리지 확인 부탁해요.", "check_points"),
    ("러닝화 파나요? 가격도 알려주세요.", "search_products"),
    ("텀블러 종류 뭐 있어요?", "search_products"),
    ("이어폰 상품 찾아주세요.", "search_products"),
    ("P20 지금 살 수 있나요? 품절인가요?", "check_stock"),
    ("P10 재고 몇 개 남았어요?", "check_stock"),
    ("상품 P30 수량 넉넉한가요?", "check_stock"),
    ("환불 규정이 어떻게 되나요?", "search_faq"),
    ("제주도는 배송이 며칠 걸려요?", "search_faq"),
    ("신규 가입 쿠폰은 언제까지 쓸 수 있어요?", "search_faq"),
    ("상담원이랑 직접 통화하고 싶어요.", "escalate_to_human"),
    ("안녕하세요!", NO_TOOL),
    ("감사합니다. 좋은 하루 보내세요.", NO_TOOL),
]
