"""
규칙 기반 AI 시뮬레이션 로직.

이 파일은 "AI 기능"이라 부르는 4가지(영업기회 탐지, 위험도 감지, 미팅 Copilot,
제안서 생성)를 실제로는 설명 가능한 규칙/공식으로 흉내낸 것이다. 나중에 실제 LLM
호출로 교체하더라도 다른 파일(라우터, 프론트엔드)은 건드릴 필요가 없도록, 모든
"AI 판단"은 이 파일 안의 순수 함수로만 구현한다.

핵심 원칙: 모든 결과는 영업 담당자의 판단을 돕는 참고 정보이며, 왜 그 점수/등급이
나왔는지 근거 문장에 실제 숫자를 인용한다 (블랙박스가 아니어야 한다).
"""

import re
from datetime import datetime, timedelta

# 이 앱이 참조하는 실거래 데이터(거래처_매입매출_데이터 등)는 2025년 중 시점의 데이터다.
# "지금이 언제인가"를 실제 시스템 날짜(예: 2026년)로 계산하면 모든 계약이 이미 오래 전에
# 끝난 것으로 나와 재계약 임박 판단이 무의미해진다. 그래서 이 데이터셋 안에서의
# "오늘"을 데이터 분포상 의미 있는 시점(계약 종료일이 과거/임박/미래로 고르게
# 나뉘는 시점)으로 고정한다. 실시간으로 예약하는 미팅 일정 등 "지금 사용자가 실제로
# 하는 행동"에는 이 값을 쓰지 않고 실제 현재 시각을 그대로 쓴다.
SIMULATED_TODAY = datetime(2025, 9, 1)

PIPELINE_STAGES = ["영업기회 발견", "고객접촉", "미팅", "제안", "협의", "계약", "고객관리"]

# 실제 거래처_매입매출_데이터.xlsx의 품목카테고리="IT서비스" 8개 품목.
# 넥스트라인이 거래처에 "추가로 붙여 팔 수 있는" 서비스형 상품만 추천 후보로 삼는다.
# (원자재/부품/소모품/완제품/물류 품목은 거래처의 "현재 이용 현황" 표시에는 포함되지만
# 추천 대상에서는 제외한다 — 이미 원자재를 사는 거래처에 원자재를 "추천"하는 건 의미가 없다.)
CORE_SERVICES = [
    "DB관리",
    "ERP유지보수",
    "SW라이선스",
    "네트워크관리",
    "모니터링",
    "백업서비스",
    "보안솔루션",
    "클라우드호스팅",
]

SERVICE_BENEFITS = {
    "DB관리": "데이터베이스 운영/백업을 전문 위탁해 장애 대응 속도를 높입니다.",
    "ERP유지보수": "ERP 시스템 오류 대응과 업데이트를 안정적으로 지원합니다.",
    "SW라이선스": "사용 중인 소프트웨어의 라이선스 관리와 최신 버전 유지를 돕습니다.",
    "네트워크관리": "사내 네트워크 장애를 사전에 모니터링하고 신속히 대응합니다.",
    "모니터링": "시스템/설비 이상을 실시간으로 감지해 다운타임을 줄입니다.",
    "백업서비스": "핵심 데이터를 정기적으로 백업해 장애·재해 시 손실을 최소화합니다.",
    "보안솔루션": "외부 위협으로부터 시스템과 데이터를 보호합니다.",
    "클라우드호스팅": "자체 서버 운영 부담 없이 안정적인 클라우드 인프라를 제공합니다.",
}

# VOC태그 -> 담당자가 바로 이해할 수 있는 표현
VOC_TAG_PLAIN = {
    "이탈징후": "이탈 신호로 해석될 수 있는 문의",
    "재구매의향": "추가 구매 의향을 보인 문의",
    "제안": "서비스 개선/추가 제안성 문의",
    "서비스불만": "서비스 이용 불만",
    "배송불만": "배송/납기 관련 불만",
    "가격불만": "가격/비용 관련 불만",
    "제품개선": "제품 개선 요청",
    "긴급대응": "긴급 대응이 필요했던 문의",
    "칭찬": "긍정적 피드백",
    "단순문의": "단순 정보성 문의",
}

