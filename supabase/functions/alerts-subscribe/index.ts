// alerts-subscribe — the only way a phone gets onto the Hub alerts list.
// Called by alerts/index.html (GitHub Pages). Added 24/09/2026 so that only
// Hub members can subscribe: before this the page inserted straight into
// push_subscriptions with the public anon key, and anyone could.
//
// POST JSON:
//   {action:"on",  pass?, endpoint, p256dh, auth, specialities, user_agent}
//   {action:"off", endpoint}
//
// "on": a member pass (issued by WordPress snippet 4510 only to a member whose
// plan opens the Live Desk, page 675; see ../ask-the-hub/pass.ts) saves or
// renews the phone against that member. Without a pass, a phone already on
// file for a member may change its specialities; anything else gets 403.
// It upserts on the endpoint, so a re-save really updates the specialities
// (the old direct insert answered 409 and silently kept the old ones).
//
// "off": deletes the row for that endpoint. Knowing the endpoint is proof of
// holding the phone; the browser never shows it to anyone else.
//
// verify_jwt is OFF on purpose: the pass is the auth check
// (supabase-edge-function-auth-standard.md). Deploy:
//   supabase functions deploy alerts-subscribe --no-verify-jwt --project-ref vbthumugbzyqndirmyns
//
// Secrets: ASK_PASS_SECRET (shared with the WordPress snippet),
// SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (injected by Supabase).

import { verifyPass } from "../ask-the-hub/pass.ts";
import { decide, PASS_GRACE, readSub } from "./rules.ts";

const ORIGINS = [
  "https://louisehoult-beep.github.io",
  "https://alerts.medsalesintelligencehub.co.uk",
];
const TABLE = "push_subscriptions";
const DB = (Deno.env.get("SUPABASE_URL") || "").replace(/\/$/, "") + "/rest/v1/" + TABLE;
const KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const SECRET = Deno.env.get("ASK_PASS_SECRET") || "";

function cors(origin: string | null): Record<string, string> {
  return {
    "Access-Control-Allow-Origin": origin && ORIGINS.includes(origin) ? origin : ORIGINS[0],
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function reply(origin: string | null, status: number, body: Record<string, unknown>): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...cors(origin), "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

async function db(method: string, query: string, body?: unknown, prefer?: string): Promise<unknown> {
  const headers: Record<string, string> = { apikey: KEY, Authorization: "Bearer " + KEY, Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (prefer) headers["Prefer"] = prefer;
  const r = await fetch(DB + query, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const text = await r.text();
  if (!r.ok) throw new Error(`${method} ${TABLE} ${r.status}: ${text.slice(0, 200)}`);
  return text ? JSON.parse(text) : null;
}

Deno.serve(async (req) => {
  const origin = req.headers.get("origin");
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
  if (req.method !== "POST") return reply(origin, 405, { ok: false, why: "method" });
  if (!KEY || !SECRET) return reply(origin, 500, { ok: false, why: "config" });

  let body: Record<string, unknown>;
  try { body = await req.json(); } catch { return reply(origin, 400, { ok: false, why: "json" }); }
  if (!body || typeof body !== "object") return reply(origin, 400, { ok: false, why: "json" });

  try {
    if (body.action === "off") {
      if (typeof body.endpoint !== "string" || !body.endpoint) return reply(origin, 400, { ok: false, why: "endpoint" });
      await db("DELETE", "?endpoint=eq." + encodeURIComponent(body.endpoint), undefined, "return=minimal");
      return reply(origin, 200, { ok: true, state: "off" });
    }
    if (body.action !== "on") return reply(origin, 400, { ok: false, why: "action" });

    const sub = readSub(body);
    if (typeof sub === "string") return reply(origin, 400, { ok: false, why: sub });

    const member = await verifyPass(body.pass, SECRET, Math.floor(Date.now() / 1000), PASS_GRACE);
    const rows = await db("GET", "?select=member_id&endpoint=eq." + encodeURIComponent(sub.endpoint)) as
      { member_id: number | null }[];
    const existing = rows && rows.length ? rows[0].member_id : undefined;
    const d = decide(member, existing);
    const now = new Date().toISOString();

    if (d.kind === "refuse") {
      return reply(origin, 403, { ok: false, why: body.pass ? "pass" : "member" });
    }
    if (d.kind === "save") {
      await db("POST", "?on_conflict=endpoint", { ...sub, member_id: d.member_id, verified_at: now, updated_at: now },
        "resolution=merge-duplicates,return=minimal");
    } else {
      await db("PATCH", "?endpoint=eq." + encodeURIComponent(sub.endpoint),
        { p256dh: sub.p256dh, auth: sub.auth, specialities: sub.specialities, user_agent: sub.user_agent, updated_at: now },
        "return=minimal");
    }
    return reply(origin, 200, { ok: true, state: "on", specialities: sub.specialities });
  } catch (err) {
    console.error("alerts-subscribe:", String(err));
    return reply(origin, 502, { ok: false, why: "store" });
  }
});
