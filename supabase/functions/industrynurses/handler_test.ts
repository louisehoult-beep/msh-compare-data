// Runs the real handler against a real Postgres (PGlite, in memory) loaded with the real migration.
// Only Supabase Auth is faked: a token is just the user id.
import { assert, assertEquals } from "jsr:@std/assert@1";
import { PGlite } from "npm:@electric-sql/pglite@0.2.17";
import { createHandler, type Auth } from "./handler.ts";

const MIGRATION = await Deno.readTextFile(new URL("../../migrations/20261026180000_industry_nurses_app.sql", import.meta.url));

async function boot() {
  const db = new PGlite();
  await db.exec(`create role anon; create role authenticated; create schema auth;
    create table auth.users (id uuid primary key default gen_random_uuid(), email text unique);`);
  await db.exec(MIGRATION);
  const sent: string[] = [];
  const deleted: string[] = [];
  const auth: Auth = {
    userFromToken: async (t) => { const r = await db.query<{ id: string; email: string }>("select id, email from auth.users where id::text = $1", [t]); return r.rows[0] ?? null; },
    createUser: async (email) => { const r = await db.query<{ id: string }>("insert into auth.users (email) values ($1) on conflict do nothing returning id", [email]); return r.rows[0]?.id ?? null; },
    sendCode: async (email) => { sent.push(email); },
    deleteUser: async (id) => { deleted.push(id); await db.query("delete from auth.users where id = $1", [id]); },
  };
  const handle = createHandler({ query: async (t, p = []) => (await db.query(t, p as never[])).rows as never, auth, adminEmails: ["admin@example.com"] });
  const client = (token?: string) => async (method: string, path: string, body?: unknown) => {
    const r = await handle(new Request("https://x.test/functions/v1/industrynurses" + path, { method, headers: { "content-type": "application/json", ...(token ? { authorization: "Bearer " + token } : {}) }, body: body ? JSON.stringify(body) : undefined }));
    const ct = r.headers.get("content-type") || "";
    return { status: r.status, body: ct.includes("json") ? await r.json() : await r.text(), headers: r.headers };
  };
  const anon = client();
  const join = async (email: string, extra = {}) => {
    const r = await anon("POST", "/api/auth/signup", signup(email, extra));
    assertEquals(r.status, 200, JSON.stringify(r.body));
    const id = (await db.query<{ id: string }>("select id from auth.users where email = $1", [email])).rows[0].id;
    return { id, call: client(id) };
  };
  const approveAll = () => db.exec("update ain_members set status = 'approved'");
  return { db, anon, join, sent, deleted, approveAll };
}
const signup = (email: string, extra = {}) => ({ email, name: "Test Nurse", nmc_pin: "12A3456E", role_category: "Clinical educator", employer_type: "Medical device company", consent: true, ...extra });

Deno.test("signup validates PIN and consent, then emails a code", async () => {
  const { anon, sent } = await boot();
  assertEquals((await anon("POST", "/api/auth/signup", signup("a@example.com", { nmc_pin: "bad" }))).status, 400);
  assertEquals((await anon("POST", "/api/auth/signup", signup("a@example.com", { consent: false }))).status, 400);
  assertEquals(sent.length, 0);
  assertEquals((await anon("POST", "/api/auth/signup", signup("a@example.com"))).status, 200);
  assertEquals(sent, ["a@example.com"]);
  assertEquals((await anon("POST", "/api/auth/signup", signup("a@example.com"))).status, 409);
});

Deno.test("pending members are gated, approved members are not, admins decide", async () => {
  const { join } = await boot();
  const admin = await join("admin@example.com");
  const nurse = await join("nurse@example.com");
  assertEquals((await nurse.call("GET", "/api/channels")).status, 403);
  assertEquals((await nurse.call("GET", "/api/jobs")).status, 403);
  const pending = (await admin.call("GET", "/api/admin/pending")).body;
  assertEquals(pending.length, 1);
  assertEquals((await nurse.call("GET", "/api/admin/pending")).status, 403);
  assertEquals((await admin.call("POST", `/api/admin/members/${pending[0].id}/decision`, { decision: "approve" })).status, 200);
  assertEquals((await nurse.call("GET", "/api/channels")).status, 200);
  assertEquals((await nurse.call("GET", "/api/me")).body.unread, 1);
});

Deno.test("unknown emails look the same as members, and nobody is signed in without a token", async () => {
  const { anon, sent, join } = await boot();
  await join("known@example.com");
  sent.length = 0;
  assertEquals((await anon("POST", "/api/auth/request", { email: "nobody@example.com" })).body, { ok: true });
  assertEquals((await anon("POST", "/api/auth/request", { email: "known@example.com" })).body, { ok: true });
  assertEquals(sent, ["known@example.com"]);
  assertEquals((await anon("GET", "/api/me")).body, { member: null });
  assertEquals((await anon("GET", "/api/channels")).status, 401);
});

