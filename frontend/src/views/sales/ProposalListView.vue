<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { cachedGet, unwrap } from "../../api";
import { useAuthStore } from "../../stores/authStore";

const router = useRouter();
const auth = useAuthStore();
const proposals = ref([]);

onMounted(async () => {
  proposals.value = await unwrap(cachedGet("/proposals"));
});

function open(id) {
  router.push({ name: auth.isAdmin ? "admin-proposal-edit" : "proposal-edit", params: { id } });
}
</script>

<template>
  <h2>제안서 목록</h2>
  <table class="simple" v-if="proposals.length">
    <thead><tr><th>고객사</th><th>추천 서비스</th><th>상태</th><th>수정일</th></tr></thead>
    <tbody>
      <tr v-for="p in proposals" :key="p.id" style="cursor:pointer;" @click="open(p.id)">
        <td>{{ p.account_code }}</td>
        <td>{{ p.recommended_service }}</td>
        <td>{{ p.status }}</td>
        <td>{{ (p.updated_at || '').slice(0, 10) }}</td>
      </tr>
    </tbody>
  </table>
  <div class="muted" v-else>아직 작성된 제안서가 없습니다. 고객사 상세 화면에서 생성해보세요.</div>
</template>
