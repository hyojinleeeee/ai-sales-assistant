<script setup>
import { computed, onMounted, ref } from "vue";
import http, { unwrap } from "../../api";

const reps = ref([]);
const accounts = ref([]);
const assigningFor = ref(null);
const pickedAccounts = ref([]);
const accountSearch = ref("");
const search = ref("");

const filters = ref({ team: "전체", position: "전체", status: "전체" });

async function load() {
  reps.value = await unwrap(http.get("/users"));
  accounts.value = await unwrap(http.get("/accounts"));
}
onMounted(load);

const teams = computed(() => ["전체", ...new Set(reps.value.map((r) => r.team).filter(Boolean))].sort());
const positions = computed(() => ["전체", ...new Set(reps.value.map((r) => r.position).filter(Boolean))].sort());

const filteredReps = computed(() => {
  const f = filters.value;
  return reps.value.filter((r) => {
    if (search.value && !r.display_name.includes(search.value) && !r.sls_code.includes(search.value)) return false;
    if (f.team !== "전체" && r.team !== f.team) return false;
    if (f.position !== "전체" && r.position !== f.position) return false;
    if (f.status !== "전체" && (f.status === "활성") !== r.is_active) return false;
    return true;
  });
});

function resetFilters() {
  filters.value = { team: "전체", position: "전체", status: "전체" };
  search.value = "";
}

const filteredAccounts = computed(() => {
  const q = accountSearch.value.trim();
  if (!q) return accounts.value;
  return accounts.value.filter((a) => a.name.includes(q) || a.code.includes(q));
});

function openAssign(rep) {
  assigningFor.value = rep;
  accountSearch.value = "";
  pickedAccounts.value = accounts.value.filter((a) => a.rep_sls_code === rep.sls_code).map((a) => a.code);
}

async function saveAssign() {
  await unwrap(http.put(`/users/${assigningFor.value.id}/assignments`, { account_codes: pickedAccounts.value }));
  assigningFor.value = null;
  await load();
}

async function deactivate(rep) {
  if (!confirm(`${rep.display_name}님을 비활성화할까요?`)) return;
  await unwrap(http.put(`/users/${rep.id}/deactivate`));
  await load();
}
</script>

<template>
  <h2>조직원 관리</h2>

  <div class="row" style="margin-bottom:10px;">
    <input v-model="search" placeholder="이름/사번 검색" style="width:220px;" />
  </div>

  <div class="card row" style="margin-bottom:16px;gap:16px;">
    <div class="stack" style="gap:4px;">
      <label class="muted" style="font-size:12px;">팀</label>
      <select v-model="filters.team">
        <option v-for="v in teams" :key="v" :value="v">{{ v }}</option>
      </select>
    </div>
    <div class="stack" style="gap:4px;">
      <label class="muted" style="font-size:12px;">직급</label>
      <select v-model="filters.position">
        <option v-for="v in positions" :key="v" :value="v">{{ v }}</option>
      </select>
    </div>
    <div class="stack" style="gap:4px;">
      <label class="muted" style="font-size:12px;">상태</label>
      <select v-model="filters.status">
        <option value="전체">전체</option>
        <option value="활성">활성</option>
        <option value="비활성">비활성</option>
      </select>
    </div>
    <button class="btn secondary small" style="align-self:flex-end;" @click="resetFilters">필터 초기화</button>
  </div>

  <div class="muted" style="margin-bottom:8px;">{{ filteredReps.length }}명 (전체 {{ reps.length }}명 중)</div>

  <table class="simple">
    <thead><tr><th>이름</th><th>팀</th><th>직급</th><th>담당 고객사 수</th><th>상태</th><th></th></tr></thead>
    <tbody>
      <tr v-for="r in filteredReps" :key="r.id">
        <td>{{ r.display_name }} ({{ r.sls_code }})</td>
        <td>{{ r.team }}</td>
        <td>{{ r.position }}</td>
        <td>{{ r.account_count }}</td>
        <td>{{ r.is_active ? '활성' : '비활성' }}</td>
        <td class="row">
          <button class="btn small secondary" @click="openAssign(r)">담당 배정</button>
          <button class="btn small secondary" @click="deactivate(r)" v-if="r.is_active">비활성화</button>
        </td>
      </tr>
    </tbody>
  </table>
  <div class="muted" v-if="!filteredReps.length" style="margin-top:10px;">조건에 맞는 조직원이 없습니다.</div>

  <div v-if="assigningFor" style="position:fixed;inset:0;background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;">
    <div class="card" style="width:480px;max-height:70vh;overflow:auto;">
      <h3>{{ assigningFor.display_name }} 담당 고객사 배정</h3>
      <input v-model="accountSearch" placeholder="고객사명/코드 검색" style="width:100%;margin-bottom:10px;" />
      <div class="muted" style="margin-bottom:6px;">{{ pickedAccounts.length }}개 선택됨 · 검색결과 {{ filteredAccounts.length }}개</div>
      <div class="stack">
        <label v-for="a in filteredAccounts" :key="a.code" style="display:flex;gap:8px;align-items:center;font-size:13.5px;">
          <input type="checkbox" :value="a.code" v-model="pickedAccounts" />
          {{ a.name }} ({{ a.code }}) <span class="muted">— 현재: {{ a.rep_sls_code }}</span>
        </label>
        <div class="muted" v-if="!filteredAccounts.length">검색 결과가 없습니다.</div>
      </div>
      <div class="row" style="margin-top:16px;justify-content:flex-end;">
        <button class="btn secondary" @click="assigningFor=null">취소</button>
        <button class="btn" @click="saveAssign">저장</button>
      </div>
    </div>
  </div>
</template>