POSITIVE_VOC_TAGS = {"재구매의향", "칭찬", "제안"}
NEGATIVE_VOC_TAGS = {"이탈징후", "서비스불만", "배송불만", "가격불만"}

# --- 미팅 노트 키워드 시뮬레이션(§4E) ------------------------------------

KEYWORD_MAP = {
    "db": "DB관리",
    "데이터베이스": "DB관리",
    "erp": "ERP유지보수",
    "전사자원": "ERP유지보수",
    "라이선스": "SW라이선스",
    "license": "SW라이선스",
    "네트워크": "네트워크관리",
    "망관리": "네트워크관리",
    "모니터링": "모니터링",
    "감시": "모니터링",
    "백업": "백업서비스",
    "보안": "보안솔루션",
    "해킹": "보안솔루션",
    "클라우드": "클라우드호스팅",
    "호스팅": "클라우드호스팅",
}

PAIN_KEYWORDS = {
    "느리": "성능/속도 이슈",
    "지연": "성능/속도 이슈",
    "비싸": "가격 민감",
    "가격": "가격 민감",
    "복잡": "사용성 이슈",
    "어렵": "사용성 이슈",
    "오류": "품질/오류 이슈",
    "불량": "품질/오류 이슈",
    "느려": "성능/속도 이슈",
    "불편": "사용성 이슈",
    "부족": "기능 부족",
}

POSITIVE_NOTE_WORDS = ["만족", "좋", "긍정", "관심", "기대"]
NEGATIVE_NOTE_WORDS = ["불만", "불편", "부정", "실망", "거절"]

REQUIREMENT_MARKERS = ["필요", "요청", "원함", "희망", "요구"]


def _clamp(value, low, high):
    return max(low, min(high, value))


def _percentile_rank(value, all_values):
    if not all_values:
        return 0.0
    sorted_vals = sorted(all_values)
    below = sum(1 for v in sorted_vals if v <= value)
    return below / len(sorted_vals)


def _days_since(date_str, reference=None):
    if not date_str:
        return 999
    reference = reference or SIMULATED_TODAY
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
    except ValueError:
        return 999
    return max(0, (reference - d).days)


def build_service_co_occurrence(account_services_map: dict) -> dict:
    """
    account_services_map: {account_code: set(item_name, ...)} — 원자재/부품/소모품/완제품/
    물류/IT서비스 등 실제 거래 품목 전체(카테고리 무관)를 담은 집합.

    반환: {(it_service, other_item): 두 품목을 함께 구매한 거래처 수}. CORE_SERVICES(추천
    후보인 IT서비스 8종) 각각에 대해, 그 거래처가 함께 사거나 안 사는 "다른 모든 품목"과의
    동시 구매 빈도를 계산한다 — 원자재/부품만 사는 거래처도 장바구니 유사도로 추천이
    가능하도록, 짝을 CORE_SERVICES 안으로 제한하지 않는다.
    """
    all_sets = list(account_services_map.values())
    all_items = set()
    for s in all_sets:
        all_items |= s

    co = {}
    for it_service in CORE_SERVICES:
        for other in all_items:
            if other == it_service:
                continue
            count = sum(1 for s in all_sets if it_service in s and other in s)
            if count:
                co[(it_service, other)] = count
    return co


