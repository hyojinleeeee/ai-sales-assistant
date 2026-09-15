<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import http, { unwrap } from "../../api";

const props = defineProps({ code: String });
const router = useRouter();
const meetingDate = ref(new Date().toISOString().slice(0, 10));
const meeting = ref(null);
const loading = ref(false);

async function generate() {
  loading.value = true;
  try {
    meeting.value = await unwrap(http.post("/meetings", { account_code: props.code, meeting_date: meetingDate.value }));
  } finally {
    loading.value = false;
  }
}

function goNotes() {
  router.push({ name: "meeting-notes", params: { id: meeting.value.id } });
}
</script>

<template>
  <h2>AI Meeting Copilot — 미팅 전 브리핑</h2>
  <p class="muted">고객사 {{ code }} · AI가 생성한 참고 브리핑입니다.</p>

  <div class="card row" v-if="!meeting">
    <label>미팅일자</label>
    <input type="date" v-model="meetingDate" />
    <button class="btn" @click="generate" :disabled="loading">{{ loading ? '생성 중...' : '브리핑 생성' }}</button>
  </div>

  <div v-if="meeting" class="card stack">
    <div><b>고객사 현황:</b> {{ meeting.pre_brief.account_status }}</div>
    <div><b>현재 이용 서비스:</b> {{ meeting.pre_brief.current_services.join(', ') || '없음' }}</div>
    <div><b>최근 상담 내역:</b>
      <ul><li v-for="(r,i) in meeting.pre_brief.recent_inquiries" :key="i">{{ r }}</li></ul>
    </div>
    <div><b>예상 Pain Point:</b>
      <ul><li v-for="(p,i) in meeting.pre_brief.expected_pain_points" :key="i">{{ p }}</li></ul>
    </div>
    <div><b>추천 서비스:</b> {{ meeting.pre_brief.recommended_service || '-' }}</div>
    <div><b>미팅 시 확인할 질문:</b>
      <ul><li v-for="(q,i) in meeting.pre_brief.suggested_questions" :key="i">{{ q }}</li></ul>
    </div>
    <div style="color:var(--accent);"><b>추천 방향:</b> {{ meeting.pre_brief.recommended_direction }}</div>

    <button class="btn" @click="goNotes">미팅 완료 → 메모 입력하기</button>
  </div>
</template>
