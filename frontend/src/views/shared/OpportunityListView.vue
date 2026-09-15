<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import http, { unwrap } from "../../api";
import { useAuthStore } from "../../stores/authStore";

const router = useRouter();
const auth = useAuthStore();
const opportunities = ref([]);

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
</script>

<template>
  <h2>AI 영업기회 {{ auth.isAdmin ? '관리' : '탐지' }}</h2>
  <p class="muted">AI가 계산한 참고 점수입니다 — 실제 진행 여부는 담당자가 판단하세요.</p>

  <div class="grid" style="grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));">
    <div v-for="o in opportunities" :key="o.account_code" class="card stack" style="cursor:pointer;" @click="open(o.account_code)">
      <div class="row" style="justify-content:space-between;">
        <b>{{ o.account_name }}</b>
        <span :style="{ color: scoreColor(o.opportunity_score), fontWeight: 700 }">{{ o.opportunity_score }}점</span>
      </div>
      <div class="muted" style="font-size:13px;">현재: {{ o.current_service_summary }}</div>
      <div style="font-size:13.5px;"><b>추천:</b> {{ o.recommended_service || '-' }}</div>
      <div class="muted" style="font-size:12.5px;">{{ o.ai_rationale }}</div>
      <div style="font-size:13px;color:var(--accent);">▶ {{ o.recommended_action }}</div>
      <span class="badge" style="align-self:flex-start;background:var(--accent-soft);color:var(--accent);">{{ o.status }}</span>
    </div>
  </div>
</template>
