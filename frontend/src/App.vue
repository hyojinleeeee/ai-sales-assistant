<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "./stores/authStore";

const auth = useAuthStore();
const route = useRoute();
const showNav = computed(() => auth.isAuthenticated && route.name !== "login");

const adminLinks = [
  { to: "/admin", label: "대시보드" },
  { to: "/admin/reps", label: "조직원 관리" },
  { to: "/admin/accounts", label: "고객사 관리" },
  { to: "/admin/opportunities", label: "영업기회" },
  { to: "/admin/risk", label: "위험도 관리" },
  { to: "/admin/pipeline", label: "영업현황" },
];
const salesLinks = [
  { to: "/sales", label: "대시보드" },
  { to: "/sales/accounts", label: "담당 고객사" },
  { to: "/sales/opportunities", label: "영업기회" },
  { to: "/sales/risk", label: "위험도" },
  { to: "/sales/proposals", label: "제안서" },
];

function doLogout() {
  auth.logout();
  window.location.href = "/login";
}
</script>

<template>
  <div class="shell">
    <header v-if="showNav" class="topbar">
      <div class="brand"><span class="brand-dot"></span>AI Sales Assistant</div>
      <nav>
        <router-link v-for="l in auth.isAdmin ? adminLinks : salesLinks" :key="l.to" :to="l.to">{{ l.label }}</router-link>
      </nav>
      <div class="who">
        <span class="who-name">{{ auth.user?.display_name }}</span>
        <span class="who-role">{{ auth.isAdmin ? '관리자' : '조직원' }}</span>
        <button @click="doLogout">로그아웃</button>
      </div>
    </header>
    <main class="content" :class="{ 'content--bare': !showNav }">
      <router-view />
    </main>
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');

/*
  이트너스 ESRM(esrm.etners.com) 톤앤매너 참고:
  - 서체: Noto Sans KR
  - 카드: 테두리 없이 아주 옅고 넓게 퍼지는 무채색 그림자만으로 구분 (딱딱한 테두리 지양)
  - 라운드를 크게(피pill 버튼/뱃지, 넉넉한 radius)
  - 포인트는 오렌지~코랄 그라데이션의 동그란 배지로 표현
*/
:root {
  --accent: #ff6d2d;
  --accent-2: #fe5f40;
  --accent-dark: #db521a;
  --accent-soft: #fff1e8;
  --accent-soft-line: #ffd2bb;
  --accent-gradient: linear-gradient(135deg, #ff6d2d, #fe5f40);
  --ink: #333132;
  --ink-muted: #8a8d93;
  --line: #ececec;
  --surface: #ffffff;
  --bg: #faf9f7;
  --shadow: 0 0 24px rgba(60, 50, 40, 0.07);
  --shadow-sm: 0 0 14px rgba(60, 50, 40, 0.06);
}

* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Noto Sans KR", "Segoe UI", "Malgun Gothic", sans-serif;
  background: var(--bg);
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
}
h1, h2, h3 { letter-spacing: -.01em; }
h2 { font-size: 21px; font-weight: 700; margin: 0 0 18px; }

.shell { min-height: 100vh; }

