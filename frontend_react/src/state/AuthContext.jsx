import { createContext, useContext, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import {
  api,
  attachAuthToken,
  clearAuthStorage,
  loadAuthTokenFromStorage,
  persistAuthSession
} from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("authToken") || "");
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem("refreshToken") || "");
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("authUser");
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (!token) {
      loadAuthTokenFromStorage();
      return;
    }
    attachAuthToken(token);
  }, [token]);

  useEffect(() => {
    const onStorage = () => {
      const nextToken = localStorage.getItem("authToken") || "";
      const nextRefreshToken = localStorage.getItem("refreshToken") || "";
      const rawUser = localStorage.getItem("authUser");
      let nextUser = null;
      if (rawUser) {
        try {
          nextUser = JSON.parse(rawUser);
        } catch {
          nextUser = null;
        }
      }

      setToken(nextToken);
      setRefreshToken(nextRefreshToken);
      setUser(nextUser);
    };

    const onAuthExpired = () => {
      setToken("");
      setRefreshToken("");
      setUser(null);
      toast.error("Session expired. Please sign in again.");
    };

    window.addEventListener("storage", onStorage);
    window.addEventListener("auth:expired", onAuthExpired);

    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("auth:expired", onAuthExpired);
    };
  }, []);

  const login = async (email, password) => {
    const normalizedEmail = email.trim().toLowerCase();
    const { data } = await api.post("/auth/login", { email: normalizedEmail, password });
    setToken(data.access_token);
    setRefreshToken(data.refresh_token);
    setUser(data.user);
    persistAuthSession(data.access_token, data.refresh_token, data.user);
    toast.success("Welcome back");
  };

  const signup = async (name, email, password) => {
    const normalizedEmail = email.trim().toLowerCase();
    const { data } = await api.post("/auth/signup", { name, email: normalizedEmail, password });
    setToken(data.access_token);
    setRefreshToken(data.refresh_token);
    setUser(data.user);
    persistAuthSession(data.access_token, data.refresh_token, data.user);
    toast.success("Account created successfully");
  };

  const logout = async () => {
    try {
      if (token && refreshToken) {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      }
    } catch {
      // Local logout should still succeed.
    }
    setToken("");
    setRefreshToken("");
    setUser(null);
    clearAuthStorage();
    toast.success("Logged out");
  };

  const value = useMemo(
    () => ({ token, refreshToken, user, login, signup, logout }),
    [token, refreshToken, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
