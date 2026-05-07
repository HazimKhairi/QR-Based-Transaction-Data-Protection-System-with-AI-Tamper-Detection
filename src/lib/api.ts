export const getBackendUrl = () => {
  return process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5000";
};

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: any;
  headers?: Record<string, string>;
};

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const url = `${getBackendUrl()}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(url, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = (data && (data.error || data.message)) || `Request failed: ${res.status}`;
    throw new Error(msg);
  }
  return data as T;
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("access_token");
}

export type AuthUser = {
  id?: number;
  email?: string;
  full_name?: string;
  role?: "resident" | "admin" | "super_admin";
};

export function getCurrentUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function getUserRole(): AuthUser["role"] | null {
  return getCurrentUser()?.role ?? null;
}

export function isAdmin(): boolean {
  const role = getUserRole();
  return role === "admin" || role === "super_admin";
}

export function defaultLandingFor(role: AuthUser["role"] | null | undefined): string {
  if (role === "admin" || role === "super_admin") return "/admin/dashboard";
  if (role === "resident") return "/resident/payment";
  return "/login";
}

export function logout() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    window.location.href = "/login";
  }
}