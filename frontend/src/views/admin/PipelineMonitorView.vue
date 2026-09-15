<script setup>
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { computed, onMounted, ref } from "vue";
import { Pie } from "vue-chartjs";
import { useRouter } from "vue-router";
import http, { unwrap } from "../../api";

ChartJS.register(ArcElement, Tooltip, Legend);

const STAGE_COLORS = ["#2ec4b6", "#4a7fd6", "#ff6b6b", "#ffc86b", "#8b6bff", "#5fbf6f", "#c9c9c9"];

const router = useRouter();
const summary = ref(null);
const reps = ref([]); // from /api/users: {sls_code, display_name, team, ...}
const accounts = ref([]); // from /api/accounts
const meetings = ref([]); // from /api/meetings
const selectedDept = ref("전체");

onMounted(async () => {
  // 4개를 Promise.all로 한꺼번에 쏘면 서버리스 콜드스타트가 겹치고 DB 커넥션 풀도
  // 동시에 눌러써서 오히려 더 느려진다(원격 Postgres에서 확인됨). 순서대로 하나씩
  // 불러오면서, 화면 위쪽(전체 파이프라인)부터 먼저 뜨도록 한다.
  summary.value = await unwrap(http.get("/pipeline/summary"));
  reps.value = await unwrap(http.get("/users"));
  accounts.value = await unwrap(http.get("/accounts"));
  meetings.value = await unwrap(http.get("/meetings"));
});

function pct(n, total) {
  return total ? Math.round((n / total) * 100) : 0;
}

const repInfo = computed(() => {
  const map = {};
  for (const r of reps.value) map[r.sls_code] = r;
  return map;
});

// 실제 이트너스 채용공고 기준 "영업·마케팅" 직무 중, 거래처를 직접 담당하는
// 이 40명의 역할은 전부 "영업/영업지원"에 해당한다 (영업기획/마케팅/MD는 별도 직무).
const jobFunction = "영업/영업지원 (Sales Support)";

const departments = computed(() => {
  const set = new Set(reps.value.map((r) => r.team).filter(Boolean));
  return ["전체", ...Array.from(set).sort()];
});

const deptSummary = computed(() => {
  if (!summary.value) return {};
  const result = {};
  for (const [sls, counts] of Object.entries(summary.value.by_rep)) {
    const team = repInfo.value[sls]?.team || "미배정";
    if (!result[team]) {
      result[team] = Object.fromEntries(summary.value.stages.map((s) => [s, 0]));
    }
    for (const s of summary.value.stages) {
      result[team][s] += counts[s] || 0;
    }
  }
  return result;
});

// 부서를 선택하면 상단 그래프도 그 부서 기준으로 바뀐다.
const displayedCounts = computed(() => {
  if (!summary.value) return {};
  if (selectedDept.value === "전체") return summary.value.counts;
  return deptSummary.value[selectedDept.value] || Object.fromEntries(summary.value.stages.map((s) => [s, 0]));
});

const displayedTotal = computed(() =>
  Object.values(displayedCounts.value).reduce((a, b) => a + b, 0)
);

// 파이차트 데이터 — 스테이지별 색상은 STAGE_COLORS를 그대로 매핑해 범례 색과 일치시킨다.
const pieData = computed(() => {
  if (!summary.value) return { labels: [], datasets: [] };
  return {
    labels: summary.value.stages,
    datasets: [
      {
        data: summary.value.stages.map((s) => displayedCounts.value[s] || 0),
        backgroundColor: STAGE_COLORS,
        borderColor: "#fff",
        borderWidth: 2,
      },
    ],
  };
});

const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
          const pct = total ? Math.round((ctx.parsed / total) * 1000) / 10 : 0;
          return `${ctx.label}: ${ctx.parsed}개 (${pct}%)`;
        },
      },
    },
  },
};

// 차트 옆에 표시할 범례용 퍼센트 목록 (0건인 단계는 숨긴다).
const stagePercents = computed(() => {
  if (!summary.value) return [];
  return summary.value.stages
    .map((s, i) => {
      const count = displayedCounts.value[s] || 0;
      const pct = displayedTotal.value ? Math.round((count / displayedTotal.value) * 1000) / 10 : 0;
      return { stage: s, count, pct, color: STAGE_COLORS[i] };
    })
    .filter((row) => row.count > 0);
});

const accountsForDept = computed(() => {
  if (selectedDept.value === "전체") return [];
  return accounts.value
    .filter((a) => repInfo.value[a.rep_sls_code]?.team === selectedDept.value)
    .sort((a, b) => a.current_stage?.localeCompare(b.current_stage));
});

