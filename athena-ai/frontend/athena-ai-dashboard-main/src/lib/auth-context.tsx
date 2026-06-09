import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, tokenStore } from "./api";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = tokenStore.getAccess();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then((u) => setUser(u))
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    await api.healthCheck();
    const res = await api.login({ email, password });
    tokenStore.set(res.access_token, res.refresh_token);
    setUser(res.user);
  };

  const register = async (name: string, email: string, password: string) => {
    await api.healthCheck();
    const res = await api.register({ name, email, password });
    if (res.access_token) tokenStore.set(res.access_token, res.refresh_token);
    if (res.user) setUser(res.user);
  };

  const logout = async () => {
    const refresh = tokenStore.getRefresh();
    try {
      if (refresh) await api.logout(refresh);
    } catch {
      // Local logout should still succeed if the backend session is already gone.
    }
    tokenStore.clear();
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const u = await api.me();
      setUser(u);
    } catch {
      tokenStore.clear();
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