def compute_opportunity(
    account_code: str,
    owned_services: set,
    revenue: float,
    all_revenues: list,
    interest_signal_rate: float,
    days_since_last_contact: int,
    co_occurrence: dict,
) -> dict:
    """영업기회 점수(0~100)와 추천 서비스를 계산한다."""
    size_score = _percentile_rank(revenue, all_revenues) * 40

    missing = [s for s in CORE_SERVICES if s not in owned_services]
    coverage_gap_ratio = len(missing) / len(CORE_SERVICES)
    coverage_score = coverage_gap_ratio * 25

    interest_score = _clamp(interest_signal_rate, 0, 1) * 20

    recency_score = _clamp(15 * (1 - days_since_last_contact / 180), 0, 15)

    total = round(size_score + coverage_score + interest_score + recency_score, 1)
    total = _clamp(total, 0, 100)

    recommended_service = None
    best_affinity = -1
    affinity_note = ""
    if missing:
        for candidate in missing:
            affinity = sum(
                co_occurrence.get((candidate, owned), 0) for owned in owned_services
            )
            if affinity > best_affinity:
                best_affinity = affinity
                recommended_service = candidate
        if recommended_service and best_affinity > 0:
            affinity_note = (
                f"보유 서비스와 함께 쓰이는 사례 {best_affinity}건을 근거로 "
                f"'{recommended_service}'을(를) 추천했습니다."
            )
        elif recommended_service:
            affinity_note = f"아직 다른 거래처와의 공통 사용 사례는 적지만, 미보유 서비스 중 하나로 '{recommended_service}'을(를) 제안합니다."

    rationale_parts = [
        f"연간매출 규모 상위 {round((1 - _percentile_rank(revenue, all_revenues)) * 100)}% 수준(가중 {round(size_score,1)}점)",
        f"보유하지 않은 서비스가 {len(missing)}/{len(CORE_SERVICES)}개로 확장 여지가 있음(가중 {round(coverage_score,1)}점)",
        f"최근 문의 중 관심 신호 비율 {round(interest_signal_rate*100)}%(가중 {round(interest_score,1)}점)",
        f"최근 거래 후 {days_since_last_contact}일 경과(가중 {round(recency_score,1)}점)",
    ]
    if affinity_note:
        rationale_parts.append(affinity_note)

    if total >= 70:
        action = "우선 컨택 후 제안 미팅 추진"
    elif total >= 40:
        action = "정기 컨택과 함께 소개 자료 공유"
    else:
        action = "현재는 관망, 다음 분기 재평가"

    return {
        "opportunity_score": total,
        "recommended_service": recommended_service,
        "ai_rationale": " / ".join(rationale_parts),
        "recommended_action": action,
    }


