// livedesk-revenuecat — RevenueCat webhook for Live Desk app subscriptions.
// Added 01/10/2026. Apple and Google subscriptions are handled by RevenueCat;
// every purchase, renewal, cancellation and expiry posts here, and this keeps
// livedesk_access.store_expires_at current. The app's RevenueCat user id is the
// Supabase user id (Purchases.logIn), so events map straight onto accounts.
//
// Auth: RevenueCat sends the Authorization header value set in its dashboard;
// it must equal the REVENUECAT_WEBHOOK_SECRET secret. verify_jwt is OFF.
// Deploy:
//   supabase functions deploy livedesk-revenuecat --no-verify-jwt --project-ref vbthumugbzyqndirmyns

import { fromRevenueCat } from "../livedesk/rules.ts";

const BASE = (Deno.env.get("SUPABASE_URL") || "").replace(/\/$/, "");
const KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const HOOK = Deno.env.get("REVENUECAT_WEBHOOK_SECRET") || "";

function same(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("method", { status: 405 });
  if (!BASE || !KEY || HOOK.length < 24) return new Response("config", { status: 500 });
  const auth = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
  if (!same(auth, HOOK)) return new Response("auth", { status: 401 });

  let body: { event?: Record<string, unknown> };
  try { body = await req.json(); } catch { return new Response("json", { status: 400 }); }
  const row = body && body.event ? fromRevenueCat(body.event) : null;
  // Ignored events still answer 200, or RevenueCat retries them for days.
  if (!row) return new Response("ignored", { status: 200 });

  const r = await fetch(BASE + "/rest/v1/livedesk_access?on_conflict=user_id", {
    method: "POST",
    headers: {
      apikey: KEY, Authorization: "Bearer " + KEY, "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates,return=minimal",
    },
    body: JSON.stringify({ ...row, updated_at: new Date().toISOString() }),
  });
  if (!r.ok) {
    // A user deleted since the purchase has no auth row: the foreign key refuses
    // the insert. Nothing to keep; say so and stop the retries.
    const t = await r.text();
    if (r.status === 409 || t.includes("foreign key")) return new Response("no user", { status: 200 });
    console.error("livedesk-revenuecat:", r.status, t.slice(0, 200));
    return new Response("store", { status: 502 });
  }
  return new Response("ok", { status: 200 });
});
