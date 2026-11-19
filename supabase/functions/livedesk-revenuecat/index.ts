// livedesk-revenuecat — RevenueCat webhook for Live Desk app subscriptions.
// Added 01/10/2026. Apple and Google subscriptions are handled by RevenueCat;
// every purchase, renewal, cancellation and expiry posts here, and this keeps
// livedesk_access.store_expires_at current. The app's RevenueCat user id is the
// Supabase user id (Purchases.logIn), so events map straight onto accounts.
// Guest (anonymous) Supabase users count too: since 1.0.3 the app lets people
// subscribe without registering (App Store 5.1.1(v)). A TRANSFER (Restore
// purchases on another account, or on a new guest after a reinstall) moves the
// store columns from the old account to the new one.
//
// Auth: RevenueCat sends the Authorization header value set in its dashboard;
// it must equal the REVENUECAT_WEBHOOK_SECRET secret. verify_jwt is OFF.
// Deploy:
//   supabase functions deploy livedesk-revenuecat --no-verify-jwt --project-ref vbthumugbzyqndirmyns

import { fromRevenueCat, transferFromRevenueCat } from "../livedesk/rules.ts";

const BASE = (Deno.env.get("SUPABASE_URL") || "").replace(/\/$/, "");
const KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const HOOK = Deno.env.get("REVENUECAT_WEBHOOK_SECRET") || "";

function same(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

type StoreCols = { store_product: string | null; store_expires_at: string | null; store_platform: string | null };

async function rest(method: string, path: string, body?: unknown, prefer?: string): Promise<Response> {
  const headers: Record<string, string> = { apikey: KEY, Authorization: "Bearer " + KEY, Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (prefer) headers["Prefer"] = prefer;
  return await fetch(BASE + "/rest/v1/" + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
}

// Copy the latest store subscription of the "from" accounts to the "to"
// accounts, then clear it from "from". Hub links are not touched.
async function transfer(from: string[], to: string[]): Promise<Response> {
  const now = new Date().toISOString();
  const r = await rest("GET", "livedesk_access?select=store_product,store_expires_at,store_platform&store_expires_at=not.is.null"
    + "&order=store_expires_at.desc&limit=1&user_id=in.(" + from.join(",") + ")");
  if (!r.ok) { console.error("livedesk-revenuecat transfer read:", r.status); return new Response("store", { status: 502 }); }
  const rows = await r.json() as StoreCols[];
  if (!rows.length) return new Response("nothing to move", { status: 200 });
  for (const uid of to) {
    const w = await rest("POST", "livedesk_access?on_conflict=user_id", { user_id: uid, ...rows[0], updated_at: now },
      "resolution=merge-duplicates,return=minimal");
    if (!w.ok) {
      const t = await w.text();
      if (w.status === 409 || t.includes("foreign key")) continue; // account deleted since
      console.error("livedesk-revenuecat transfer write:", w.status, t.slice(0, 200));
      return new Response("store", { status: 502 });
    }
  }
  const c = await rest("PATCH", "livedesk_access?user_id=in.(" + from.join(",") + ")",
    { store_product: null, store_expires_at: null, store_platform: null, updated_at: now }, "return=minimal");
  if (!c.ok) { console.error("livedesk-revenuecat transfer clear:", c.status); return new Response("store", { status: 502 }); }
  return new Response("moved", { status: 200 });
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("method", { status: 405 });
  if (!BASE || !KEY || HOOK.length < 24) return new Response("config", { status: 500 });
  const auth = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
  if (!same(auth, HOOK)) return new Response("auth", { status: 401 });

  let body: { event?: Record<string, unknown> };
  try { body = await req.json(); } catch { return new Response("json", { status: 400 }); }
  const moved = body && body.event ? transferFromRevenueCat(body.event) : null;
  if (moved) return await transfer(moved.from, moved.to);
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
