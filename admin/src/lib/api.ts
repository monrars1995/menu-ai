import { useAuth } from "./auth";

export function useApi() {
  const auth = useAuth();

  async function apiFetch(path: string, options: RequestInit = {}) {
    const headers = new Headers(options.headers || {});
    if (auth.token) {
      headers.set("Authorization", `Bearer ${auth.token}`);
    } else if (auth.apiKey) {
      headers.set("X-Admin-Api-Key", auth.apiKey);
    }
    if (options.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    const res = await fetch(path, { ...options, headers });
    if (res.status === 401) {
      auth.logout();
    }
    return res;
  }

  return { apiFetch };
}
