<script setup>
import { reactive, ref } from "vue";
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import http, { unwrap } from "../../api";
import { useAuthStore } from "../../stores/authStore";

const router = useRouter();
const auth = useAuthStore();
const opportunities = ref([]);
const expandedCode = ref(null);
const marketFit = reactive({}); // account_code -> analysis result
const loadingFit = ref(null);
const generating = ref(null);

onMounted(async () => {
  opportunities.value = await unwrap(http.get("/opportunities"));
});

function open(code) {
  router.push({ name: auth.isAdmin ? "admin-account-detail" : "sales-account-detail", params: { code } });
}

function scoreColor(score) {
  if (score >= 70) return "#1f7a4d";
  if (score >= 40) return "#a86a00";
  return "#888";
}

async function toggleAnalysis(code) {
  if (expandedCode.value === code) {
    expandedCode.value = null;
    return;
  }
  expandedCode.value = code;
  if (!marketFit[code]) {
    loadingFit.value = code;
    try {
      marketFit[code] = await unwrap(http.get(`/opportunities/${code}/market-fit`));
    } finally {
      loadingFit.value = null;
    }
  }
}

function fitColor(score) {
  if (score >= 65) return "#1f7a4d";
  if (score >= 40) return "#a86a00";
  return "#888";
}

async function generateEtnersProposal(code) {
  generating.value = code;
  try {
    const res = await unwrap(http.post(`/opportunities/${code}/etners-proposal`));
    router.push({ name: auth.isAdmin ? "admin-proposal-edit" : "proposal-edit", params: { id: res.id } });
  } finally {
    generating.value = null;
  }
}
</script>

<template>
  <h2>AI 영업기회 {{ auth.isAdmin ? '관리' : '탐지' }}</h2>
  <p class="muted">AI가 계산한 참고 점수입니다 — 실제 진행 여부는 담당자가 판단하세요.</p>

  <div class="grid" style="grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));">
    <div v-for="o in opportunities" :key="o.account_code" class="card stack">
      <div class="row" style="justify-content:space-between;cursor:pointer;" @click="open(o.account_code)">
        <b>{{ o.account_name }}</b>
        <span :style="{ color: scoreColor(o.opportunity_score), fontWeight: 700 }">{{ o.opportunity_score }}점</span>
      </div>
      <div class="muted" style="font-size:13px;">현재: {{ o.current_service_summary }}</div>
      <div style="font-size:13.5px;"><b>추천:</b> {{ o.recommended_service || '-' }}</div>
      <div class="muted" style="font-size:12.5px;">{{ o.ai_rationale }}</div>
      <div style="font-size:13px;color:var(--accent);">▶ {{ o.recommended_action }}</div>
      <div class="row" style="justify-content:space-between;">
        <span class="badge" style="background:var(--accent-soft);color:var(--accent);">{{ o.status }}</span>
        <button class="btn small secondary" @click="toggleAnalysis(o.account_code)">
          {{ expandedCode === o.account_code ? '분석 닫기' : 'AI 시장성·적합도 분석' }}
        </button>
      </div>

      <div v-if="expandedCode === o.account_code" style="border-top:1px solid var(--line);padding-top:12px;margin-top:2px;">
        <div v-if="loadingFit === o.account_code" class="muted">분석 중...</div>
        <div v-else-if="marketFit[o.account_code]" class="stack" style="gap:8px;">
          <div><b>시장 전망:</b> {{ marketFit[o.account_code].market_outlook }}</div>
          <div>
            <b>이트너스와의 적합도:</b>
            <span :style="{ color: fitColor(marketFit[o.account_code].fit_score), fontWeight: 700 }">
              {{ marketFit[o.account_code].fit_score }}/100
            </span>
          </div>
          <ul style="margin:0;padding-left:16px;font-size:12.5px;" class="muted">
            <li v-for="(f, i) in marketFit[o.account_code].fit_findings" :key="i">{{ f }}</li>
          </ul>
          <div style="font-size:13.5px;">
            <b>추천 이트너스 서비스:</b> {{ marketFit[o.account_code].recommended_services_label }}
            <div class="muted" style="font-size:12px;">{{ marketFit[o.account_code].recommended_service_desc }}</div>
          </div>
          <div style="color:var(--accent-dark);font-weight:600;font-size:13px;">▶ {{ marketFit[o.account_code].recommendation }}</div>
          <button
            class="btn"
            style="align-self:flex-start;"
            :disabled="generating === o.account_code"
            @click="generateEtnersProposal(o.account_code)"
          >
            {{ generating === o.account_code ? '생성 중...' : '이 회사 맞춤 이트너스 제안서 생성' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
