<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import http, { unwrap } from "../../api";
import { useAuthStore } from "../../stores/authStore";

const props = defineProps({ code: String });
const router = useRouter();
const auth = useAuthStore();
const account = ref(null);

async function load() {
  account.value = await unwrap(http.get(`/accounts/${props.code}`));
}
onMounted(load);

function fmt(n) {
  return n ? Math.round(n).toLocaleString() : "-";
}

function goBrief() {
  router.push({ name: "meeting-brief", params: { code: props.code } });
}
function goProposal() {
  router.push({ name: "proposal-new", params: { code: props.code } });
}
</script>

<template>
  <div v-if="account" class="stack">
    <div class="row" style="justify-content:space-between;">
      <h2 style="margin:0;">{{ account.name }} <span class="muted" style="font-size:14px;">({{ account.code }})</span></h2>
      <div class="row" v-if="!auth.isAdmin">
        <button class="btn secondary" @click="goBrief">미팅 브리핑 생성</button>
        <button class="btn" @click="goProposal">제안서 초안 생성</button>
      </div>
    </div>

    <div class="card">
      <div class="section-title" style="margin-top:0;">고객 기본정보</div>
      <div class="grid" style="grid-template-columns:repeat(4,1fr);font-size:13.5px;">
        <div><b>업종</b><br>{{ account.industry }}</div>
        <div><b>지역</b><br>{{ account.region }}</div>
        <div><b>규모</b><br>{{ account.contract_size_tier }}</div>
        <div><b>신용등급</b><br>{{ account.credit_grade }}</div>
        <div><b>담당자</b><br>{{ account.rep_sls_code }}</div>
        <div><b>담당자 연락처</b><br>{{ account.main_contact_phone || '-' }}</div>
        <div><b>계약기간</b><br>{{ account.contract_start_date }} ~ {{ account.contract_end_date }}</div>
        <div><b>연간매출</b><br>{{ fmt(account.annual_revenue) }}원</div>
      </div>
    </div>

    <div class="card">
      <div class="section-title" style="margin-top:0;">서비스 이용 현황</div>
      <table class="simple">
        <thead><tr><th>품목</th><th>카테고리</th><th>거래횟수</th><th>최근거래일</th></tr></thead>
        <tbody>
          <tr v-for="s in account.services" :key="s.service_name">
            <td>{{ s.service_name }}</td><td>{{ s.category }}</td><td>{{ s.txn_count }}</td><td>{{ s.last_txn_date }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <div class="section-title" style="margin-top:0;">AI 영업기회 (참고용)</div>
      <div v-if="account.opportunity">
        <div><b>영업기회 점수:</b> {{ account.opportunity.opportunity_score }} / 100</div>
        <div><b>추천 서비스:</b> {{ account.opportunity.recommended_service }}</div>
        <div class="muted">{{ account.opportunity.ai_rationale }}</div>
        <div style="color:var(--accent);">▶ {{ account.opportunity.recommended_action }}</div>
      </div>
    </div>

    <div class="card">
      <div class="section-title" style="margin-top:0;">AI 고객 위험도 (참고용)</div>
      <div v-if="account.risk">
        <span class="badge" :class="account.risk.risk_tier">{{ account.risk.risk_tier }}</span>
        <ul>
          <li v-for="(f,i) in account.risk.ai_findings" :key="i">{{ f }}</li>
        </ul>
        <div style="color:var(--accent);">▶ {{ account.risk.recommended_action }}</div>
      </div>
    </div>

    <div class="card">
      <div class="section-title" style="margin-top:0;">최근 거래/상담 내역</div>
      <table class="simple">
        <thead><tr><th>일자</th><th>구분</th><th>내용</th><th>금액/태그</th></tr></thead>
        <tbody>
          <tr v-for="(t,i) in account.recent_transactions.slice(0,5)" :key="'t'+i">
            <td>{{ t.txn_date }}</td><td>거래</td><td>{{ t.item_name }}</td><td>{{ fmt(t.amount) }}원</td>
          </tr>
          <tr v-for="(q,i) in account.inquiries.slice(0,5)" :key="'q'+i">
            <td>{{ q.inquiry_date }}</td><td>상담</td><td>{{ q.type_major }}</td><td>{{ q.voc_tag }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <div class="section-title" style="margin-top:0;">Next Action</div>
      <div>현재 영업단계: <b>{{ account.current_stage }}</b></div>
    </div>
  </div>
  <div v-else class="muted">불러오는 중...</div>
</template>
