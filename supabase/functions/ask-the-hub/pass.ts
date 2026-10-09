// The member pass, and the signature on the gap email. Pure functions: no env
// reads, no network, so both the accept and the reject paths are unit-tested
// (pass_test.ts) without a live WordPress session. See
// "Process flows for all brands/supabase-edge-function-auth-standard.md".
//
// A pass is issued by WordPress (WPCode snippet "Ask the Hub - member pass")
// only to a logged-in user whose membership opens the Live Desk (page 675):
//
//   base64url(JSON {v:1, u:<wp user id>, e:<unix expiry>}) + "." +
//   base64url(HMAC-SHA256(ASK_PASS_SECRET, <that first part>))
//
// It lives at most MAX_LIFE seconds, so a copied pass stops working quickly.

export const MAX_LIFE = 15 * 60;

const enc = new TextEncoder();

function b64url(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromB64url(s: string): string {
  const pad = s.length % 4 ? "=".repeat(4 - (s.length % 4)) : "";
  return atob(s.replace(/-/g, "+").replace(/_/g, "/") + pad);
}

export async function hmac(secret: string, msg: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  return b64url(new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(msg))));
}

function sameString(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

/** The WordPress user id the pass was issued to, or null for anything else.
 *  grace: seconds past expiry a pass is still honoured. 0 for Ask the Hub.
 *  Phone alerts pass a day, because an iPhone member has to add the alerts
 *  page to the Home Screen and open it from there before the pass is used. */
export async function verifyPass(
  pass: unknown, secret: string, now = Math.floor(Date.now() / 1000), grace = 0,
): Promise<number | null> {
  if (typeof pass !== "string" || !secret || secret.length < 32) return null;
  const parts = pass.split(".");
  if (parts.length !== 2 || !parts[0] || !parts[1]) return null;
  if (!sameString(await hmac(secret, parts[0]), parts[1])) return null;
  let claims: { v?: number; u?: unknown; e?: unknown };
  try { claims = JSON.parse(fromB64url(parts[0])); } catch { return null; }
  if (claims.v !== 1) return null;
  if (typeof claims.u !== "number" || !Number.isInteger(claims.u) || claims.u <= 0) return null;
  if (typeof claims.e !== "number" || claims.e <= now - grace || claims.e > now + MAX_LIFE) return null;
  return claims.u;
}

/** Test helper and the shape WordPress must produce. */
export async function makePass(secret: string, user: number, expiry: number): Promise<string> {
  const head = b64url(enc.encode(JSON.stringify({ v: 1, u: user, e: expiry })));
  return head + "." + await hmac(secret, head);
}
