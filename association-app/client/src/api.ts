export class ApiError extends Error {}

// The phone apps are built with VITE_API_BASE set to the hosted address; the website uses same-origin calls and a cookie.
export const API_BASE: string = (import.meta as any).env?.VITE_API_BASE || '';
const TOKEN_KEY = 'ain-session';
const store = {
  get: () => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } },
  set: (v: string | null) => { try { v ? localStorage.setItem(TOKEN_KEY, v) : localStorage.removeItem(TOKEN_KEY); } catch { /* private mode */ } },
};

export async function api<T = any>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body) headers['content-type'] = 'application/json';
  const token = API_BASE ? store.get() : null;
  if (token) headers.authorization = `Bearer ${token}`;
  const r = await fetch(API_BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(data.error || 'Something went wrong. Try again.');
  if (API_BASE && path === '/api/auth/verify' && data.session) store.set(data.session);
  if (API_BASE && path === '/api/auth/logout') store.set(null);
  if (API_BASE && method === 'DELETE' && path === '/api/me') store.set(null);
  return data as T;
}

export interface Member {
  id: number; name: string; email: string; role_category: string; employer_type: string; speciality: string; region: string;
  directory_visible: boolean; mentoring: string; email_notifications: boolean; status: string; is_admin: boolean;
}
export interface EventItem {
  id: number; title: string; organiser: string; detail: string; start_date: string | null; end_date: string | null; venue: string | null;
  source_url: string; source_label: string; group_label: string; members_only: boolean; verified_at: string; saved: boolean;
}
