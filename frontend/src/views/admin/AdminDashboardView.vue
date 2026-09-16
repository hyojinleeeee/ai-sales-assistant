<script setup>
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { cachedGet, unwrap } from "../../api";

const router = useRouter();
const data = ref(null);
const accounts = ref([]);
const accountsLoading = ref(false);
const selectedDept = ref("전체");

async function loadDashboard() {
  data.value = await unwrap(cachedGet("/dashboard/admin"));
}
loadDashboard();

// 고객사 목록은 대시보드 로딩과 무관하게, 실제로 특정 부서를 골랐을 때만 필요하다.
// 부서 선택 시에만 불러오되, cachedGet 덕분에 다른 화면에서 이미 불러온 목록이
// 있으면(30초 이내) 재요청 없이 바로 쓴다.
watch(selectedDept, async (dept) => {
  if (dept === "전체" || accounts.value.length || accountsLoading.value) return;
  accountsLoading.value = true;
  try {
    accounts.value = await unwrap(cachedGet("/accounts"));
  } finally {
    accountsLoading.value = false;
  }
});

const repInfo = computed(() => {
  const map = {};
  if (data.value) {
    for (const r of data.value.rep_status) map[r.sls_code] = r;
  }
  return map;
});

const departments = computed(() => {
  if (!data.value) return ["전체"];
  const set = new Set(data.value.rep_status.map((r) => r.team).filter(Boolean));
  return ["전체", ...Array.from(set).sort()];
});

const accountsForDept = computed(() => {
  if (selectedDept.value === "전체") return [];
  return accounts.value
    .filter((a) => repInfo.value[a.rep_sls_code]?.team === selectedDept.value)
    .sort((a, b) => a.current_stage?.localeCompare(b.current_stage));
});

function openAccount(code) {
  router.push({ name: "admin-account-detail", params: { code } });
}
</script>

<template>
  <div v-if="data">
    <h2>관리자 대시보드</h2>
    <div class="kpi-row">
      <div class="kpi-tile" style="cursor:pointer;" @click="router.push('/admin/accounts')"><div class="num">{{ data.total_accounts }}</div><div class="label">전체 고객사</div></div>
      <div class="kpi-tile" style="cursor:pointer;" @click="router.push('/admin/opportunities')"><div class="num">{{ data.new_opportunities }}</div><div class="label">신규 영업기회</div></div>
      <div class="kpi-tile" style="cursor:pointer;" @click="router.push('/admin/pipeline')"><div class="num">{{ data.in_progress_accounts }}</div><div class="label">진행 중인 영업</div></div>
      <div class="kpi-tile" style="cursor:pointer;" @click="router.push('/admin/pipeline')"><div class="num">{{ data.upcoming_meetings }}</div><div class="label">미팅 예정</div></div>
      <div class="kpi-tile" style="cursor:pointer;" @click="router.push('/admin/proposals')"><div class="num">{{ data.proposals_in_progress }}</div><div class="label">제안 진행</div></div>
      <div class="kpi-tile" style="cursor:pointer;" @click="router.push('/admin/risk')"><div class="num">{{ data.at_risk_accounts }}</div><div class="label">이탈위험 감지</div></div>
    </div>

    <div class="section-title">조직원별 영업 현황</div>
    <div class="row" style="margin-bottom:12px;">
      <label class="muted" for="dash-dept-select">부서 선택</label>
      <select id="dash-dept-select" v-model="selectedDept">
        <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
      </select>
    </div>

    <table class="simple" v-if="selectedDept === '전체'">
      <thead>
        <tr><th>담당자</th><th>팀</th><th>담당 고객사</th><th>신규 기회</th><th>이탈위험</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in data.rep_status" :key="r.sls_code">
          <td>{{ r.display_name }} ({{ r.sls_code }})</td>
          <td>{{ r.team }}</td>
          <td>{{ r.account_count }}</td>
          <td>{{ r.new_opportunity_count }}</td>
          <td>{{ r.at_risk_count }}</td>
        </tr>
      </tbody>
    </table>

    <template v-else>
      <div class="section-title" style="margin-top:0;">{{ selectedDept }} · 접촉 고객사 및 진행현황</div>
      <div class="muted" v-if="accountsLoading">불러오는 중...</div>
      <table class="simple" v-else>
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
      <div class="muted" v-if="!accountsLoading && !accountsForDept.length" style="margin-top:8px;">이 부서가 담당하는 고객사가 없습니다.</div>
    </template>
  </div>
  <div v-else class="muted">불러오는 중...</div>
</template>
