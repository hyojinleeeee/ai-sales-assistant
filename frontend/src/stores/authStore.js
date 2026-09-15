import { defineStore } from "pinia";
import { computed, ref } from "vue";

import http, { unwrap } from "../api";

export const useAuthStore = defineStore("auth", () => {
  const token = ref(localStorage.getItem("asa_token") || "");
  const user = ref(JSON.parse(localStorage.getItem("asa_user") || "null"));

  const isAuthenticated = computed(() => !!token.value);
  const isAdmin = computed(() => user.value?.role === "admin");

  function setSession(newToken, newUser) {
    token.value = newToken;
    user.value = newUser;
    localStorage.setItem("asa_token", newToken);
    localStorage.setItem("asa_user", JSON.stringify(newUser));
  }

  async function login(username, password) {
    const data = await unwrap(http.post("/auth/login", { username, password }));
    setSession(data.access_token, data.user);
    return data.user;
  }

  function logout() {
    token.value = "";
    user.value = null;
    localStorage.removeItem("asa_token");
    localStorage.removeItem("asa_user");
  }

  return { token, user, isAuthenticated, isAdmin, login, logout, setSession };
});