def compute_risk(inquiry_rows: list, contract_end_date: str, reference=None) -> dict:
    """
    inquiry_rows: [{"voc_tag":..., "repeat_inquiry": bool, "rating": float|None}, ...]
    """
    n = len(inquiry_rows)
    if n == 0:
        churn_rate = 0.0
        repeat_rate = 0.0
        avg_rating = 4.0
    else:
        churn_rate = sum(1 for r in inquiry_rows if r.get("voc_tag") == "이탈징후") / n
        repeat_rate = sum(1 for r in inquiry_rows if r.get("repeat_inquiry")) / n
        ratings = [r["rating"] for r in inquiry_rows if r.get("rating") is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 4.0

    churn_score = churn_rate * 40
    repeat_score = repeat_rate * 20
    rating_score = (1 - _clamp(avg_rating / 5, 0, 1)) * 20

    days_left = _days_since(contract_end_date, reference) * -1 if contract_end_date else None
    contract_score = 0
    if contract_end_date:
        days_to_end = None
        try:
            d = datetime.strptime(str(contract_end_date)[:10], "%Y-%m-%d")
            days_to_end = (d - (reference or SIMULATED_TODAY)).days
        except ValueError:
            days_to_end = None
        if days_to_end is not None:
            if 0 <= days_to_end <= 90:
                contract_score = 20
            elif 90 < days_to_end <= 180:
                contract_score = 10

    total = round(churn_score + repeat_score + rating_score + contract_score, 1)
    total = _clamp(total, 0, 100)

    if total >= 70:
        tier = "위험"
    elif total >= 40:
        tier = "주의"
    elif total >= 20:
        tier = "관심"
    else:
        tier = "정상"

    findings = []
    if n > 0:
        findings.append(f"최근 상담 {n}건 중 이탈징후 태그 비율 {round(churn_rate*100)}%")
        findings.append(f"동일 유형 재문의 비율 {round(repeat_rate*100)}%")
        findings.append(f"평균 만족도 평점 {round(avg_rating,1)}/5")
    if contract_score > 0:
        findings.append("계약 종료일이 임박했습니다.")
    if not findings:
        findings.append("최근 특이 신호가 감지되지 않았습니다.")

    if tier in ("위험", "주의"):
        action = "담당 영업사원의 고객 미팅 진행"
    elif tier == "관심":
        action = "다음 정기 컨택 때 이용 현황 확인"
    else:
        action = "특별 조치 불필요, 정기 모니터링 유지"

    return {
        "risk_score": total,
        "risk_tier": tier,
        "ai_findings": findings,
        "recommended_action": action,
    }


def compute_initial_stage(opportunity_score: float, risk_tier: str) -> str:
    if risk_tier in ("주의", "위험"):
        return "고객관리"
    if opportunity_score >= 70:
        return "제안"
    if opportunity_score >= 55:
        return "협의"
    if opportunity_score >= 40:
        return "미팅"
    if opportunity_score >= 25:
        return "고객접촉"
    return "영업기회 발견"


def generate_pre_meeting_brief(
    account: dict,
    owned_services: list,
    recent_inquiries: list,
    risk: dict,
    opportunity: dict,
) -> dict:
    pain_points = []
    for row in recent_inquiries[:5]:
        tag = row.get("voc_tag")
        if tag in VOC_TAG_PLAIN and VOC_TAG_PLAIN[tag] not in pain_points:
            pain_points.append(VOC_TAG_PLAIN[tag])
    if not pain_points:
        pain_points.append("최근 뚜렷한 불편 신호는 없습니다.")

    questions = ["현재 이용 중인 서비스에 불편한 점은 없으신가요?"]
    if risk.get("risk_tier") in ("주의", "위험"):
        questions.append("최근 문의가 늘었는데, 서비스 이용에 어려움이 있으셨는지 확인이 필요합니다.")
    if opportunity.get("recommended_service"):
        questions.append(f"{opportunity['recommended_service']} 도입을 검토해보신 적 있으신가요?")
    questions.append("다음 계약 갱신/확장 시점에 우선적으로 고려하는 조건이 있으신가요?")

    if risk.get("risk_tier") in ("주의", "위험"):
        direction = "신규 제안보다 현재 서비스 불편사항 해소와 신뢰 회복을 우선하세요."
    elif opportunity.get("opportunity_score", 0) >= 55:
        direction = "적극적으로 추천 서비스를 소개하고 다음 단계(제안서) 일정을 잡으세요."
    else:
        direction = "관계 유지 차원의 정기 미팅으로 진행하고, 새로운 니즈가 있는지 탐색하세요."

    return {
        "account_status": f"{account.get('name')} ({account.get('industry')}, {account.get('contract_size_tier')}등급)",
        "current_services": owned_services,
        "recent_inquiries": [
            f"{r.get('inquiry_date','')} · {r.get('type_major','')} · {VOC_TAG_PLAIN.get(r.get('voc_tag'), r.get('voc_tag'))}"
            for r in recent_inquiries[:3]
        ],
        "expected_pain_points": pain_points,
        "recommended_service": opportunity.get("recommended_service"),
        "suggested_questions": questions,
        "recommended_direction": direction,
    }


def extract_meeting_fields(notes_raw: str) -> dict:
    """
    미팅 후 자유 입력 텍스트에서 구조화된 필드를 뽑아낸다.
    실제 NLP가 아니라 키워드/패턴 매칭 시뮬레이션임을 명확히 한다.
    """
    text = notes_raw or ""
    lower = text.lower()

    interest_services = sorted(
        {svc for kw, svc in KEYWORD_MAP.items() if kw in lower}
    )

    pain_points = sorted(
        {label for kw, label in PAIN_KEYWORDS.items() if kw in text}
    )

    pos_hits = sum(text.count(w) for w in POSITIVE_NOTE_WORDS)
    neg_hits = sum(text.count(w) for w in NEGATIVE_NOTE_WORDS)
    if pos_hits > neg_hits:
        reaction = "긍정적"
    elif neg_hits > pos_hits:
        reaction = "부정적"
    else:
        reaction = "중립적"

    sentences = re.split(r"[.\n。]", text)
    requirements = [
        s.strip()
        for s in sentences
        if s.strip() and any(marker in s for marker in REQUIREMENT_MARKERS)
    ]
    if not requirements:
        requirements = ["명시적인 요구사항 문장을 찾지 못했습니다 — 원문을 직접 확인하세요."]

    date_match = re.search(r"(다음\s*주|\d{1,2}월\s*\d{1,2}일|\d{1,2}/\d{1,2})", text)
    next_schedule = date_match.group(0) if date_match else "일정 미정 (직접 입력 필요)"

    followups = requirements[:3] if requirements else ["후속 확인사항 없음"]
    if interest_services:
        next_action = f"{interest_services[0]} 관련 제안 자료 준비"
    else:
        next_action = "다음 컨택 일정 조율"

    return {
        "extracted_requirements": requirements,
        "extracted_pain_points": pain_points or ["특이 불편사항 언급 없음"],
        "extracted_interest_services": interest_services,
        "extracted_customer_reaction": reaction,
        "extracted_followup_items": followups,
        "extracted_next_action": next_action,
        "extracted_next_schedule": next_schedule,
    }


def generate_proposal_draft(
    account: dict, opportunity: dict, risk: dict, meeting: dict | None
) -> dict:
    key_problems = list(risk.get("ai_findings", []))
    if meeting and meeting.get("extracted_pain_points"):
        key_problems.extend(meeting["extracted_pain_points"])

    recommended = opportunity.get("recommended_service") or "CRM클라우드"
    benefit = SERVICE_BENEFITS.get(recommended, "업무 효율 개선에 도움이 됩니다.")

    stage_next_steps = {
        "영업기회 발견": "담당자 미팅 일정을 우선 확정합니다.",
        "고객접촉": "니즈 파악을 위한 미팅을 진행합니다.",
        "미팅": "미팅 결과를 바탕으로 맞춤 제안서를 공유합니다.",
        "제안": "제안 내용에 대한 고객 피드백을 수집하고 협의를 진행합니다.",
        "협의": "계약 조건을 조율하고 계약서를 준비합니다.",
        "계약": "도입 일정을 수립하고 온보딩을 지원합니다.",
        "고객관리": "불편사항을 우선 해소한 뒤 추가 제안을 검토합니다.",
    }

    return {
        "customer_situation": f"{account.get('name')}은(는) 현재 {account.get('contract_size_tier')}등급 거래처로, "
        f"연간매출 {int(account.get('annual_revenue') or 0):,}원 규모입니다.",
        "key_problems": key_problems or ["뚜렷한 문제 신호는 없으나, 서비스 확장 여지가 있습니다."],
        "solution_direction": f"'{recommended}' 도입을 통해 현재 이용 서비스와의 연계 효과를 높이는 방향을 제안합니다.",
        "recommended_service": recommended,
        "expected_effect": benefit,
        "next_steps": stage_next_steps.get(
            account.get("current_stage", "영업기회 발견"), "다음 액션을 담당자가 정합니다."
        ),
    }


# ============================================================================
# 신규 영업(프로스펙팅) — 시장 전망 · 적합도 분석 · 이트너스 경영지원 제안서
# ----------------------------------------------------------------------------
# 위 CORE_SERVICES/SERVICE_BENEFITS는 "이미 거래 중인 60개 거래처에게 IT서비스를
# 추가로 파는" 업셀 시나리오용이다. 이 섹션은 반대로 "이 거래처가 이트너스의 실제
# 사업(인사·총무 경영지원 BPO)의 신규 영업 대상으로서 얼마나 매력적인가"를 평가해,
# 영업담당자가 상부에 보고하거나 실제 컨택에 쓸 수 있는 제안서를 만드는 용도다.
# 이트너스 실제 패밀리 서비스 라인업(etners.com/welcome.etners.com에서 확인한
# 공식 서비스명)을 후보로 쓴다 — 넥스트라인이 파는 가상 서비스가 아니라 실제 이트너스
# 사업이라는 점에서 위 섹션과 성격이 다르다.
# ============================================================================

ETNERS_SERVICES = {
    "SHARED SERVICE": "인사·총무 업무 전반을 통합 대행하는 경영지원 서비스",
    "ESRM": "임직원 업무요청(급여/복리후생/총무 등)을 한곳에서 접수·처리하는 기록관리 솔루션",
    "PAYROLL": "급여 계산부터 지급까지 대행하는 급여 아웃소싱 서비스",
    "GAMDONG TIME": "임직원 복지포인트·리워드 운영 서비스",
    "HOUSING": "임직원 사택·주거 지원 운영 서비스",
    "MOVING": "임직원 이사 지원 서비스",
    "RELOCATION": "해외 주재원 등 임직원 이주 지원 서비스",
    "BIDDING": "구매·입찰 프로세스 대행 서비스",
}

ETNERS_SERVICE_BENEFITS = {
    "SHARED SERVICE": "인사/총무 담당 인력을 늘리지 않고도 표준화된 프로세스로 업무 품질을 높일 수 있습니다.",
    "ESRM": "이메일·전화·메신저로 흩어져 있던 임직원 요청을 한 곳에서 추적·관리해 누락을 없앨 수 있습니다.",
    "PAYROLL": "매월 반복되는 급여 계산/신고 업무 부담과 오류 리스크를 전문 대행으로 줄일 수 있습니다.",
    "GAMDONG TIME": "임직원 복지 만족도를 높이는 리워드 운영을 직접 구축하지 않고 바로 도입할 수 있습니다.",
    "HOUSING": "지방/해외 발령 임직원의 주거 문제를 표준화된 절차로 지원할 수 있습니다.",
    "MOVING": "임직원 이사 지원 업무를 총무팀이 직접 처리하지 않아도 됩니다.",
    "RELOCATION": "해외 주재원 파견 시 발생하는 행정 부담을 전문 대행사에 위임할 수 있습니다.",
    "BIDDING": "구매/입찰 프로세스를 표준화해 처리 시간과 리스크를 줄일 수 있습니다.",
}

# 업종별로 "인사/총무 등 경영지원 수요가 얼마나 클 것으로 보이는가"에 대한 가중치.
# 사무직 비중이 높고 조직 관리가 복잡할수록 높게 잡았다 — 실제 인사 데이터가 아니라
# 업종 특성에 대한 합리적 가정이므로, 근거 문장에 "업종 특성상"이라고 명시한다.
INDUSTRY_FIT_WEIGHT = {
    "컨설팅": 30,
    "IT솔루션": 28,
    "서비스업체": 26,
    "유통업체": 20,
    "제조업체": 16,
    "물류업체": 14,
    "원자재공급": 12,
}

SIZE_FIT_WEIGHT = {"A(대형)": 40, "B(중형)": 25, "C(소형)": 12}
SIZE_TO_SERVICE = {"A(대형)": "SHARED SERVICE", "B(중형)": "ESRM", "C(소형)": "PAYROLL"}


def _revenue_trend(transactions: list) -> tuple[str, float]:
    """
    transactions: [{"txn_date": "YYYY-MM-DD", "amount": float}, ...]
    최근 절반 기간과 이전 절반 기간의 총 거래금액을 비교해 추세를 판단한다.
    """
    dated = []
    for t in transactions:
        d = t.get("txn_date")
        if not d:
            continue
        try:
            dated.append((datetime.strptime(str(d)[:10], "%Y-%m-%d"), t.get("amount") or 0))
        except ValueError:
            continue
    if len(dated) < 4:
        return "보통", 0.0

    dated.sort(key=lambda x: x[0])
    mid = len(dated) // 2
    earlier = sum(a for _, a in dated[:mid]) or 1
    later = sum(a for _, a in dated[mid:])
    growth = (later - earlier) / earlier

    if growth >= 0.15:
        return "상승", growth
    if growth <= -0.15:
        return "하락", growth
    return "보통", growth


def analyze_market_fit(account: dict, all_revenues: list, transactions: list) -> dict:
    """
    account: {"name","industry","region","contract_size_tier","annual_revenue"}
    transactions: 이 거래처의 account_transactions 레코드 목록 (거래 추세 계산용)

    반환: 시장 전망(market_outlook), 적합도 점수/근거(fit_score/fit_findings),
    추천 이트너스 서비스(recommended_service)를 담은 dict. 전부 실제 보유 데이터
    (업종/지역/매출/거래추세/기업규모)로부터 산출되며, 최종 판단은 영업담당자 몫이다.
    """
    revenue = account.get("annual_revenue") or 0
    percentile = round(_percentile_rank(revenue, all_revenues) * 100)
    trend_label, growth_rate = _revenue_trend(transactions)
    industry = account.get("industry")
    size_tier = account.get("contract_size_tier")

    trend_sentence = {
        "상승": f"최근 거래 규모가 이전 대비 {round(growth_rate*100)}% 늘어나는 추세로, 사업이 확장 국면에 있는 것으로 보입니다.",
        "하락": f"최근 거래 규모가 이전 대비 {round(abs(growth_rate)*100)}% 줄어드는 추세로, 사업 축소 또는 거래 비중 감소 가능성이 있습니다.",
        "보통": "최근 거래 규모는 큰 변동 없이 유지되고 있습니다.",
    }[trend_label]

    market_outlook = (
        f"{industry} 업종, 연매출 규모는 전체 거래처 중 상위 {100 - percentile}% 수준입니다. {trend_sentence}"
    )

    size_score = SIZE_FIT_WEIGHT.get(size_tier, 12)
    industry_score = INDUSTRY_FIT_WEIGHT.get(industry, 15)
    revenue_score = round(_percentile_rank(revenue, all_revenues) * 30)
    fit_score = _clamp(size_score + industry_score + revenue_score, 0, 100)

    fit_findings = [
        f"기업 규모 {size_tier} 등급 (가중 {size_score}점) — 규모가 클수록 인사/총무 업무량과 표준화 필요성이 커집니다.",
        f"업종 특성상 {industry}은(는) 경영지원 수요가 {'높은' if industry_score >= 25 else '중간' if industry_score >= 18 else '상대적으로 낮은'} 편으로 가정합니다 (가중 {industry_score}점).",
        f"연매출 규모 상위 {100 - percentile}% 수준 (가중 {revenue_score}점).",
    ]

    recommended_service = SIZE_TO_SERVICE.get(size_tier, "ESRM")

    if fit_score >= 65:
        recommendation = "신규 영업 우선순위가 높은 후보입니다. 담당자 컨택을 추천합니다."
    elif fit_score >= 40:
        recommendation = "중장기 관찰 후보입니다. 정보 축적과 함께 컨택 시점을 조율하세요."
    else:
        recommendation = "현재 시점에서는 우선순위가 낮은 후보입니다."

    return {
        "market_outlook": market_outlook,
        "revenue_percentile": percentile,
        "trend": trend_label,
        "fit_score": fit_score,
        "fit_findings": fit_findings,
        "recommended_service": recommended_service,
        "recommended_service_desc": ETNERS_SERVICES.get(recommended_service, ""),
        "recommendation": recommendation,
    }


def generate_etners_market_proposal(account: dict, market_fit: dict) -> dict:
    """market/fit 분석 결과를 바탕으로 신규 영업(프로스펙팅)용 이트너스 제안서를 만든다."""
    service = market_fit["recommended_service"]
    service_label = f"{service} ({ETNERS_SERVICES.get(service, '')})"
    benefit = ETNERS_SERVICE_BENEFITS.get(service, "경영지원 업무 부담을 줄일 수 있습니다.")

    return {
        "customer_situation": (
            f"{account.get('name')}({account.get('industry')}, {account.get('contract_size_tier')}등급)"
            f" — {market_fit['market_outlook']}"
        ),
        "key_problems": [
            f"적합도 점수 {market_fit['fit_score']}/100 — {market_fit['recommendation']}",
            *market_fit["fit_findings"],
        ],
        "solution_direction": f"이트너스 '{service_label}' 도입을 제안하여 경영지원 업무 효율화를 지원합니다.",
        "recommended_service": service_label,
        "expected_effect": benefit,
        "next_steps": "1차 미팅을 통해 현재 인사/총무 운영 방식을 확인하고, 적합한 서비스 범위를 구체화합니다.",
    }
