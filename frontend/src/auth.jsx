import { createContext, useContext, useState } from "react";
import api, { AUTH_STORAGE_KEY } from "./api.js";

const AuthContext = createContext(null);

function readAuth() {
  try {
    const raw = sessionStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(readAuth);

  // Persist synchronously so the axios request interceptor always sees the
  // current token (no dependency on React effect ordering).
  const login = (data) => {
    const value = { token: data.token, user: data.user };
    sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(value));
    setAuth(value);
  };

  const logout = async () => {
    try {
      await api.post("/api/auth/logout");
    } catch {
      /* ignore */
    }
    sessionStorage.removeItem(AUTH_STORAGE_KEY);
    setAuth(null);
  };

  return (
    <AuthContext.Provider
      value={{
        token: auth?.token || null,
        user: auth?.user || null,
        role: auth?.user?.role || null,
        isAuthed: !!auth?.token,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
