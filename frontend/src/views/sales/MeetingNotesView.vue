<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import http, { unwrap } from "../../api";

const props = defineProps({ id: [String, Number] });
const router = useRouter();
const meeting = ref(null);
const notes = ref("");
const loading = ref(false);

onMounted(async () => {
  meeting.value = await unwrap(http.get(`/meetings/${props.id}`));
  notes.value = meeting.value.notes_raw || "";
});

async function submit() {
  loading.value = true;
  try {
    meeting.value = await unwrap(http.put(`/meetings/${props.id}/notes`, { notes_raw: notes.value }));
  } finally {
    loading.value = false;
  }
}

function goProposal() {
  router.push({ name: "proposal-new", params: { code: meeting.value.account_code }, query: { meeting_id: meeting.value.id } });
}
</script>

<template>
  <h2>AI Meeting Copilot — 미팅 후 정리</h2>
  <div class="card stack" v-if="meeting">
    <label class="muted">미팅 메모 (자유롭게 입력하세요)</label>
    <textarea v-model="notes" rows="6" placeholder="예: 고객이 클라우드 이전을 요청함. 가격이 비싸다는 의견도 있었음..."></textarea>
    <button class="btn" @click="submit" :disabled="loading">{{ loading ? '분석 중...' : 'AI로 정리하기' }}</button>

    <div v-if="meeting.extracted_customer_reaction" class="card" style="background:#f7f8fc;">
      <div class="section-title" style="margin-top:0;font-size:14px;">AI 추출 결과 (키워드 기반 시뮬레이션)</div>
      <div><b>고객 요구사항:</b><ul><li v-for="(r,i) in meeting.extracted_requirements" :key="i">{{ r }}</li></ul></div>
      <div><b>Pain Point:</b> {{ (meeting.extracted_pain_points||[]).join(', ') }}</div>
      <div><b>관심 서비스:</b> {{ (meeting.extracted_interest_services||[]).join(', ') || '없음' }}</div>
      <div><b>고객 반응:</b> {{ meeting.extracted_customer_reaction }}</div>
      <div><b>다음 Action:</b> {{ meeting.extracted_next_action }}</div>
      <div><b>후속 일정:</b> {{ meeting.extracted_next_schedule }}</div>
      <button class="btn" style="margin-top:10px;" @click="goProposal">제안서 초안 생성하기</button>
    </div>
  </div>
</template>
