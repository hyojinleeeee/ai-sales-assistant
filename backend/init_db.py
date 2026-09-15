"""
넥스트라인 실제 데이터(엑셀)를 읽어 AI Sales Assistant용 SQLite DB를 채우는 1회성 시드
스크립트. data/, docs/ 원본 파일은 절대 수정하지 않고 읽기만 한다.

재실행해도 안전하도록(idempotent) users 테이블에 데이터가 이미 있으면 그대로 종료한다.
"""

import hashlib
import json
import os
import random
import sys
from datetime import datetime, timedelta

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd

import ai_rules
from auth import hash_password
from database import Base, SessionLocal, engine
from models import (
    Account,
    AccountInquirySignal,
    AccountPipelineState,
    AccountService,
    AccountTransaction,
    Opportunity,
    PipelineStageHistory,
    RepPerformance,
    RiskAssessment,
    User,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "data"))


def _p(filename):
    return os.path.join(DATA_DIR, filename)


def _clean(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _stable_rng(code: str) -> random.Random:
    seed = int(hashlib.md5(code.encode("utf-8")).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()

    if db.query(User).count() > 0:
        print("[INFO] 이미 시드된 DB입니다. 스킵합니다.")
        db.close()
        return

    print("[INFO] 데이터 시드를 시작합니다...")

    # ---------------------------------------------------------------- users
    sls_df = pd.read_excel(_p("담당자코드_매핑_데이터.xlsx"), sheet_name="SLS영업담당")
    for _, row in sls_df.iterrows():
        sls_code = row["담당자코드"]
        user = User(
            username=sls_code.lower(),
            password_hash=hash_password("1234"),
            role="sales",
            emp_code=_clean(row.get("사원번호(EMP)")),
            sls_code=sls_code,
            display_name=row["성명"],
            team=_clean(row.get("팀")),
            position=_clean(row.get("직급")),
            is_active=True,
        )
        db.add(user)

    admin = User(
        username="admin",
        password_hash=hash_password("1234"),
        role="admin",
        display_name="관리자",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    print(f"[INFO] users 시드 완료: {db.query(User).count()}명")

    # ------------------------------------------------------------- accounts
    map_df = pd.read_excel(_p("거래처_담당자_매핑.xlsx"), sheet_name="거래처담당매핑")
    master_df = pd.read_excel(
        _p("거래처_매입매출_데이터.xlsx"), sheet_name="거래처마스터"
    )
    merged = map_df.merge(
        master_df[
            [
                "거래처코드",
                "사업자번호",
                "대표담당자",
                "연락처",
                "연간거래건수",
                "평균거래금액(원)",
            ]
        ],
        on="거래처코드",
        how="left",
    )

    for _, row in merged.iterrows():
        account = Account(
            code=row["거래처코드"],
            name=row["거래처명"],
            industry=_clean(row.get("업종")),
            region=_clean(row.get("지역")),
            credit_grade=_clean(row.get("신용등급")),
            contract_size_tier=_clean(row.get("계약규모구분")),
            rep_sls_code=row["주담당자코드"],
            contract_start_date=str(_clean(row.get("담당시작일")) or ""),
            contract_end_date=str(_clean(row.get("계약종료일")) or ""),
            annual_revenue=float(_clean(row.get("연간총매출액(원)")) or 0),
            annual_purchase=float(_clean(row.get("연간총매입액(원)")) or 0),
            biz_reg_no=_clean(row.get("사업자번호")),
            main_contact_name=_clean(row.get("대표담당자")),
            main_contact_phone=_clean(row.get("연락처")),
            annual_txn_count=int(_clean(row.get("연간거래건수")) or 0),
            avg_txn_amount=float(_clean(row.get("평균거래금액(원)")) or 0),
        )
        db.add(account)
    db.commit()
    account_codes = [a.code for a in db.query(Account).all()]
    print(f"[INFO] accounts 시드 완료: {len(account_codes)}개")

    # ----------------------------------------------- transactions/services
    txn_df = pd.read_excel(
        _p("거래처_매입매출_데이터.xlsx"), sheet_name="매입매출거래내역"
    )
    txn_df = txn_df[txn_df["거래처코드"].isin(account_codes)]

    for _, row in txn_df.iterrows():
        db.add(
            AccountTransaction(
                account_code=row["거래처코드"],
                txn_date=str(_clean(row.get("거래일자")) or ""),
                item_category=_clean(row.get("품목카테고리")),
                item_name=_clean(row.get("품목명")),
                amount=float(_clean(row.get("합계금액(원)")) or 0),
                txn_type=_clean(row.get("거래유형")),
            )
        )

    sales_df = txn_df[txn_df["거래유형"] == "매출"]
    service_groups = sales_df.groupby(["거래처코드", "품목카테고리", "품목명"])
    account_services_map = {code: set() for code in account_codes}
    for (code, category, item_name), group in service_groups:
        db.add(
            AccountService(
                account_code=code,
                service_name=item_name,
                category=category,
                first_txn_date=str(group["거래일자"].min()),
                last_txn_date=str(group["거래일자"].max()),
                txn_count=len(group),
            )
        )
        account_services_map[code].add(item_name)
    db.commit()
    print(f"[INFO] account_transactions/services 시드 완료: {len(txn_df)}건 거래")

    # ------------------------------------------------- inquiry signals (§1)
    cs_df = pd.read_excel(_p("고객문의_CS접수_데이터.xlsx"))
    cs_rows = cs_df.to_dict("records")

    inquiry_map = {code: [] for code in account_codes}
    for account in db.query(Account).all():
        rng = _stable_rng(account.code)
        n = max(3, min(12, round((account.annual_txn_count or 20) / 5)))
        sampled = rng.choices(cs_rows, k=n)
        for i, src in enumerate(sampled):
            days_ago = rng.randint(1, 180)
            inquiry_date_str = (ai_rules.SIMULATED_TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            row = {
                "account_code": account.code,
                "inquiry_date": inquiry_date_str,
                "type_major": _clean(src.get("문의유형(대)")),
                "type_minor": _clean(src.get("문의유형(소)")),
                "voc_tag": _clean(src.get("VOC태그")),
                "rating": float(_clean(src.get("고객평점(5)")) or 0) or None,
                "nps": float(_clean(src.get("NPS점수(10)")) or 0) or None,
                "repeat_inquiry": _clean(src.get("재문의여부")) == "Y",
                "channel": _clean(src.get("접수채널")),
            }
            db.add(AccountInquirySignal(**row))
            inquiry_map[account.code].append(row)
    db.commit()
    print(f"[INFO] account_inquiry_signals 시드 완료 (거래처당 3~12건 시뮬레이션)")

    # ------------------------------------------------------- rep_performance
    perf_df = pd.read_excel(
        _p("월별_매출_영업실적_데이터.xlsx"), sheet_name="담당자별연간요약"
    )
    for _, row in perf_df.iterrows():
        db.add(
            RepPerformance(
                sls_code=row["담당자코드"],
                rep_name=row["담당자명"],
                team=_clean(row.get("소속팀")),
                target_revenue=float(_clean(row.get("연간목표매출(원)")) or 0),
                actual_revenue=float(_clean(row.get("연간실적매출(원)")) or 0),
                achievement_rate=float(_clean(row.get("연간달성률(%)")) or 0),
                quote_count=int(_clean(row.get("연간총견적건수")) or 0),
                order_count=int(_clean(row.get("연간총수주건수")) or 0),
                conversion_rate=float(_clean(row.get("연간수주전환율(%)")) or 0),
                kpi_grade=_clean(row.get("종합KPI등급")),
                rank=int(_clean(row.get("순위")) or 0),
            )
        )
    db.commit()
    print(f"[INFO] rep_performance 시드 완료: {len(perf_df)}명")

    # ------------------------------------------------- AI 파생 필드 계산
    co_occurrence = ai_rules.build_service_co_occurrence(account_services_map)
    all_revenues = [a.annual_revenue for a in db.query(Account).all()]

    for account in db.query(Account).all():
        owned = account_services_map.get(account.code, set())
        txns = (
            db.query(AccountTransaction)
            .filter(AccountTransaction.account_code == account.code)
            .all()
        )
        last_dates = [t.txn_date for t in txns if t.txn_date]
        if last_dates:
            latest = max(datetime.strptime(d, "%Y-%m-%d") for d in last_dates)
            days_since = (ai_rules.SIMULATED_TODAY - latest).days
        else:
            days_since = 999

        inquiries = inquiry_map[account.code]
        interest_tags = {"제안", "재구매의향", "단순문의"}
        interest_rate = (
            sum(1 for r in inquiries if r["voc_tag"] in interest_tags) / len(inquiries)
            if inquiries
            else 0
        )

        opp = ai_rules.compute_opportunity(
            account.code,
            owned,
            account.annual_revenue,
            all_revenues,
            interest_rate,
            days_since,
            co_occurrence,
        )
        current_services_text = ", ".join(sorted(owned)) if owned else "없음"
        db.add(
            Opportunity(
                account_code=account.code,
                current_service_summary=current_services_text,
                recommended_service=opp["recommended_service"],
                ai_rationale=opp["ai_rationale"],
                opportunity_score=opp["opportunity_score"],
                recommended_action=opp["recommended_action"],
                status="신규",
            )
        )

        risk = ai_rules.compute_risk(inquiries, account.contract_end_date)
        db.add(
            RiskAssessment(
                account_code=account.code,
                risk_tier=risk["risk_tier"],
                risk_score=risk["risk_score"],
                ai_findings=json.dumps(risk["ai_findings"], ensure_ascii=False),
                recommended_action=risk["recommended_action"],
            )
        )

        stage = ai_rules.compute_initial_stage(opp["opportunity_score"], risk["risk_tier"])
        db.add(AccountPipelineState(account_code=account.code, current_stage=stage))
        db.add(
            PipelineStageHistory(
                account_code=account.code, stage=stage, note="초기 시드값"
            )
        )

    db.commit()
    print("[INFO] opportunities/risk_assessments/pipeline_state 시드 완료")
    print("[INFO] 전체 시드 완료.")
    db.close()


if __name__ == "__main__":
    seed()
