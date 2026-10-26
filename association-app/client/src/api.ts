export class ApiError extends Error {}

export async function api<T = any>(method: string, path: string, body?: unknown): Promise<T> {
  const r = await fetch(path, { method, headers: body ? { 'content-type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(data.error || 'Something went wrong. Try again.');
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
