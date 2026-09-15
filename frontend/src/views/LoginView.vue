<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/authStore";

const auth = useAuthStore();
const router = useRouter();
const username = ref("admin");
const password = ref("1234");
const error = ref("");
const loading = ref(false);

async function submit() {
  error.value = "";
  loading.value = true;
  try {
    const user = await auth.login(username.value, password.value);
    router.push(user.role === "admin" ? "/admin" : "/sales");
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div style="max-width:380px;margin:80px auto 0;">
    <div class="card stack">
      <h2 style="margin:0;">E:PACE</h2>
      <p class="muted">넥스트라인 영업 지원 시스템에 로그인하세요.</p>
      <div v-if="error" style="background:#fde3e3;color:#c0392b;padding:8px 12px;border-radius:8px;font-size:13px;">{{ error }}</div>
      <form class="stack" @submit.prevent="submit">
        <label class="muted">아이디</label>
        <input v-model="username" placeholder="예: admin, sls001" />
        <label class="muted">비밀번호</label>
        <input v-model="password" type="password" />
        <button class="btn" type="submit" :disabled="loading">{{ loading ? '로그인 중...' : '로그인' }}</button>
      </form>
      <p class="muted" style="font-size:12px;">데모 계정: admin / 1234 (관리자), sls001~sls040 / 1234 (조직원)</p>
    </div>
  </div>
</template>
