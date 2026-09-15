<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import http, { unwrap } from "../../api";

const route = useRoute();
const router = useRouter();
const proposal = ref(null);
const saved = ref(false);

onMounted(async () => {
  if (route.name === "proposal-edit") {
    proposal.value = await unwrap(http.get(`/proposals/${route.params.id}`));
  } else {
    proposal.value = await unwrap(
      http.post("/proposals", {
        account_code: route.params.code,
        meeting_id: route.query.meeting_id ? Number(route.query.meeting_id) : null,
      })
    );
  }
});

async function save() {
  proposal.value = await unwrap(
    http.put(`/proposals/${proposal.value.id}`, {
      customer_situation: proposal.value.customer_situation,
      key_problems: proposal.value.key_problems,
      solution_direction: proposal.value.solution_direction,
      recommended_service: proposal.value.recommended_service,
      expected_effect: proposal.value.expected_effect,
      next_steps: proposal.value.next_steps,
    })
  );
  saved.value = true;
  setTimeout(() => (saved.value = false), 2000);
}

function backToList() {
  router.push({ name: "sales-proposals" });
}
</script>

<template>
  <h2>AI 제안서 초안</h2>
  <p class="muted">AI가 만든 초안입니다 — 검토 후 자유롭게 수정하세요.</p>

  <div v-if="proposal" class="card stack">
    <span class="badge" style="align-self:flex-start;background:var(--accent-soft);color:var(--accent);">{{ proposal.status }}</span>

    <label class="muted">1. 고객 현황</label>
    <textarea v-model="proposal.customer_situation" rows="2"></textarea>

    <label class="muted">2. 고객의 주요 문제</label>
    <textarea v-model="proposal.key_problems" rows="3"></textarea>

    <label class="muted">3. 해결 방향</label>
    <textarea v-model="proposal.solution_direction" rows="2"></textarea>

    <label class="muted">4. 추천 이트너스 서비스</label>
    <input v-model="proposal.recommended_service" />

    <label class="muted">5. 서비스 도입 기대효과</label>
    <textarea v-model="proposal.expected_effect" rows="2"></textarea>

    <label class="muted">6. 향후 진행 방향</label>
    <textarea v-model="proposal.next_steps" rows="2"></textarea>

    <div class="row">
      <button class="btn" @click="save">저장</button>
      <button class="btn secondary" @click="backToList">목록으로</button>
      <span v-if="saved" style="color:#1f7a4d;">저장되었습니다.</span>
    </div>
  </div>
</template>
