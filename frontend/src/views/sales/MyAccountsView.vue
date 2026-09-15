<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import http, { unwrap } from "../../api";

const router = useRouter();
const accounts = ref([]);

onMounted(async () => {
  accounts.value = await unwrap(http.get("/accounts"));
});

function open(code) {
  router.push({ name: "sales-account-detail", params: { code } });
}
</script>

<template>
  <h2>담당 고객사</h2>
  <table class="simple">
    <thead><tr><th>고객사</th><th>업종</th><th>영업단계</th><th>위험도</th><th>기회점수</th></tr></thead>
    <tbody>
      <tr v-for="a in accounts" :key="a.code" style="cursor:pointer;" @click="open(a.code)">
        <td>{{ a.name }}</td>
        <td>{{ a.industry }}</td>
        <td>{{ a.current_stage }}</td>
        <td><span class="badge" :class="a.risk_tier">{{ a.risk_tier }}</span></td>
        <td>{{ a.opportunity_score }}</td>
      </tr>
    </tbody>
  </table>
</template>
