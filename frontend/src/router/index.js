import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "../stores/authStore";

import LoginView from "../views/LoginView.vue";

import AdminDashboardView from "../views/admin/AdminDashboardView.vue";
import RepManageView from "../views/admin/RepManageView.vue";
import AccountListView from "../views/admin/AccountListView.vue";
import PipelineMonitorView from "../views/admin/PipelineMonitorView.vue";

import SalesDashboardView from "../views/sales/SalesDashboardView.vue";
import MyAccountsView from "../views/sales/MyAccountsView.vue";
import MeetingBriefView from "../views/sales/MeetingBriefView.vue";
import MeetingNotesView from "../views/sales/MeetingNotesView.vue";
import ProposalDraftView from "../views/sales/ProposalDraftView.vue";
import ProposalListView from "../views/sales/ProposalListView.vue";

import AccountDetailView from "../views/shared/AccountDetailView.vue";
import OpportunityListView from "../views/shared/OpportunityListView.vue";
import RiskListView from "../views/shared/RiskListView.vue";

const routes = [
  { path: "/", redirect: "/login" },
  { path: "/login", name: "login", component: LoginView, meta: { public: true } },

  { path: "/admin", name: "admin-dashboard", component: AdminDashboardView, meta: { role: "admin" } },
  { path: "/admin/reps", name: "admin-reps", component: RepManageView, meta: { role: "admin" } },
  { path: "/admin/accounts", name: "admin-accounts", component: AccountListView, meta: { role: "admin" } },
  { path: "/admin/accounts/:code", name: "admin-account-detail", component: AccountDetailView, meta: { role: "admin" }, props: true },
  { path: "/admin/opportunities", name: "admin-opportunities", component: OpportunityListView, meta: { role: "admin" } },
  { path: "/admin/risk", name: "admin-risk", component: RiskListView, meta: { role: "admin" } },
  { path: "/admin/pipeline", name: "admin-pipeline", component: PipelineMonitorView, meta: { role: "admin" } },

  { path: "/sales", name: "sales-dashboard", component: SalesDashboardView, meta: { role: "sales" } },
  { path: "/sales/accounts", name: "sales-accounts", component: MyAccountsView, meta: { role: "sales" } },
  { path: "/sales/accounts/:code", name: "sales-account-detail", component: AccountDetailView, meta: { role: "sales" }, props: true },
  { path: "/sales/opportunities", name: "sales-opportunities", component: OpportunityListView, meta: { role: "sales" } },
  { path: "/sales/risk", name: "sales-risk", component: RiskListView, meta: { role: "sales" } },
  { path: "/sales/meetings/:code/brief", name: "meeting-brief", component: MeetingBriefView, meta: { role: "sales" }, props: true },
  { path: "/sales/meetings/:id/notes", name: "meeting-notes", component: MeetingNotesView, meta: { role: "sales" }, props: true },
  { path: "/sales/proposals", name: "sales-proposals", component: ProposalListView, meta: { role: "sales" } },
  { path: "/sales/proposals/:code/new", name: "proposal-new", component: ProposalDraftView, meta: { role: "sales" }, props: true },
  { path: "/sales/proposals/edit/:id", name: "proposal-edit", component: ProposalDraftView, meta: { role: "sales" }, props: true },

  // 존재하지 않는 경로로 들어오면 로그인 화면으로 보낸다 (인증 상태면 beforeEach가 대시보드로 다시 보냄).
  { path: "/:pathMatch(.*)*", redirect: "/login" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.meta.public) {
    if (to.name === "login" && auth.isAuthenticated) {
      return auth.isAdmin ? { name: "admin-dashboard" } : { name: "sales-dashboard" };
    }
    return true;
  }
  if (!auth.isAuthenticated) {
    return { name: "login" };
  }
  if (to.meta.role === "admin" && !auth.isAdmin) {
    return { name: "sales-dashboard" };
  }
  if (to.meta.role === "sales" && auth.isAdmin) {
    return { name: "admin-dashboard" };
  }
  return true;
});

export default router;