.topbar {
  display: flex; align-items: center; gap: 28px;
  background: var(--surface); color: var(--ink);
  padding: 0 28px; height: 60px;
  box-shadow: var(--shadow-sm);
  position: sticky; top: 0; z-index: 10;
}
.brand { display: flex; align-items: center; gap: 9px; font-weight: 900; font-size: 16px; white-space: nowrap; color: var(--ink); }
.brand-dot {
  width: 11px; height: 11px; border-radius: 50%;
  background: var(--accent-gradient); display: inline-block;
}
.topbar nav { display: flex; gap: 2px; flex: 1; flex-wrap: wrap; height: 100%; }
.topbar nav a {
  color: var(--ink-muted); text-decoration: none; font-size: 13.5px; font-weight: 500;
  display: flex; align-items: center; height: 100%; padding: 0 14px;
  border-bottom: 3px solid transparent; transition: color .12s;
}
.topbar nav a:hover { color: var(--ink); }
.topbar nav a.router-link-active { color: var(--accent-dark); font-weight: 700; border-bottom-color: var(--accent); }
.who { display: flex; align-items: center; gap: 10px; font-size: 13px; white-space: nowrap; }
.who-name { font-weight: 600; }
.who-role {
  font-size: 11px; font-weight: 700; color: #fff;
  background: var(--accent-gradient); border-radius: 999px; padding: 3px 11px;
}
.who button {
  background: #f4f3f1; color: var(--ink-muted); border: none;
  border-radius: 999px; padding: 7px 14px; cursor: pointer; font-size: 12.5px; transition: background .12s;
}
.who button:hover { background: #ebe9e6; color: var(--ink); }

.content { padding: 32px; max-width: 1180px; margin: 0 auto; }
.content--bare { padding: 0; max-width: none; }

.card {
  background: var(--surface); border-radius: 18px;
  padding: 22px 24px; box-shadow: var(--shadow);
}
.grid { display: grid; gap: 14px; }

.kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-bottom: 26px; }
.kpi-tile {
  background: var(--surface); border-radius: 16px;
  padding: 18px 20px; box-shadow: var(--shadow); position: relative; overflow: hidden;
}
.kpi-tile::before {
  content: ""; position: absolute; right: 14px; top: 16px; width: 10px; height: 10px;
  border-radius: 50%; background: var(--accent-gradient);
}
.kpi-tile .num { font-size: 28px; font-weight: 900; color: var(--ink); font-variant-numeric: tabular-nums; }
.kpi-tile .label { font-size: 12.5px; color: var(--ink-muted); margin-top: 5px; }

table.simple {
  width: 100%; border-collapse: collapse; background: var(--surface);
  border-radius: 16px; overflow: hidden; box-shadow: var(--shadow);
}
table.simple th, table.simple td { text-align: left; padding: 12px 16px; border-bottom: 1px solid var(--line); font-size: 13.5px; }
table.simple th {
  background: #fdfaf7; color: var(--ink-muted); font-weight: 700;
  font-size: 11.5px; text-transform: uppercase; letter-spacing: .04em;
}
table.simple tr:last-child td { border-bottom: none; }
table.simple tbody tr:hover td { background: var(--accent-soft); }

.badge { display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.badge.정상 { background: #e5f5ec; color: #1f8a4c; }
.badge.관심 { background: var(--accent-soft); color: var(--accent-dark); }
.badge.주의 { background: #fde3cf; color: #b3540d; }
.badge.위험 { background: #fde2e2; color: #c53030; }

.btn {
  border: none; border-radius: 999px; padding: 9px 20px; font-size: 13.5px;
  font-weight: 700; cursor: pointer; background: var(--accent-gradient); color: #fff;
  box-shadow: 0 6px 16px -6px rgba(255, 109, 45, 0.55); transition: transform .1s, box-shadow .1s;
}
.btn:hover { transform: translateY(-1px); box-shadow: 0 8px 20px -6px rgba(255, 109, 45, 0.6); }
.btn:disabled { opacity: .55; cursor: not-allowed; transform: none; box-shadow: none; }
.btn.secondary { background: #f4f3f1; color: var(--ink); box-shadow: none; }
.btn.secondary:hover { background: #ebe9e6; transform: none; box-shadow: none; }
.btn.small { padding: 6px 14px; font-size: 12px; }

input, select, textarea {
  border: 1px solid var(--line); border-radius: 12px; padding: 9px 13px;
  font-size: 13.5px; font-family: inherit; background: var(--surface); color: var(--ink);
}
input:focus, select:focus, textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }

.section-title { font-size: 16px; font-weight: 700; margin: 32px 0 12px; color: var(--ink); }
.muted { color: var(--ink-muted); font-size: 13px; }
.stack { display: flex; flex-direction: column; gap: 12px; }
.row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
</style>
