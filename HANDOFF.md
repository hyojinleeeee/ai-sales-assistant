# E:PACE (AI Sales Assistant) — 프로젝트 인수인계 문서

다른 Agent/세션에서 이 프로젝트를 이어서 작업할 때 참고할 수 있도록, 지금까지의 작업 전체를 정리한 문서입니다.

---

## 1. 이게 뭔가요

넥스트라인(NEXTLINE, 가상 IT기업)의 **영업 담당자용 AI 세일즈 어시스턴트**. 관리자(Admin)와 조직원(Sales User) 권한을 나눠, 고객사 관리·AI 영업기회 탐지·AI 미팅 Copilot·AI 제안서 초안·고객 위험도 감지 기능을 제공합니다.

**핵심 원칙**: "AI가 영업을 대신하는 시스템"이 아니라 "고객 데이터를 담당자가 행동할 수 있는 정보로 전환하는 시스템". 모든 AI 출력은 참고 정보로 표시됩니다.

브랜드명은 **E:PACE**로 리브랜딩되었고, 디자인은 이트너스(Etners) 공식 톤앤매너(ESRM 앱 참고, 공식 브랜드 오렌지 `#FF6D2D`)를 따릅니다.

---

## 2. 지금 바로 접속 가능한 것

- **라이브 사이트**: https://ai-sales-assistant-wheat-phi.vercel.app
- **데모 계정**: `admin`/`1234` (관리자), `sls001`~`sls040`/`1234` (조직원 40명)
- **GitHub 저장소(공개)**: https://github.com/hyojinleeeee/ai-sales-assistant
- **로컬 코드 위치**: `C:\workspace_claude\11_nextline_practice\output\ai_sales_assistant\`

---

## 3. 기술 스택

- **프론트엔드**: Vue 3 (`<script setup>`, Composition API, 상태관리 없이 화면에서 직접 axios 호출), Vue Router, 순수 CSS(디자인 시스템은 `App.vue`의 `:root` 변수)
- **백엔드**: FastAPI + SQLAlchemy, JWT 인증(`python-jose`), 비밀번호 해시는 `werkzeug.security`
- **DB**: 로컬은 SQLite 파일(`backend/sales_assistant.db`), 배포 환경은 Supabase Postgres (`DATABASE_URL` 환경변수 유무로 자동 분기, `backend/database.py` 참고)
- **AI 기능**: 실제 LLM 호출 없이 **설명 가능한 규칙 기반 로직**으로 시뮬레이션 (`backend/ai_rules.py` 하나에 전부 모여있음 — 나중에 진짜 LLM으로 바꿀 때 이 파일만 교체하면 됨)

---

## 4. 폴더 구조

```
output/ai_sales_assistant/
├── HANDOFF.md          ← 이 문서
├── CLAUDE.md            앱 자체 설명 + 시뮬레이션 caveat 문서
├── start_server.bat / shutdown_server.bat   로컬 실행 스크립트
├── backend/
│   ├── main.py           FastAPI 앱, CORS, 라우터 등록
│   ├── database.py       DB 연결 (SQLite ↔ Postgres 자동 분기 + 스키마 격리)
│   ├── models.py         SQLAlchemy 모델 전체
│   ├── schemas.py         Pydantic 요청 스키마 + 공통 응답 포맷
│   ├── auth.py            JWT 발급/검증, 비밀번호 해시
│   ├── scoping.py          조직원은 담당 거래처만 보게 하는 권한 필터 헬퍼
│   ├── ai_rules.py          ★ 규칙 기반 "AI" 로직 전부 (오퍼튜니티/위험도 점수식, 미팅 브리핑, 노트 추출, 제안서 생성)
│   ├── init_db.py            실데이터 시딩 스크립트 (data/*.xlsx 읽어서 DB 채움, 재실행해도 안전)
│   ├── vercel.json            Vercel 배포 설정
│   └── routers/                auth, users, accounts, opportunities, risk, pipeline, meetings, proposals, dashboard
└── frontend/
    ├── vite.config.js        로컬 개발용 /api 프록시(8004)
    ├── src/api/index.js         axios 인스턴스 (VITE_API_BASE로 배포 시 백엔드 주소 주입)
    ├── src/router/index.js       역할별 라우트 가드
    ├── src/stores/authStore.js     로그인 세션(localStorage)
    └── src/views/
        ├── LoginView.vue
        ├── admin/    AdminDashboardView, RepManageView, AccountListView, PipelineMonitorView
        ├── sales/    SalesDashboardView, MyAccountsView, MeetingBriefView, MeetingNotesView, ProposalDraftView, ProposalListView
        └── shared/   AccountDetailView, OpportunityListView, RiskListView (관리자/조직원 공용)
```

---

## 5. 데이터 모델 (요약)

실제 `11_nextline_practice/data/*.xlsx` 파일에서 시딩됩니다 (읽기 전용, 절대 수정 안 함).

| 테이블 | 내용 | 출처 |
|---|---|---|
| `users` | 41명 (관리자 1 + 영업담당 40) | `담당자코드_매핑_데이터.xlsx` |
| `accounts` | 거래처 60곳 | `거래처_담당자_매핑.xlsx` + `거래처_매입매출_데이터.xlsx` |
| `account_services` / `account_transactions` | 실제 거래 내역 | `매입매출거래내역` 시트 |
| `account_inquiry_signals` | 거래처별 CS 신호 시뮬레이션 | `고객문의_CS접수_데이터.xlsx`의 통계적 분포를 거래처 규모에 비례해 재현 (실제 1:1 매핑 아님 — B2C 데이터라 B2B 거래처와 연결할 키가 없어서 통계적으로 흉내냄) |
| `rep_performance` | 담당자별 실적 | `월별_매출_영업실적_데이터.xlsx` |
| `opportunities` / `risk_assessments` / `account_pipeline_state` | AI 계산 결과 | `ai_rules.py`로 계산, 시드 시 1회 + 필요시 재계산 API |
| `meetings` / `proposals` | 앱에서 직접 생성되는 데이터 | 시드 없음, 앱 사용하면서 쌓임 |

**추천 대상 서비스(CORE_SERVICES)는 8종 IT서비스**(DB관리/ERP유지보수/SW라이선스/네트워크관리/모니터링/백업서비스/보안솔루션/클라우드호스팅)로 한정 — 원자재/부품 사는 거래처에 원자재를 "추천"하는 게 의미 없어서 실제 거래 품목 카테고리 중 IT서비스만 추천 후보로 씀.

**중요 — 기준일(SIMULATED_TODAY)**: 실거래 데이터가 2025년 시점이라, 실제 시스템 날짜(코드 실행 시점)를 그대로 쓰면 모든 계약이 이미 끝난 것으로 계산됨. `ai_rules.py`의 `SIMULATED_TODAY = datetime(2025, 9, 1)` 상수로 고정되어 있고, 프론트엔드 `RiskListView.vue`에도 같은 값이 하드코딩되어 있음. **이 값을 바꾸려면 두 곳(백엔드 ai_rules.py, 프론트 RiskListView.vue) 다 맞춰야 함.**

---

## 6. AI 규칙 엔진 (`backend/ai_rules.py`)

- **영업기회 점수(0~100)**: 매출규모(40) + 서비스미보유비율(25) + 문의관심신호(20) + 최근거래경과일(15), 추천 서비스는 시장바구니 동시구매 분석(co-occurrence)으로 선정
- **위험도(정상/관심/주의/위험)**: 이탈징후 태그 비율(40) + 재문의 비율(20) + 평균평점(20) + 계약만료임박(20)
- **초기 영업단계**: 위 두 점수로부터 역산 (위험 신호 있으면 "고객관리", 아니면 기회점수 구간별 단계)
- **미팅 전 브리핑**: 이미 계산된 데이터 조합/템플릿
- **미팅 후 추출**: 진짜 NLP 아니고 키워드 매칭 시뮬레이션 (`KEYWORD_MAP`, `PAIN_KEYWORDS`) — 화면에도 "키워드 기반 시뮬레이션"이라고 명시됨
- **제안서 초안**: 계정+기회+위험+미팅 데이터를 템플릿에 채움

---

## 7. 인증

- JWT를 localStorage에 저장 (`authStore.js`), payload에 `sub/username/role/sls_code`
- 조직원(`role=sales`)은 `rep_sls_code`가 본인과 일치하는 거래처만 조회/수정 가능 (`scoping.py`), 위반 시 403 — 이미 교차 접근 테스트로 검증됨
- 데모용 고정 `SECRET_KEY`가 `auth.py`에 하드코딩되어 있음 (실서비스라면 반드시 환경변수로 분리해야 함, 지금은 교육용이라 의도적으로 남겨둠)

---

## 8. 로컬에서 다시 실행하기

```bash
# 백엔드
cd output/ai_sales_assistant/backend
pip install -r requirements.txt
python main.py          # http://localhost:8004, 최초 실행시 자동 시딩

# 프론트엔드 (새 터미널)
cd output/ai_sales_assistant/frontend
npm install
npm run dev              # http://localhost:5177
```

로컬은 `DATABASE_URL` 환경변수가 없으면 자동으로 SQLite를 씁니다. 배포된 DB(Postgres)에 로컬에서 붙여서 테스트하려면 `backend/.env`에 `DATABASE_URL`이 이미 들어있음 (git에는 안 올라감, `.gitignore` 처리됨).

---

## 9. 배포 구조 (중요 — 다시 배포/수정할 때 알아야 할 것)

- **GitHub**: 저장소 하나(`ai-sales-assistant`)에 `backend/`, `frontend/` 둘 다 들어있음. `main`(계정: hyojinleeeee) push하면 두 Vercel 프로젝트가 **각각 자동 재배포**됨.
- **Vercel — 백엔드**: 프로젝트명 `ai-sales-assistant-api`, `backend/vercel.json`이 `@vercel/python`으로 `main.py`(FastAPI ASGI app)를 그대로 서버리스로 띄움. 환경변수 `DATABASE_URL` 설정됨(Secret).
- **Vercel — 프론트엔드**: 프로젝트명 `ai-sales-assistant`, Vite 프레임워크 자동인식. 환경변수 `VITE_API_BASE=https://ai-sales-assistant-api-nine.vercel.app/api` (빌드타임에 번들에 박힘 — 백엔드 URL이 바뀌면 이 값도 다시 설정해야 함).
- **CORS**: 백엔드 `main.py`에서 `localhost:5177` + `*.vercel.app` 정규식 허용.
- **Supabase DB — 스키마 격리 트릭**: 이 앱은 **신규 Supabase 프로젝트를 만들지 않고**, 이전에 다른 앱(ENTS_TODO_APP, 프로젝트명 `20260915_ENTS_S`)이 쓰던 Supabase 프로젝트를 **같이 씁니다** (Supabase 무료 요금제가 계정당 활성 프로젝트 2개 제한이라 새로 못 만들었음). 대신 Postgres의 **전용 스키마 `ai_sales_assistant`**를 만들어 그 안에 테이블을 격리했습니다(`backend/database.py`에서 `MetaData(schema="ai_sales_assistant")` + `CREATE SCHEMA IF NOT EXISTS`). 같은 DB 인스턴스의 `public` 스키마에 있는 다른 앱의 `users`/`todos` 테이블과는 완전히 분리되어 있어 이름이 겹쳐도 충돌 없음. **다음에 정말 독립된 Supabase 프로젝트가 필요해지면**(무료 한도가 풀리거나 유료 전환 시) `database.py`의 `DATABASE_URL`만 새 프로젝트 값으로 바꾸면 됨 — 스키마 로직은 그대로 둬도 무방.

---

## 10. 디자인 시스템

- 서체: **Noto Sans KR** (Google Fonts)
- 브랜드 컬러: `--accent: #ff6d2d` (이트너스 공식 오렌지, Pantone Orange 021 U), `--accent-2: #fe5f40`
- 카드/버튼/뱃지 전부 큰 radius + 테두리 없는 옅고 넓은 그림자(`--shadow: 0 0 24px rgba(60,50,40,.07)`) — 이트너스 ESRM(esrm.etners.com) 톤앤매너 참고해서 "딱딱하지 않게" 다듬은 결과
- 위험도 배지 색(정상=초록/관심·주의=주황계열/위험=빨강)은 **의미색**이라 브랜드 액센트와 별개로 유지
- 전역 스타일은 전부 `frontend/src/App.vue`의 `<style>` 블록에 있음 (컴포넌트별 scoped 스타일 없이 공용 클래스 `.card`, `.btn`, `.badge`, `table.simple` 등을 재사용)

---

## 11. 알려진 제약사항 / 주의사항

- CS 문의 데이터는 **통계적 시뮬레이션**이지 실제 상담 이력 1:1 매핑이 아님 (§5 참고)
- 미팅 노트 "AI 추출"은 키워드 매칭이지 진짜 자연어 이해 아님
- `SIMULATED_TODAY`를 실제 "오늘"로 바꾸면(예: 데이터 리프레시 없이 그냥 datetime.now() 복구) 계약 만료 계산이 전부 깨짐 — 반드시 데이터 시점에 맞는 고정값을 써야 함
- 관리자용 "고객 정보 수정" API(`PUT /api/accounts/{code}`)는 백엔드엔 있지만 프론트 UI에서는 아직 연결 안 됨 (조회만 가능)
- JWT `SECRET_KEY`가 코드에 하드코딩됨 (교육용이라 의도적, 실서비스 전환 시 환경변수로 변경 필요)
- Supabase 무료 요금제 활성 프로젝트 2개 제한 — 위 §9 스키마 격리로 우회 중

---

## 12. 지금까지 진행된 주요 작업 순서

1. 요구사항서 기반 기획 → Plan 모드로 아키텍처 설계 승인받음
2. 백엔드 전체 구현(DB 스키마, 실데이터 시딩, AI 규칙엔진, JWT 인증, 9개 라우터) → curl로 전부 검증
3. 프론트엔드 전체 구현(로그인 + 관리자 6화면 + 조직원 6화면) → 브라우저로 클릭 테스트
4. 부서(팀)별 필터/드릴다운 기능 추가 (대시보드, 영업현황, 조직원관리, 고객사관리)
5. 브랜드 컬러 적용 (처음엔 잘못된 색 → 이트너스 공식 컬러(#FF6D2D)로 재수정)
6. 계약 만료일 기반 위험도 표시 로직 추가 + 날짜 기준점 버그 발견/수정(SIMULATED_TODAY)
7. 전체 고객사 관리에 엑셀 다운로드 + 값 기반 필터(업종/규모/담당자/연매출/영업단계/위험도/기회점수) 추가
8. ESRM 톤앤매너로 전체 디자인 리터치 (Noto Sans KR, 라운드/소프트 섀도우)
9. 사이트명 "E:PACE"로 리브랜딩
10. GitHub(공개) + Vercel(프론트/백엔드 분리 배포) + Supabase(스키마 격리) 로 실제 배포, 라이브 URL로 접속 가능하게 완료

---

## 13. 다음에 이어서 하면 좋을 것 (제안, 미해결 아님)

- 관리자용 고객사 정보 수정 UI 연결 (API는 이미 있음)
- 실제 LLM 연동 (ai_rules.py의 함수들을 실제 API 호출로 교체 — 인터페이스는 그대로 유지 가능하게 설계되어 있음)
- 비밀번호/JWT 시크릿을 환경변수로 분리 (실서비스 전환 시)
- 독립 Supabase 프로젝트로 이전 (무료 한도 해제/유료 전환 시)

---

## 14. 참고 — 재사용 가능한 배포 스킬

`C:\Users\ETNERS\.claude\skills\web-connector-260915\`에 이번에 쓴 GitHub+Vercel+Supabase 배포 절차가 스킬로 저장되어 있음. 다음에 또 다른 앱을 배포할 때 이 스킬을 부르면 같은 절차(툴 설치 → 로그인 → 리포/프로젝트 생성 → 배포 → 검증)를 자동으로 반복함.