const accountByCode = computed(() => {
  const map = {};
  for (const a of accounts.value) map[a.code] = a;
  return map;
});

function teamOf(accountCode) {
  const a = accountByCode.value[accountCode];
  return a ? repInfo.value[a.rep_sls_code]?.team || "미배정" : "미배정";
}

function inSelectedDept(team) {
  return selectedDept.value === "전체" || team === selectedDept.value;
}

function getWeekRange() {
  const now = new Date();
  const day = now.getDay();
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const monday = new Date(now);
  monday.setHours(0, 0, 0, 0);
  monday.setDate(now.getDate() + diffToMonday);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  sunday.setHours(23, 59, 59, 999);
  return [monday, sunday];
}

// 금주 미팅 예정: 이번 주(월~일) 안에 잡힌, 아직 진행 전인 미팅
const thisWeekMeetings = computed(() => {
  const [monday, sunday] = getWeekRange();
  return meetings.value
    .filter((m) => {
      if (m.status !== "예정" || !m.meeting_date) return false;
      const d = new Date(m.meeting_date);
      return d >= monday && d <= sunday && inSelectedDept(teamOf(m.account_code));
    })
    .map((m) => ({
      ...m,
      account_name: accountByCode.value[m.account_code]?.name || m.account_code,
      rep_name: repInfo.value[accountByCode.value[m.account_code]?.rep_sls_code]?.display_name,
      team: teamOf(m.account_code),
    }))
    .sort((a, b) => (a.meeting_date || "").localeCompare(b.meeting_date || ""));
});

// 미팅 준비 필요: 영업단계가 "미팅"인데 아직 예정된 미팅이 잡혀있지 않은 고객사
const meetingPrepNeeded = computed(() => {
  const scheduledCodes = new Set(meetings.value.filter((m) => m.status === "예정").map((m) => m.account_code));
  return accounts.value.filter(
    (a) => a.current_stage === "미팅" && !scheduledCodes.has(a.code) && inSelectedDept(teamOf(a.code))
  );
});

// 계약 진행중: 영업단계가 "협의" 또는 "계약"인 고객사
const contractInProgress = computed(() =>
  accounts.value.filter(
    (a) => ["협의", "계약"].includes(a.current_stage) && inSelectedDept(teamOf(a.code))
  )
);

function openAccount(code) {
  router.push({ name: "admin-account-detail", params: { code } });
}
</script>