Deno.test("community: post, reply, notify, report, hide", async () => {
  const { join, approveAll } = await boot();
  const admin = await join("admin@example.com"), a = await join("a@example.com"), b = await join("b@example.com");
  await approveAll();
  const t = await a.call("POST", "/api/channels/moving-into-industry/posts", { body: "How did you move across?" });
  assertEquals(t.status, 200);
  await b.call("POST", "/api/channels/moving-into-industry/posts", { body: "Start with NAMDET.", parent_id: t.body.id });
  assertEquals((await a.call("GET", "/api/me")).body.unread, 1);
  const thread = (await a.call("GET", "/api/channels/moving-into-industry/posts")).body.threads[0];
  assertEquals(thread.replies.length, 1);
  assertEquals((await a.call("POST", `/api/posts/${t.body.id}/report`, { reason: "test" })).status, 200);
  const reports = (await admin.call("GET", "/api/admin/reports")).body;
  assertEquals(reports.length, 1);
  await admin.call("POST", `/api/admin/reports/${reports[0].id}/resolve`, { hide: true });
  assertEquals((await a.call("GET", "/api/channels/moving-into-industry/posts")).body.threads.length, 0);
});

Deno.test("directory only shows members who opted in, and never email or PIN", async () => {
  const { join, approveAll } = await boot();
  const a = await join("a@example.com"), b = await join("b@example.com", { name: "Hidden Person" });
  await approveAll();
  assertEquals((await a.call("GET", "/api/directory")).body.length, 0);
  await b.call("PATCH", "/api/me", { directory_visible: true });
  const dir = (await a.call("GET", "/api/directory")).body;
  assertEquals(dir.length, 1);
  assertEquals(dir[0].email, undefined);
  assertEquals(dir[0].nmc_pin, undefined);
  assertEquals((await a.call("GET", "/api/directory?q=hidd")).body.length, 1);
});

Deno.test("undated events have no calendar file; dated ones do; saves work", async () => {
  const { anon, join } = await boot();
  const events = (await anon("GET", "/api/events")).body;
  const undated = events.find((e: { start_date: unknown }) => !e.start_date), dated = events.find((e: { start_date: unknown }) => e.start_date);
  assertEquals(typeof dated.start_date, "string");
  assertEquals((await anon("GET", `/api/events/${undated.id}.ics`)).status, 404);
  const ics = await anon("GET", `/api/events/${dated.id}.ics`);
  assertEquals(ics.status, 200);
  assert(String(ics.body).includes("BEGIN:VEVENT"));
  const a = await join("a@example.com");
  await a.call("POST", `/api/events/${dated.id}/save`);
  assertEquals((await a.call("GET", "/api/events")).body.find((e: { id: number }) => e.id === dated.id).saved, true);
  assertEquals((await anon("GET", "/api/events")).body.find((e: { id: number }) => e.id === dated.id).saved, false);
});

Deno.test("member can delete their account; posts stay but lose their text and author", async () => {
  const { join, approveAll, db, deleted } = await boot();
  const a = await join("a@example.com");
  await approveAll();
  await a.call("POST", "/api/channels/regional/posts", { body: "Private thought" });
  assertEquals((await a.call("DELETE", "/api/me")).status, 200);
  assertEquals((await db.query("select count(*)::int c from ain_members")).rows[0], { c: 0 });
  assertEquals((await db.query("select body, hidden, member_id from ain_posts")).rows[0], { body: "[deleted]", hidden: true, member_id: null });
  assertEquals(deleted, [a.id]);
});

Deno.test("blocked members disappear from the blocker's feed only", async () => {
  const { join, approveAll } = await boot();
  const a = await join("a@example.com"), b = await join("b@example.com");
  await approveAll();
  await b.call("POST", "/api/channels/regional/posts", { body: "Hello from B" });
  assertEquals((await a.call("GET", "/api/channels/regional/posts")).body.threads.length, 1);
  assertEquals((await a.call("POST", `/api/members/${b.id}/block`)).status, 200);
  assertEquals((await a.call("GET", "/api/channels/regional/posts")).body.threads.length, 0);
  assertEquals((await b.call("GET", "/api/channels/regional/posts")).body.threads.length, 1);
});

Deno.test("only admins add jobs, resources and events; jobs need the employer's own link", async () => {
  const { join, approveAll } = await boot();
  const admin = await join("admin@example.com"), a = await join("a@example.com");
  await approveAll();
  const job = { employer: "Acme", title: "Clinical specialist", source_url: "https://acme.example/jobs/1", remote: true };
  assertEquals((await a.call("POST", "/api/admin/jobs", job)).status, 403);
  assertEquals((await admin.call("POST", "/api/admin/jobs", { ...job, source_url: "" })).status, 400);
  assertEquals((await admin.call("POST", "/api/admin/jobs", job)).status, 200);
  assertEquals((await a.call("GET", "/api/jobs?remote=1&q=acme")).body.length, 1);
  const id = (await a.call("GET", "/api/jobs")).body[0].id;
  assertEquals((await a.call("POST", `/api/jobs/${id}/click`)).body.url, job.source_url);
  assertEquals((await admin.call("GET", "/api/admin/stats")).body.job_clicks, 1);
});
