import axios from "axios";
import router from "../router";
import { useAuthStore } from "../stores/authStore";

// 로컬 개발: vite.config.js의 /api 프록시를 그대로 사용.
// 배포 환경: 프론트엔드와 백엔드가 서로 다른 Vercel 프로젝트(다른 도메인)이므로
// 빌드 시점에 VITE_API_BASE로 실제 백엔드 주소를 주입한다.
const baseURL = import.meta.env.VITE_API_BASE || "/api";
const http = axios.create({ baseURL });

http.interceptors.request.use((config) => {
  const auth = useAuthStore();
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`;
  }
  return config;
});

http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      const auth = useAuthStore();
      auth.logout();
      router.push("/login");
    }
    return Promise.reject(err);
  }
);

function errorMessage(err) {
  if (err.response && err.response.data) {
    return err.response.data.error_message || err.response.data.detail || "요청 중 오류가 발생했습니다.";
  }
  return err.message || "요청 중 오류가 발생했습니다.";
}

export async function unwrap(promise) {
  let res;
  try {
    res = await promise;
  } catch (err) {
    throw new Error(errorMessage(err));
  }
  if (!res.data.success) {
    throw new Error(res.data.error_message || "알 수 없는 오류");
  }
  return res.data.data;
}

export default http;
