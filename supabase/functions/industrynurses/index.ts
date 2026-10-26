// industrynurses — the Association for Industry Professional Nurses app's server. Added 26/10/2026.
//
// Replaces the Node + SQLite server. Routes are the same /api/... paths, under
// /functions/v1/industrynurses. The app signs in with Supabase Auth (email code);
// this function reads the member from the bearer token and applies the rules in
// handler.ts. Deploy with the gateway JWT check OFF, because the public routes
// (options, events) and sign-up are called before anyone is signed in:
//
//   supabase functions deploy industrynurses --no-verify-jwt --project-ref vbthumugbzyqndirmyns
//
// Secrets: ADMIN_EMAILS (comma separated; those sign-ups are approved admins).
// SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY and SUPABASE_DB_URL are injected by Supabase.

import postgres from "npm:postgres@3.4.5";
import { createHandler, type Auth } from "./handler.ts";

const BASE = (Deno.env.get("SUPABASE_URL") || "").replace(/\/$/, "");
const SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const ANON = Deno.env.get("SUPABASE_ANON_KEY") || "";

const sql = postgres(Deno.env.get("SUPABASE_DB_URL") || "", { max: 3, prepare: false, idle_timeout: 20 });

const gotrue = (path: string, init: RequestInit & { key?: string } = {}) =>
  fetch(BASE + "/auth/v1" + path, { ...init, headers: { apikey: init.key || SERVICE, Authorization: "Bearer " + (init.key || SERVICE), "Content-Type": "application/json", ...(init.headers || {}) } });

const auth: Auth = {
  async userFromToken(token) {
    const r = await fetch(BASE + "/auth/v1/user", { headers: { apikey: ANON || SERVICE, Authorization: "Bearer " + token } });
    if (!r.ok) return null;
    const u = await r.json();
    return typeof u?.id === "string" ? { id: u.id, email: String(u.email || "") } : null;
  },
  async createUser(email) {
    const r = await gotrue("/admin/users", { method: "POST", body: JSON.stringify({ email, email_confirm: true }) });
    if (r.ok) return (await r.json()).id as string;
    if (r.status === 422) return null; // email_exists
    throw new Error("createUser " + r.status + " " + (await r.text()).slice(0, 200));
  },
  async sendCode(email) {
    const r = await gotrue("/otp", { method: "POST", key: ANON, body: JSON.stringify({ email, create_user: false }) });
    if (!r.ok) throw new Error("sendCode " + r.status + " " + (await r.text()).slice(0, 200));
  },
  async deleteUser(id) {
    const r = await gotrue("/admin/users/" + id, { method: "DELETE" });
    if (!r.ok && r.status !== 404) throw new Error("deleteUser " + r.status);
  },
};

const handle = createHandler({
  query: async (text, params = []) => [...await sql.unsafe(text, params as never[])],
  auth,
  adminEmails: (Deno.env.get("ADMIN_EMAILS") || "").toLowerCase().split(",").map((s) => s.trim()).filter(Boolean),
});

Deno.serve((req) => (!BASE || !SERVICE ? new Response('{"error":"config"}', { status: 500 }) : handle(req)));
