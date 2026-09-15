<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import http, { unwrap } from "../../api";
import { useAuthStore } from "../../stores/authStore";

const router = useRouter();
const auth = useAuthStore();
const risks = ref([]);
const accounts = ref([]);
const renewalOnly = ref(false);

onMounted(async () => {
  const [riskData, accountData] = await Promise.all([
    unwrap(http.get("/risk")),
    unwrap(http.get("/accounts")),
  ]);
  risks.value = riskData;
  accounts.value = accountData;
});

const accountInfo = computed(() => {
  const map = {};
  for (const a of accounts.value) map[a.code] = a;
  return map;
});

// 백엔드 ai_rules.SIMULATED_TODAY와 동일한 기준일. 실거래 데이터가 2025년 시점이라
// 실제 시스템 날짜를 쓰면 모든 계약이 이미 끝난 것으로 계산되어 버린다.
const SIMULATED_TODAY = new Date(2025, 8, 1); // 2025-09-01 (month is 0-indexed)

function daysToEnd(dateStr) {
  if (!dateStr) return null;
  const end = new Date(dateStr);
  if (isNaN(end)) return null;
  return Math.round((end - SIMULATED_TODAY) / 86400000);
}

function renewalLabel(days) {
  if (days === null) return null;
  if (days < 0) return `계약만료 D+${Math.abs(days)}`;
  return `재계약 D-${days}`;
}

// 계약 만료일까지 4개월(약 120일) 미만이면 "임박"으로 본다 (이미 지난 계약 포함).
const RENEWAL_WINDOW_DAYS = 120;

const rows = computed(() =>
  risks.value.map((r) => {
    const acc = accountInfo.value[r.account_code] || {};
    const days = daysToEnd(acc.contract_end_date);
    const renewalSoon = days !== null && days >= 0 && days < RENEWAL_WINDOW_DAYS;
    // "특이사항"은 AI가 정상 외의 신호(관심/주의/위험)를 감지한 경우.
    const hasFindings = r.risk_tier !== "정상";
    return {
      ...r,
      contract_start_date: acc.contract_start_date,
      contract_end_date: acc.contract_end_date,
      days_to_end: days,
      renewal_soon: renewalSoon,
      has_findings: hasFindings,
      needs_attention: renewalSoon || hasFindings,
    };
  })
);

const filteredRows = computed(() =>
  renewalOnly.value ? rows.value.filter((r) => r.needs_attention) : rows.value
);

function open(code) {
  router.push({ name: auth.isAdmin ? "admin-account-detail" : "sales-account-detail", params: { code } });
}
</script>

<template>
  <h2>고객 위험도 {{ auth.isAdmin ? '관리' : '알림' }}</h2>
  <p class="muted">AI가 문의/이용 패턴을 분석해 감지한 참고 신호입니다. 계약 만료가 4개월 이내로 다가왔거나 AI가 특이사항을 감지한 고객사만 배경색으로 강조 표시됩니다.</p>

  <label class="row" style="font-size:13.5px;margin-bottom:12px;">
    <input type="checkbox" v-model="renewalOnly" style="width:auto;" />
    확인이 필요한 고객사만 보기 (계약만료 4개월 이내 또는 특이사항)
  </label>

  <table class="simple">
    <thead><tr><th>고객사</th><th>위험도</th><th>계약기간</th><th>일정</th><th>AI 감지 내용</th><th>추천 액션</th></tr></thead>
    <tbody>
      <tr
        v-for="r in filteredRows"
        :key="r.account_code"
        style="cursor:pointer;background:#fff;"
        :style="r.needs_attention ? { background: 'var(--accent-soft)' } : {}"
        @click="open(r.account_code)"
      >
        <td>{{ r.account_name }}</td>
        <td><span class="badge" :class="r.risk_tier">{{ r.risk_tier }}</span></td>
        <td class="muted">{{ r.contract_start_date }} ~ {{ r.contract_end_date }}</td>
        <td>
          <span v-if="r.renewal_soon" class="badge" style="background:var(--accent);color:#fff;">
            {{ renewalLabel(r.days_to_end) }}
          </span>
          <span v-else-if="r.days_to_end !== null && r.days_to_end < 0" class="muted">
            {{ renewalLabel(r.days_to_end) }}
          </span>
          <span v-else class="muted">-</span>
        </td>
        <td><ul style="margin:0;padding-left:16px;"><li v-for="(f,i) in r.ai_findings" :key="i">{{ f }}</li></ul></td>
        <td>{{ r.recommended_action }}</td>
      </tr>
    </tbody>
  </table>
  <div class="muted" v-if="!filteredRows.length" style="margin-top:10px;">해당하는 고객사가 없습니다.</div>
</template>
