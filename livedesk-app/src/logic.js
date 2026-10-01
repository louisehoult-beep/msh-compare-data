// Pure helpers for the Live Desk app: no DOM, no plugins, so node --test runs them.

export const LINK_SCHEME = 'uk.co.medsalesintelligencehub.livedesk://';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-10-01" -> "1 Oct". Anything unreadable -> "". */
export function shortDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
  if (!m) return '';
  const mon = MONTHS[Number(m[2]) - 1];
  return mon ? `${Number(m[3])} ${mon}` : '';
}

/** "2026-10-01T09:35:00Z" -> "1 Oct, 10:35" in UK time. */
export function stamp(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/London', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(d);
  const get = (t) => (parts.find((p) => p.type === t) || {}).value || '';
  return `${get('day')} ${get('month')}, ${get('hour')}:${get('minute')}`;
}

/** The member pass from a link back from the Hub page, or null. */
export function passFromLink(url) {
  if (typeof url !== 'string' || !url.startsWith(LINK_SCHEME + 'link')) return null;
  const q = url.indexOf('?');
  if (q < 0) return null;
  const pass = new URLSearchParams(url.slice(q + 1)).get('pass');
  return pass && /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(pass) ? pass : null;
}

/** Feed panels narrowed to the chosen specialities. Empty choice = everything.
 *  Note rows (panel status lines) are kept only when nothing is filtered.
 *  Panels left with no rows are dropped. */
export function filterFeed(feed, chosen) {
  const panels = (feed && feed.panels) || [];
  if (!chosen || !chosen.length) return panels;
  const want = new Set(chosen);
  return panels
    .map((p) => ({ ...p, rows: (p.rows || []).filter((r) => r.kind !== 'note' && (r.specialities || []).some((s) => want.has(s))) }))
    .filter((p) => p.rows.length);
}

/** Count of rows marked new across the panels. */
export function newCount(panels) {
  return panels.reduce((n, p) => n + (p.rows || []).filter((r) => r.new).length, 0);
}

/** Only http(s) links are opened. */
export function safeUrl(u) {
  return typeof u === 'string' && /^https?:\/\//i.test(u) ? u : '';
}

/** Alert items carried in a notification's data, or []. */
export function itemsFromNotification(data) {
  if (!data || typeof data.items !== 'string') return [];
  try {
    const items = JSON.parse(data.items);
    return Array.isArray(items) ? items.filter((i) => i && typeof i.t === 'string') : [];
  } catch {
    return [];
  }
}
