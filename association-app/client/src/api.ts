export class ApiError extends Error {}

// API_BASE is the Supabase edge function (https://<project>.supabase.co/functions/v1/industrynurses).
// Sign-in codes are checked by Supabase Auth directly; the app keeps the access and refresh tokens.
export const API_BASE: string = (import.meta as any).env?.VITE_API_BASE || '';
const AUTH_BASE: string = (import.meta as any).env?.VITE_AUTH_BASE || '';
const AUTH_KEY: string = (import.meta as any).env?.VITE_AUTH_KEY || '';
const TOKEN_KEY = 'ain-session';
interface Tokens { access_token: string; refresh_token: string }
const store = {
  get: (): Tokens | null => { try { return JSON.parse(localStorage.getItem(TOKEN_KEY) || 'null'); } catch { return null; } },
  set: (v: Tokens | null) => { try { v ? localStorage.setItem(TOKEN_KEY, JSON.stringify(v)) : localStorage.removeItem(TOKEN_KEY); } catch { /* private mode */ } },
};

async function authCall(path: string, body: unknown): Promise<any> {
  const r = await fetch(`${AUTH_BASE}/auth/v1${path}`, { method: 'POST', headers: { apikey: AUTH_KEY, 'content-type': 'application/json' }, body: JSON.stringify(body) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok || !data.access_token) throw new ApiError('That code or password did not work, or it has expired. Request a new one.');
  store.set({ access_token: data.access_token, refresh_token: data.refresh_token });
  return data;
}
/** Sign in with the emailed 6-digit code, or (App Store reviewers) email and password. */
export const verifyCode = (email: string, code: string) => authCall('/verify', { type: 'email', email, token: code });
export const signInWithPassword = (email: string, password: string) => authCall('/token?grant_type=password', { email, password });

async function refresh(): Promise<boolean> {
  const t = store.get();
  if (!t?.refresh_token) return false;
  try { await authCall('/token?grant_type=refresh_token', { refresh_token: t.refresh_token }); return true; } catch { store.set(null); return false; }
}

export async function api<T = any>(method: string, path: string, body?: unknown, retried = false): Promise<T> {
  const headers: Record<string, string> = {};
  if (body) headers['content-type'] = 'application/json';
  const token = store.get()?.access_token;
  if (token) headers.authorization = `Bearer ${token}`;
  const r = await fetch(API_BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (r.status === 401 && token && !retried && await refresh()) return api<T>(method, path, body, true);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(data.error || 'Something went wrong. Try again.');
  if (path === '/api/auth/logout' || (method === 'DELETE' && path === '/api/me')) store.set(null);
  return data as T;
}

export interface Member {
  id: string; name: string; email: string; role_category: string; employer_type: string; speciality: string; region: string;
  directory_visible: boolean; mentoring: string; email_notifications: boolean; status: string; is_admin: boolean;
}
export interface EventItem {
  id: number; title: string; organiser: string; detail: string; start_date: string | null; end_date: string | null; venue: string | null;
  source_url: string; source_label: string; group_label: string; members_only: boolean; verified_at: string; saved: boolean;
}
