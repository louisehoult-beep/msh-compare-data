// livedesk — everything the Live Desk app asks the server for. Added 01/10/2026.
//
// The caller is a signed-in app user: Supabase Auth checks the user's JWT
// before this runs (verify_jwt ON), and this function reads the user id from
// it via /auth/v1/user. POST JSON, one of:
//
//   {action:"status"}                         -> access status (rules.ts status())
//   {action:"feed"}                           -> the Live Desk document, or 402
//   {action:"link", pass}                     -> link a Hub membership (member pass
//                                                from WordPress snippet 4510, the
//                                                same pass Ask the Hub and phone
//                                                alerts use; ../ask-the-hub/pass.ts)
//   {action:"device", token, platform, specialities}  -> save this phone for alerts
//   {action:"device-off", token}              -> stop alerts to this phone
//   {action:"delete-account"}                 -> delete the account and everything
//                                                tied to it (App Store rule 5.1.1(v))
//
// A Hub membership opens ONE app account: linking moves hub_member_id to the
// caller and clears it from any other account (unique column).
//
// Deploy:
//   supabase functions deploy livedesk --project-ref vbthumugbzyqndirmyns
// Secrets: ASK_PASS_SECRET (shared with WordPress), SUPABASE_URL,
// SUPABASE_SERVICE_ROLE_KEY and SUPABASE_ANON_KEY (injected by Supabase).

import { verifyPass } from "../ask-the-hub/pass.ts";
import { PASS_GRACE, readDevice, status } from "./rules.ts";

// Capacitor serves the app from these origins (iOS, Android).
const ORIGINS = ["capacitor://localhost", "https://localhost", "http://localhost"];
const BASE = (Deno.env.get("SUPABASE_URL") || "").replace(/\/$/, "");
const KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const ANON = Deno.env.get("SUPABASE_ANON_KEY") || "";
const SECRET = Deno.env.get("ASK_PASS_SECRET") || "";

function cors(origin: string | null): Record<string, string> {
  return {
    "Access-Control-Allow-Origin": origin && ORIGINS.includes(origin) ? origin : ORIGINS[0],
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function reply(origin: string | null, code: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: code,
    headers: { ...cors(origin), "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

async function rest(method: string, path: string, body?: unknown, prefer?: string): Promise<unknown> {
  const headers: Record<string, string> = { apikey: KEY, Authorization: "Bearer " + KEY, Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (prefer) headers["Prefer"] = prefer;
  const r = await fetch(BASE + "/rest/v1/" + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const text = await r.text();
  if (!r.ok) throw new Error(`${method} ${path.split("?")[0]} ${r.status}: ${text.slice(0, 200)}`);
  return text ? JSON.parse(text) : null;
}

async function userId(req: Request): Promise<string | null> {
  const auth = req.headers.get("authorization") || "";
  if (!auth.startsWith("Bearer ")) return null;
  const r = await fetch(BASE + "/auth/v1/user", { headers: { apikey: ANON || KEY, Authorization: auth } });
  if (!r.ok) return null;
  const u = await r.json();
  return typeof u?.id === "string" ? u.id : null;
}

type Row = { hub_member_id: number | null; hub_verified_at: string | null; store_expires_at: string | null };

async function accessRow(uid: string): Promise<Row | null> {
  const rows = await rest("GET", "livedesk_access?select=hub_member_id,hub_verified_at,store_expires_at&user_id=eq." + uid) as Row[];
  return rows && rows.length ? rows[0] : null;
}

Deno.serve(async (req) => {
  const origin = req.headers.get("origin");
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
  if (req.method !== "POST") return reply(origin, 405, { ok: false, why: "method" });
  if (!BASE || !KEY) return reply(origin, 500, { ok: false, why: "config" });

  let body: Record<string, unknown>;
  try { body = await req.json(); } catch { return reply(origin, 400, { ok: false, why: "json" }); }
  if (!body || typeof body !== "object") return reply(origin, 400, { ok: false, why: "json" });

  try {
    const uid = await userId(req);
    if (!uid) return reply(origin, 401, { ok: false, why: "login" });
    const now = new Date().toISOString();

    switch (body.action) {
      case "status":
        return reply(origin, 200, { ok: true, ...status(await accessRow(uid)) });

      case "feed": {
        const s = status(await accessRow(uid));
        if (!s.access) return reply(origin, 402, { ok: false, why: s.relink ? "relink" : "subscribe", ...s });
        const rows = await rest("GET", "livedesk_feed?select=payload&id=eq.current") as { payload: unknown }[];
        if (!rows || !rows.length) return reply(origin, 503, { ok: false, why: "empty" });
        return reply(origin, 200, { ok: true, feed: rows[0].payload, ...s });
      }

      case "link": {
        if (!SECRET) return reply(origin, 500, { ok: false, why: "config" });
        const member = await verifyPass(body.pass, SECRET, Math.floor(Date.now() / 1000), PASS_GRACE);
        if (member === null) return reply(origin, 403, { ok: false, why: "pass" });
        // One membership, one account: release it from any other account first.
        await rest("PATCH", `livedesk_access?hub_member_id=eq.${member}&user_id=neq.${uid}`,
          { hub_member_id: null, hub_verified_at: null, updated_at: now }, "return=minimal");
        await rest("POST", "livedesk_access?on_conflict=user_id",
          { user_id: uid, hub_member_id: member, hub_verified_at: now, updated_at: now },
          "resolution=merge-duplicates,return=minimal");
        return reply(origin, 200, { ok: true, ...status(await accessRow(uid)) });
      }

      case "device": {
        const d = readDevice(body);
        if (typeof d === "string") return reply(origin, 400, { ok: false, why: d });
        await rest("POST", "livedesk_devices?on_conflict=token",
          { ...d, user_id: uid, updated_at: now }, "resolution=merge-duplicates,return=minimal");
        return reply(origin, 200, { ok: true, specialities: d.specialities });
      }

      case "device-off": {
        if (typeof body.token !== "string" || !body.token) return reply(origin, 400, { ok: false, why: "token" });
        await rest("DELETE", `livedesk_devices?token=eq.${encodeURIComponent(body.token)}&user_id=eq.${uid}`,
          undefined, "return=minimal");
        return reply(origin, 200, { ok: true });
      }

      case "delete-account": {
        // Deleting the auth user cascades to livedesk_access and livedesk_devices.
        const r = await fetch(BASE + "/auth/v1/admin/users/" + uid, {
          method: "DELETE", headers: { apikey: KEY, Authorization: "Bearer " + KEY },
        });
        if (!r.ok) throw new Error("delete user " + r.status);
        return reply(origin, 200, { ok: true, deleted: true });
      }

      default:
        return reply(origin, 400, { ok: false, why: "action" });
    }
  } catch (err) {
    console.error("livedesk:", String(err));
    return reply(origin, 502, { ok: false, why: "store" });
  }
});
