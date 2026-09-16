<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { cachedGet, unwrap } from "../../api";

const router = useRouter();
const data = ref(null);

onMounted(async () => {
  data.value = await unwrap(cachedGet("/dashboard/sales"));
});

function openAccount(code) {
  router.push({ name: "sales-account-detail", params: { code } });
}
</script>

<template>
  <div v-if="data">
    <h2>오늘의 AI 영업 브리핑</h2>
    <p class="muted">담당 고객사 {{ data.total_accounts }}곳 기준 참고 정보입니다.</p>

    <div class="section-title" style="margin-top:8px;">🔥 신규 영업기회</div>
    <table class="simple" v-if="data.new_opportunities.length">
      <tbody>
        <tr v-for="o in data.new_opportunities" :key="o.account_code" style="cursor:pointer;" @click="openAccount(o.account_code)">
          <td>{{ o.account_name }}</td><td>{{ o.recommended_service }}</td><td>{{ o.opportunity_score }}점</td>
        </tr>
      </tbody>
    </table>
    <div class="muted" v-else>표시할 신규 기회가 없습니다.</div>

    <div class="section-title">📅 오늘의 미팅</div>
    <table class="simple" v-if="data.today_meetings.length">
      <tbody>
        <tr v-for="m in data.today_meetings" :key="m.id">
          <td>{{ m.account_name }}</td><td>{{ m.meeting_date }}</td>
        </tr>
      </tbody>
    </table>
    <div class="muted" v-else>예정된 미팅이 없습니다.</div>

    <div class="section-title">📝 제안 필요</div>
    <table class="simple" v-if="data.proposal_needed.length">
      <tbody>
        <tr v-for="p in data.proposal_needed" :key="p.meeting_id" style="cursor:pointer;" @click="openAccount(p.account_code)">
          <td>{{ p.account_name }}</td><td>미팅 완료 · 제안서 작성 필요</td>
        </tr>
      </tbody>
    </table>
    <div class="muted" v-else>제안서가 필요한 건이 없습니다.</div>

    <div class="section-title">⚠ 관리 필요</div>
    <table class="simple" v-if="data.at_risk_accounts.length">
      <tbody>
        <tr v-for="r in data.at_risk_accounts" :key="r.account_code" style="cursor:pointer;" @click="openAccount(r.account_code)">
          <td>{{ r.account_name }}</td><td><span class="badge" :class="r.risk_tier">{{ r.risk_tier }}</span></td>
        </tr>
      </tbody>
    </table>
    <div class="muted" v-else>위험 신호가 감지된 고객사가 없습니다.</div>
  </div>
</template>
