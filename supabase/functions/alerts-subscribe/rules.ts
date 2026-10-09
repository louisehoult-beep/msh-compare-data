// The phone alerts sign-up rules. Pure functions: no env reads, no network,
// so every accept and reject path is unit-tested (rules_test.ts).
//
// Added 24/09/2026. Lou: only paying members can subscribe. Until then the
// alerts page inserted rows straight into push_subscriptions with the public
// anon key, so anyone who found the page could sign up.

/** Seconds past its expiry a member pass is still honoured here. An iPhone
 *  member adds the alerts page to the Home Screen and opens it from there
 *  before the pass is used, which can take longer than the pass's own life. */
export const PASS_GRACE = 24 * 3600;

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const B64URL = /^[A-Za-z0-9_-]+$/;

export type Sub = {
  endpoint: string;
  p256dh: string;
  auth: string;
  specialities: string[];
  user_agent: string;
};

/** A clean subscription from the request body, or a reason it is refused. */
export function readSub(body: Record<string, unknown>): Sub | string {
  const endpoint = body.endpoint;
  if (typeof endpoint !== "string" || endpoint.length > 1000 || !/^https:\/\/[^\s/]+\/\S+$/.test(endpoint)) {
    return "endpoint";
  }
  const p256dh = body.p256dh, auth = body.auth;
  if (typeof p256dh !== "string" || p256dh.length < 40 || p256dh.length > 200 || !B64URL.test(p256dh)) return "keys";
  if (typeof auth !== "string" || auth.length < 16 || auth.length > 100 || !B64URL.test(auth)) return "keys";
  const specs = body.specialities ?? [];
  if (!Array.isArray(specs) || specs.length > 60) return "specialities";
  const clean: string[] = [];
  for (const s of specs) {
    if (typeof s !== "string" || s.length > 80 || !SLUG.test(s)) return "specialities";
    if (!clean.includes(s)) clean.push(s);
  }
  const ua = typeof body.user_agent === "string" ? body.user_agent.slice(0, 200) : "";
  return { endpoint, p256dh, auth, specialities: clean, user_agent: ua };
}

export type Decision =
  | { kind: "save"; member_id: number }   // new or renewed by a valid pass
  | { kind: "update" }                    // already a verified member's phone
  | { kind: "refuse"; why: "member" };

/** member: the user id a valid pass proved, or null.
 *  existing: this endpoint's current member_id, undefined when not on file.
 *  Holding the endpoint is proof of holding the phone (the browser keeps it
 *  secret), so a verified phone may change its own specialities without a
 *  fresh pass. An unverified row never becomes verified without one. */
export function decide(member: number | null, existing: number | null | undefined): Decision {
  if (member !== null) return { kind: "save", member_id: member };
  if (typeof existing === "number" && existing > 0) return { kind: "update" };
  return { kind: "refuse", why: "member" };
}
