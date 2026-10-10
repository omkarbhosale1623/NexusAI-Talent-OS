// src/hooks/useAuth.ts
"use client";
import { createContext, useContext, useEffect, useState, useCallback, createElement, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, setToken, clearToken, getToken } from "@/lib/api";

interface AuthUser {
  id: string;
  org_id: string;
  email: string;
  full_name: string;
  role: string;
  plan: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (body: { email: string; password: string; full_name: string; company_name: string }) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = getToken();
    if (!token) { setLoading(false); return; }
    api.me()
      .then((data) => setUser(data))
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.login({ email, password });
    setToken(data.token);
    document.cookie = `nexusai_token=${data.token}; path=/; max-age=${60 * 60 * 72}`;
    setUser(data);
  }, []);

  const signup = useCallback(async (body: any) => {
    const data = await api.signup(body);
    setToken(data.token);
    document.cookie = `nexusai_token=${data.token}; path=/; max-age=${60 * 60 * 72}`;
    setUser(data);
  }, []);

  const logout = useCallback(async () => {
    await api.signout().catch(() => {});
    clearToken();
    document.cookie = "nexusai_token=; path=/; max-age=0";
    setUser(null);
    router.push("/login");
  }, [router]);

  return createElement(
    AuthContext.Provider,
    { value: { user, loading, login, signup, logout } },
    children
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
