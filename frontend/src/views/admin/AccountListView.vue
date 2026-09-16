<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import * as XLSX from "xlsx";
import { cachedGet, unwrap } from "../../api";

const router = useRouter();
const accounts = ref([]);
const search = ref("");

const STAGES = ["영업기회 발견", "고객접촉", "미팅", "제안", "협의", "계약", "고객관리"];
const RISK_TIERS = ["정상", "관심", "주의", "위험"];
const SIZE_TIERS = ["A(대형)", "B(중형)", "C(소형)"];

const REVENUE_BUCKETS = [
  { label: "전체", test: () => true },
  { label: "5억 미만", test: (v) => v < 500_000_000 },
  { label: "5억 ~ 15억", test: (v) => v >= 500_000_000 && v < 1_500_000_000 },
  { label: "15억 ~ 30억", test: (v) => v >= 1_500_000_000 && v < 3_000_000_000 },
  { label: "30억 이상", test: (v) => v >= 3_000_000_000 },
];

const SCORE_BUCKETS = [
  { label: "전체", test: () => true },
  { label: "70점 이상", test: (v) => v >= 70 },
  { label: "40 ~ 69점", test: (v) => v >= 40 && v < 70 },
  { label: "40점 미만", test: (v) => v < 40 },
];

const filters = ref({
  industry: "전체",
  contract_size_tier: "전체",
  rep_sls_code: "전체",
  revenue_bucket: "전체",
  current_stage: "전체",
  risk_tier: "전체",
  score_bucket: "전체",
});

onMounted(async () => {
  accounts.value = await unwrap(cachedGet("/accounts"));
});

const industries = computed(() => ["전체", ...new Set(accounts.value.map((a) => a.industry).filter(Boolean))].sort());
const reps = computed(() => {
  const set = new Set(accounts.value.map((a) => a.rep_sls_code).filter(Boolean));
  return ["전체", ...Array.from(set).sort()];
});

const filtered = computed(() => {
  const f = filters.value;
  const revenueTest = REVENUE_BUCKETS.find((b) => b.label === f.revenue_bucket)?.test || (() => true);
  const scoreTest = SCORE_BUCKETS.find((b) => b.label === f.score_bucket)?.test || (() => true);

  return accounts.value.filter((a) => {
    if (search.value && !a.name.includes(search.value) && !a.code.includes(search.value)) return false;
    if (f.industry !== "전체" && a.industry !== f.industry) return false;
    if (f.contract_size_tier !== "전체" && a.contract_size_tier !== f.contract_size_tier) return false;
    if (f.rep_sls_code !== "전체" && a.rep_sls_code !== f.rep_sls_code) return false;
    if (f.current_stage !== "전체" && a.current_stage !== f.current_stage) return false;
    if (f.risk_tier !== "전체" && a.risk_tier !== f.risk_tier) return false;
    if (!revenueTest(a.annual_revenue || 0)) return false;
    if (!scoreTest(a.opportunity_score || 0)) return false;
    return true;
  });
});

function resetFilters() {
  for (const k of Object.keys(filters.value)) filters.value[k] = "전체";
  search.value = "";
}

function fmt(n) {
  return n ? Math.round(n).toLocaleString() : "-";
}

function open(code) {
  router.push(`/admin/accounts/${code}`);
}

function downloadExcel() {
  const rows = filtered.value.map((a) => ({
    고객사: a.name,
    고객사코드: a.code,
    업종: a.industry,
    규모: a.contract_size_tier,
    담당자: a.rep_sls_code,
    연매출: a.annual_revenue,
    영업단계: a.current_stage,
    위험도: a.risk_tier,
    기회점수: a.opportunity_score,
  }));
  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "고객사현황");
  const today = new Date().toISOString().slice(0, 10);
  XLSX.writeFile(wb, `전체_고객사_현황_${today}.xlsx`);
}
</script>

<template>
  <div class="row" style="justify-content:space-between;align-items:flex-start;">
    <h2>전체 고객사 관리</h2>
    <button class="btn" @click="downloadExcel">⬇ 엑셀 다운로드</button>
  </div>

  <div class="row" style="margin-bottom:10px;">
    <input v-model="search" placeholder="고객사명/코드 검색" style="width:220px;" />
  </div>

  <div class="card row" style="margin-bottom:16px;gap:16px;">
    <div class="stack" style="gap:4px;">
      <label class="muted" style="font-size:12px;">업종</label>
      <select v-model="filters.industry">
        <option v-for="v in industries" :key="v" :value="v">{{ v }}</option>
      </select>
    </div>
    <div class="stack" style="gap:4px;">
      <label class="muted" style="font-size:12px;">규모</label>
      <select v-model="filters.contract_size_tier">
        <option value="전체">전체</option>
        <option v-for="v in SIZE_TIERS" :key="v" :value="v">{{ v }}</option>
      </select>
    </div>
    <div class="stack" style="gap:4px;">
      <label class="muted" style="font-size:12px;">담당자</label>
      <select v-model="filters.rep_sls_code">
        <option v-for="v in reps" :key="v" :value="v">{{ v }}</option>
      </select>
    </div>
    <div class="stack" style="gap:4px;">
      <label class="muted" style="font-size:12px;">연매출</label>
      <select v-model="filters.revenue_bucket">
        <option v-for="b in REVENUE_BUCKETS" :key="b.label" :value="b.label">{{ b.label }}</option>
      </select>
    </div>
    <div class="stack" style="gap:4px;">
      <label class="muted" style="font-size:12px;">영업단계</label>
      <select v-model="filters.current_stage">
        <option value="전체">전체</option>
        <option v-for="v in STAGES" :key="v" :value="v">{{ v }}</option>
      </select>
    </div>
    <div class="stack" style="gap:4px;">
      <label class="muted" style="font-size:12px;">위험도</label>
      <select v-model="filters.risk_tier">
        <option value="전체">전체</option>
        <option v-for="v in RISK_TIERS" :key="v" :value="v">{{ v }}</option>
      </select>
    </div>
    <div class="stack" style="gap:4px;">
      <label class="muted" style="font-size:12px;">기회점수</label>
      <select v-model="filters.score_bucket">
        <option v-for="b in SCORE_BUCKETS" :key="b.label" :value="b.label">{{ b.label }}</option>
      </select>
    </div>
    <button class="btn secondary small" style="align-self:flex-end;" @click="resetFilters">필터 초기화</button>
  </div>

  <div class="muted" style="margin-bottom:8px;">{{ filtered.length }}개 고객사 (전체 {{ accounts.length }}개 중)</div>

  <table class="simple">
    <thead>
      <tr>
        <th>고객사</th><th>업종</th><th>규모</th><th>담당자</th><th>연매출</th><th>영업단계</th><th>위험도</th><th>기회점수</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="a in filtered" :key="a.code" style="cursor:pointer;" @click="open(a.code)">
        <td>{{ a.name }} <span class="muted">({{ a.code }})</span></td>
        <td>{{ a.industry }}</td>
        <td>{{ a.contract_size_tier }}</td>
        <td>{{ a.rep_sls_code }}</td>
        <td>{{ fmt(a.annual_revenue) }}원</td>
        <td>{{ a.current_stage }}</td>
        <td><span class="badge" :class="a.risk_tier">{{ a.risk_tier }}</span></td>
        <td>{{ a.opportunity_score }}</td>
      </tr>
    </tbody>
  </table>
  <div class="muted" v-if="!filtered.length" style="margin-top:10px;">조건에 맞는 고객사가 없습니다.</div>
</template>