<template>
  <h2>영업 현황 모니터링</h2>
  <p class="muted">영업기회 발견 → 고객접촉 → 미팅 → 제안 → 협의 → 계약 → 고객관리</p>

  <p class="muted" style="margin-top:14px;">
    담당 직무: <b>{{ jobFunction }}</b> — 이트너스 영업·마케팅 직무(영업기획/영업·영업지원/마케팅/MD) 중 거래처를 직접 관리하는 역할입니다.
  </p>

  <div class="row" style="margin-bottom:12px;">
    <label class="muted" for="dept-select">부서 선택</label>
    <select id="dept-select" v-model="selectedDept">
      <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
    </select>
  </div>

  <div v-if="summary" class="card stack">
    <div class="muted" style="font-weight:600;">{{ selectedDept }} 파이프라인</div>
    <div v-for="stage in summary.stages" :key="stage" class="row" style="align-items:center;">
      <div style="width:100px;font-size:13.5px;">{{ stage }}</div>
      <div style="flex:1;background:var(--accent-soft);border-radius:6px;overflow:hidden;height:22px;">
        <div
          style="background:var(--accent);height:100%;display:flex;align-items:center;padding-left:8px;color:#fff;font-size:12px;transition:width .2s;"
          :style="{ width: pct(displayedCounts[stage], displayedTotal) + '%' }"
        >
          {{ displayedCounts[stage] }}
        </div>
      </div>
    </div>
    <div class="muted">{{ selectedDept }} 총 {{ displayedTotal }}개 고객사</div>
  </div>

  <div v-if="summary" class="card" style="margin-top:14px;">
    <div class="muted" style="font-weight:600;margin-bottom:14px;">{{ selectedDept }} 영업 단계 보고서</div>
    <div class="row" style="align-items:center;gap:28px;flex-wrap:wrap;">
      <div style="width:200px;height:200px;flex-shrink:0;">
        <Pie :data="pieData" :options="pieOptions" />
      </div>
      <div class="stack" style="gap:8px;">
        <div v-for="row in stagePercents" :key="row.stage" class="row" style="gap:8px;font-size:13.5px;">
          <span style="width:10px;height:10px;border-radius:50%;display:inline-block;" :style="{ background: row.color }"></span>
          <span style="width:90px;">{{ row.stage }}</span>
          <b>{{ row.pct }}%</b>
          <span class="muted">({{ row.count }}개)</span>
        </div>
        <div class="muted" v-if="!stagePercents.length">표시할 데이터가 없습니다.</div>
      </div>
    </div>
  </div>

  <div class="section-title" style="margin-top:8px;">
    이번주 일정 관리 <span class="muted" style="font-weight:400;">({{ selectedDept }})</span>
  </div>

  <div class="grid" style="grid-template-columns:repeat(auto-fit, minmax(260px, 1fr));">
    <div class="card">
      <b>📅 금주 미팅 예정</b> <span class="muted">({{ thisWeekMeetings.length }}건)</span>
      <table class="simple" style="margin-top:10px;" v-if="thisWeekMeetings.length">
        <tbody>
          <tr v-for="m in thisWeekMeetings" :key="m.id" style="cursor:pointer;" @click="openAccount(m.account_code)">
            <td>{{ m.account_name }}<br><span class="muted">{{ m.team }} · {{ m.rep_name }}</span></td>
            <td>{{ m.meeting_date }}</td>
          </tr>
        </tbody>
      </table>
      <div class="muted" v-else style="margin-top:8px;">이번주 예정된 미팅이 없습니다.</div>
    </div>

    <div class="card">
      <b>📝 미팅 준비 필요</b> <span class="muted">({{ meetingPrepNeeded.length }}건)</span>
      <table class="simple" style="margin-top:10px;" v-if="meetingPrepNeeded.length">
        <tbody>
          <tr v-for="a in meetingPrepNeeded" :key="a.code" style="cursor:pointer;" @click="openAccount(a.code)">
            <td>{{ a.name }}<br><span class="muted">{{ teamOf(a.code) }} · {{ repInfo[a.rep_sls_code]?.display_name }}</span></td>
          </tr>
        </tbody>
      </table>
      <div class="muted" v-else style="margin-top:8px;">미팅 준비가 필요한 고객사가 없습니다.</div>
    </div>

    <div class="card">
      <b>📄 계약 진행중</b> <span class="muted">({{ contractInProgress.length }}건)</span>
      <table class="simple" style="margin-top:10px;" v-if="contractInProgress.length">
        <tbody>
          <tr v-for="a in contractInProgress" :key="a.code" style="cursor:pointer;" @click="openAccount(a.code)">
            <td>{{ a.name }}<br><span class="muted">{{ teamOf(a.code) }} · {{ repInfo[a.rep_sls_code]?.display_name }}</span></td>
            <td><span class="badge" style="background:var(--accent-soft);color:var(--accent-dark);">{{ a.current_stage }}</span></td>
          </tr>
        </tbody>
      </table>
      <div class="muted" v-else style="margin-top:8px;">계약 진행중인 고객사가 없습니다.</div>
    </div>
  </div>

  <div class="section-title">부서별 영업 단계 분포</div>
  <table class="simple" v-if="summary && selectedDept === '전체'">
    <thead>
      <tr><th>부서</th><th v-for="s in summary.stages" :key="s">{{ s }}</th><th>합계</th></tr>
    </thead>
    <tbody>
      <tr v-for="(counts, team) in deptSummary" :key="team">
        <td>{{ team }}</td>
        <td v-for="s in summary.stages" :key="s">{{ counts[s] }}</td>
        <td><b>{{ Object.values(counts).reduce((a, b) => a + b, 0) }}</b></td>
      </tr>
    </tbody>
  </table>

  <template v-if="selectedDept !== '전체'">
    <div class="section-title" style="margin-top:22px;">{{ selectedDept }} · 접촉 고객사 및 진행현황</div>
    <table class="simple">
      <thead>
        <tr><th>고객사</th><th>담당자</th><th>업종</th><th>영업단계</th><th>위험도</th><th>기회점수</th></tr>
      </thead>
      <tbody>
        <tr v-for="a in accountsForDept" :key="a.code" style="cursor:pointer;" @click="openAccount(a.code)">
          <td>{{ a.name }} <span class="muted">({{ a.code }})</span></td>
          <td>{{ repInfo[a.rep_sls_code]?.display_name || a.rep_sls_code }}</td>
          <td>{{ a.industry }}</td>
          <td>{{ a.current_stage }}</td>
          <td><span class="badge" :class="a.risk_tier">{{ a.risk_tier }}</span></td>
          <td>{{ a.opportunity_score }}</td>
        </tr>
      </tbody>
    </table>
    <div class="muted" v-if="!accountsForDept.length" style="margin-top:8px;">이 부서가 담당하는 고객사가 없습니다.</div>
  </template>
</template>
