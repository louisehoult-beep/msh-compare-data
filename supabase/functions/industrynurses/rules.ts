// Pure rules for the Association app: no database, no network. Tested in rules_test.ts.

export const PIN_RE = /^\d{2}[A-Z]\d{4}[A-Z]$/;
export const ROLES = ["Clinical educator", "Clinical specialist", "Application specialist", "Clinical affairs or regulatory", "Sales or account management", "Training or consultancy", "Moving into industry", "Other"];
export const EMPLOYERS = ["Medical device company", "Pharmaceutical company", "Diagnostics company", "Agency or consultancy", "Between roles", "Still in the NHS"];
export const MENTORING = ["none", "mentor", "mentee", "both"];

export const str = (v: unknown, max = 200): string => (typeof v === "string" ? v.trim().slice(0, max) : "");
export const isUrl = (u: string): boolean => /^https?:\/\/[^\s]+$/i.test(u);
export const isDate = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v);

export interface Signup {
  email: string; name: string; nmc_pin: string; role_category: string; employer_type: string; speciality: string; region: string;
}

/** Returns the cleaned sign-up, or the message to show the user. */
export function checkSignup(b: Record<string, unknown>): { ok: true; value: Signup } | { ok: false; error: string } {
  const email = str(b.email).toLowerCase();
  const name = str(b.name, 100);
  const pin = str(b.nmc_pin, 8).toUpperCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return { ok: false, error: "Enter a valid email address." };
  if (!name) return { ok: false, error: "Enter your name." };
  if (!PIN_RE.test(pin)) return { ok: false, error: "Your NMC PIN looks like 12A3456E: two digits, a letter, four digits, a letter." };
  if (!ROLES.includes(b.role_category as string)) return { ok: false, error: "Choose your role." };
  if (!EMPLOYERS.includes(b.employer_type as string)) return { ok: false, error: "Choose your employer type." };
  if (b.consent !== true) return { ok: false, error: "Please agree to the privacy notice to join." };
  return { ok: true, value: { email, name, nmc_pin: pin, role_category: b.role_category as string, employer_type: b.employer_type as string,
    speciality: str(b.speciality, 100), region: str(b.region, 100) } };
}

/** Calendar file for a dated event. Callers must not call this for undated events. */
export function ics(e: { id: number; title: string; venue: string | null; detail: string; source_url: string; start_date: string; end_date: string | null }, now = new Date()): string {
  const d = (s: string) => s.replaceAll("-", "");
  const end = new Date(`${e.end_date || e.start_date}T00:00:00Z`);
  end.setUTCDate(end.getUTCDate() + 1);
  const esc = (s: unknown) => String(s || "").replace(/[\;,]/g, (c) => "\\" + c).replace(/\n/g, "\\n");
  return [
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Association for Industry Professional Nurses//EN", "BEGIN:VEVENT",
    `UID:event-${e.id}@medsalesintelligencehub.co.uk`, `DTSTAMP:${now.toISOString().replace(/[-:]|\.\d+/g, "")}`,
    `DTSTART;VALUE=DATE:${d(e.start_date)}`, `DTEND;VALUE=DATE:${end.toISOString().slice(0, 10).replaceAll("-", "")}`,
    `SUMMARY:${esc(e.title)}`, `LOCATION:${esc(e.venue)}`, `DESCRIPTION:${esc(e.detail + " Confirm on the organiser site: " + e.source_url)}`,
    "END:VEVENT", "END:VCALENDAR",
  ].join("\r\n");
}
