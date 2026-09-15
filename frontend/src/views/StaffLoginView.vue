<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/authStore";

const auth = useAuthStore();
const router = useRouter();
const username = ref("");
const password = ref("");
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
  <div class="staff-login">
    <div class="staff-login-panel">
      <div class="staff-login-badge"></div>
      <h1>오늘도 좋은 영업 되세요 👋</h1>
      <p>담당 고객사 현황과 AI 브리핑이 준비되어 있어요.<br>로그인하고 오늘의 업무를 확인하세요.</p>
    </div>

    <div class="staff-login-card">
      <div class="card stack">
        <h2 style="margin:0;">조직원 로그인</h2>
        <p class="muted">사번(SLS 코드)으로 로그인하세요.</p>
        <div v-if="error" style="background:#fde3e3;color:#c0392b;padding:8px 12px;border-radius:8px;font-size:13px;">{{ error }}</div>
        <form class="stack" @submit.prevent="submit">
          <label class="muted">아이디</label>
          <input v-model="username" placeholder="예: sls001" autofocus />
          <label class="muted">비밀번호</label>
          <input v-model="password" type="password" />
          <button class="btn" type="submit" :disabled="loading">{{ loading ? '로그인 중...' : '로그인' }}</button>
        </form>
        <p class="muted" style="font-size:12px;">데모 계정: sls001 ~ sls040 / 1234</p>
        <p class="muted" style="font-size:12.5px;text-align:center;">관리자이신가요? <router-link to="/login" style="color:var(--accent-dark);font-weight:600;">관리자 로그인</router-link></p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.staff-login {
  min-height: 100vh;
  display: flex;
  align-items: stretch;
}
.staff-login-panel {
  flex: 1.1;
  background: var(--accent-gradient);
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 60px 64px;
  position: relative;
  overflow: hidden;
}
.staff-login-badge {
  width: 56px; height: 56px; border-radius: 18px;
  background: rgba(255,255,255,.22);
  margin-bottom: 28px;
}
.staff-login-panel h1 {
  font-size: 30px; font-weight: 900; line-height: 1.35; margin: 0 0 16px; max-width: 420px;
}
.staff-login-panel p {
  font-size: 14.5px; line-height: 1.7; opacity: .92; max-width: 380px;
}
.staff-login-card {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  padding: 40px 24px;
}
.staff-login-card .card { width: 100%; max-width: 340px; }

@media (max-width: 760px) {
  .staff-login { flex-direction: column; }
  .staff-login-panel { padding: 40px 28px; }
  .staff-login-panel h1 { font-size: 24px; }
}
</style>
