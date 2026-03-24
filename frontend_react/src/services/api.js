import axios from "axios";

const runtimeApiBase =
  typeof window !== "undefined" && window.SOCIALSPHERE_API_BASE
    ? String(window.SOCIALSPHERE_API_BASE)
    : "";

const defaultApiBase = (() => {
  if (typeof window === "undefined") return "/api";
  const { hostname, port } = window.location;
  const isLocalViteDev = (hostname === "localhost" || hostname === "127.0.0.1") && port === "5173";
  return isLocalViteDev ? "http://127.0.0.1:8000/api" : "/api";
})();

export const API_BASE =
  (import.meta.env.VITE_API_BASE || runtimeApiBase || defaultApiBase).replace(/\/$/, "");

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json"
  }
});

let refreshPromise = null;

export function clearAuthStorage() {
  localStorage.removeItem("authToken");
  localStorage.removeItem("refreshToken");
  localStorage.removeItem("authUser");
  attachAuthToken("");
}

export function persistAuthSession(accessToken, refreshToken, user) {
  if (!accessToken || !refreshToken || !user) return;
  localStorage.setItem("authToken", accessToken);
  localStorage.setItem("refreshToken", refreshToken);
  localStorage.setItem("authUser", JSON.stringify(user));
  attachAuthToken(accessToken);
}

function notifyAuthExpired() {
  window.dispatchEvent(new CustomEvent("auth:expired"));
}

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise;

  const refreshToken = localStorage.getItem("refreshToken") || "";
  if (!refreshToken) return "";

  refreshPromise = api
    .post("/auth/refresh", { refresh_token: refreshToken })
    .then((response) => {
      const nextAccess = response?.data?.access_token || "";
      const nextRefresh = response?.data?.refresh_token || "";
      if (!nextAccess || !nextRefresh) return "";
      localStorage.setItem("authToken", nextAccess);
      localStorage.setItem("refreshToken", nextRefresh);
      attachAuthToken(nextAccess);
      return nextAccess;
    })
    .catch(() => "")
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status;
    const original = error?.config;
    if (status !== 401 || !original || original.__retry) {
      return Promise.reject(error);
    }

    if (String(original.url || "").includes("/auth/refresh")) {
      return Promise.reject(error);
    }

    original.__retry = true;
    const token = await refreshAccessToken();
    if (!token) {
      clearAuthStorage();
      notifyAuthExpired();
      return Promise.reject(error);
    }

    original.headers = original.headers || {};
    original.headers.Authorization = `Bearer ${token}`;
    return api(original);
  }
);

export function attachAuthToken(token) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
}

export function loadAuthTokenFromStorage() {
  const token = localStorage.getItem("authToken") || "";
  attachAuthToken(token);
  return token;
}
