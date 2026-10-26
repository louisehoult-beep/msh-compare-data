// The Association app's API, ported from the Node + SQLite server (26/10/2026).
// Same routes and rules as before; members are Supabase Auth users. The handler
// takes its database and auth as arguments so tests can run it against a real
// Postgres (PGlite) with a fake auth.
import { checkSignup, EMPLOYERS, ics, isDate, isUrl, MENTORING, ROLES, str } from "./rules.ts";

// deno-lint-ignore no-explicit-any
export type Row = Record<string, any>;
export type Query = (text: string, params?: unknown[]) => Promise<Row[]>;
export interface Auth {
  /** The Supabase Auth user behind a bearer token, or null. */
  userFromToken(token: string): Promise<{ id: string; email: string } | null>;
  /** Create a confirmed auth user for this email; null when one already exists. */
  createUser(email: string): Promise<string | null>;
  /** Email the 6-digit sign-in code. */
  sendCode(email: string): Promise<void>;
  deleteUser(id: string): Promise<void>;
}
export interface Deps { query: Query; auth: Auth; adminEmails?: string[] }

const ORIGINS = ["capacitor://localhost", "https://localhost", "http://localhost"];
const cors = (origin: string | null): Record<string, string> => ({
  "Access-Control-Allow-Origin": origin && ORIGINS.includes(origin) ? origin : ORIGINS[0],
  "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,OPTIONS",
  "Access-Control-Allow-Headers": "authorization, content-type, apikey, x-client-info",
  "Access-Control-Max-Age": "86400",
  "Vary": "Origin",
});

class HttpError extends Error { constructor(public code: number, msg: string) { super(msg); } }
const fail = (msg: string, code = 400): never => { throw new HttpError(code, msg); };

const EVENT_COLS = "e.id, e.title, e.organiser, e.detail, e.start_date::text AS start_date, e.end_date::text AS end_date, e.venue, e.source_url, e.source_label, e.group_label, e.members_only, e.verified_at::text AS verified_at";

export function createHandler({ query, auth, adminEmails = [] }: Deps) {
  const one = async (text: string, params: unknown[] = []) => (await query(text, params))[0] ?? null;
  const notify = (memberId: string, text: string, link = "") =>
    query("INSERT INTO ain_notifications (member_id, text, link) VALUES ($1,$2,$3)", [memberId, text, link]);
  const notifyAdmins = async (text: string, exceptId: string | null = null) => {
    for (const a of await query("SELECT id FROM ain_members WHERE is_admin AND ($1::uuid IS NULL OR id <> $1)", [exceptId])) await notify(a.id, text, "/admin");
  };

  return async function handle(req: Request): Promise<Response> {
    const origin = req.headers.get("origin");
    const send = (code: number, body: unknown, extra: Record<string, string> = {}) => new Response(JSON.stringify(body), {
      status: code, headers: { ...cors(origin), "Content-Type": "application/json", "Cache-Control": "no-store", ...extra } });
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });

    try {
      const url = new URL(req.url);
      const path = url.pathname.replace(/^.*\/industrynurses(?=\/|$)/, "") || "/";
      const m = req.method;
      const body: Row = m === "GET" || m === "DELETE" ? {} : await req.json().catch(() => ({}));
      const ok = { ok: true };

      // ---- who is calling
      const bearer = /^Bearer (.+)$/.exec(req.headers.get("authorization") || "")?.[1];
      const user = bearer ? await auth.userFromToken(bearer) : null;
      const me: Row | null = user ? await one("SELECT * FROM ain_members WHERE id = $1", [user.id]) : null;
      const needAuth = (): Row => me ?? fail("Please sign in.", 401);
      const needApproved = (): Row => needAuth().status === "approved" ? me! : fail("Your membership is waiting for approval.", 403);
      const needAdmin = (): Row => needAuth().is_admin ? me! : fail("Admins only.", 403);
      const route = (method: string, re: RegExp): RegExpExecArray | null => (m === method ? re.exec(path) : null);
      let r: RegExpExecArray | null;

      // ---- auth
      if (route("GET", /^\/api\/options$/)) return send(200, { roles: ROLES, employers: EMPLOYERS });

      if (route("POST", /^\/api\/auth\/signup$/)) {
        const c = checkSignup(body);
        if (!c.ok) return fail(c.error);
        const s = c.value;
        if (await one("SELECT 1 FROM ain_members WHERE email = $1", [s.email])) return fail('That email is already registered. Use "Sign in".', 409);
        // An auth user may already exist (a Live Desk account, or an earlier half-finished sign-up): reuse it.
        const id = (await auth.createUser(s.email)) ?? (await one("SELECT id FROM auth.users WHERE lower(email) = $1", [s.email]))?.id;
        if (!id) return fail("We could not create your account. Try again.", 500);
        const isAdmin = adminEmails.includes(s.email);
        await query(`INSERT INTO ain_members (id, email, name, nmc_pin, role_category, employer_type, speciality, region, status, is_admin, verified_at, consent_at)
          VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,now())`,
          [id, s.email, s.name, s.nmc_pin, s.role_category, s.employer_type, s.speciality, s.region,
            isAdmin ? "approved" : "pending", isAdmin, isAdmin ? new Date().toISOString() : null]);
        await notifyAdmins(`New member waiting for approval: ${s.name}`, id);
        await auth.sendCode(s.email);
        return send(200, ok);
      }

      if (route("POST", /^\/api\/auth\/request$/)) {
        const email = str(body.email).toLowerCase();
        // Same answer whether or not the email is registered, so the form cannot be used to probe for members.
        if (await one("SELECT 1 FROM ain_members WHERE email = $1", [email])) await auth.sendCode(email).catch((e) => console.error("sendCode", e));
        return send(200, ok);
      }

      // Sign-in itself (code check) is done by Supabase Auth; the app calls it directly. Logout is the app dropping its tokens.
      if (route("POST", /^\/api\/auth\/logout$/)) return send(200, ok);

      if (route("GET", /^\/api\/me$/)) {
        if (!me) return send(200, { member: null });
        const unread = (await one("SELECT COUNT(*)::int c FROM ain_notifications WHERE member_id = $1 AND NOT read", [me.id]))!.c;
        return send(200, { member: pub(me), unread });
      }

      if (route("PATCH", /^\/api\/me$/)) {
        const u = needAuth();
        const mentoring = MENTORING.includes(body.mentoring) ? body.mentoring : u.mentoring;
        const role = ROLES.includes(body.role_category) ? body.role_category : u.role_category;
        const emp = EMPLOYERS.includes(body.employer_type) ? body.employer_type : u.employer_type;
        const row = await one(`UPDATE ain_members SET name=$1, role_category=$2, employer_type=$3, speciality=$4, region=$5, directory_visible=$6, mentoring=$7, email_notifications=$8
          WHERE id=$9 RETURNING *`,
          [str(body.name, 100) || u.name, role, emp, str(body.speciality ?? u.speciality, 100), str(body.region ?? u.region, 100),
            body.directory_visible === undefined ? u.directory_visible : !!body.directory_visible, mentoring,
            body.email_notifications === undefined ? u.email_notifications : !!body.email_notifications, u.id]);
        return send(200, { member: pub(row!) });
      }

      // Member can delete their own account and data (UK GDPR erasure, App Store rule 5.1.1(v)).
      if (route("DELETE", /^\/api\/me$/)) {
        const u = needAuth();
        await query("UPDATE ain_posts SET body = '[deleted]', hidden = true WHERE member_id = $1", [u.id]);
        await query("DELETE FROM ain_members WHERE id = $1", [u.id]); // cascades notifications, saves, clicks, reports, blocks; posts keep a null author
        // Another app (Live Desk) may use the same sign-in: only remove the auth user when nothing else needs it.
        const live = await one("SELECT to_regclass('public.livedesk_access') AS t");
        const shared = live?.t ? await one("SELECT 1 FROM livedesk_access WHERE user_id = $1", [u.id]) : null;
        if (!shared) await auth.deleteUser(u.id);
        return send(200, ok);
      }

      if (route("GET", /^\/api\/me\/export$/)) {
        const u = needAuth();
        return send(200, {
          member: await one("SELECT * FROM ain_members WHERE id = $1", [u.id]),
          posts: await query("SELECT * FROM ain_posts WHERE member_id = $1", [u.id]),
          saved_events: await query("SELECT event_id FROM ain_event_saves WHERE member_id = $1", [u.id]),
          job_clicks: await query("SELECT job_id, created_at FROM ain_job_clicks WHERE member_id = $1", [u.id]),
        });
      }

      // ---- notifications
      if (route("GET", /^\/api\/notifications$/)) return send(200, await query("SELECT * FROM ain_notifications WHERE member_id = $1 ORDER BY id DESC LIMIT 50", [needAuth().id]));
      if (route("POST", /^\/api\/notifications\/read$/)) { await query("UPDATE ain_notifications SET read = true WHERE member_id = $1", [needAuth().id]); return send(200, ok); }

      // ---- events (public read; saves need a member)
      if (route("GET", /^\/api\/events$/)) {
        const rows = await query(`SELECT ${EVENT_COLS}, (s.member_id IS NOT NULL) AS saved FROM ain_events e
          LEFT JOIN ain_event_saves s ON s.event_id = e.id AND s.member_id = $1
          ORDER BY (e.start_date IS NULL), e.start_date, e.title`, [me?.id ?? null]);
        return send(200, rows);
      }
      if ((r = route("POST", /^\/api\/events\/(\d+)\/save$/))) {
        if (!await one("SELECT 1 FROM ain_events WHERE id = $1", [r[1]])) return fail("Event not found.", 404);
        await query("INSERT INTO ain_event_saves (event_id, member_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", [r[1], needAuth().id]);
        return send(200, ok);
      }
      if ((r = route("DELETE", /^\/api\/events\/(\d+)\/save$/))) {
        await query("DELETE FROM ain_event_saves WHERE event_id = $1 AND member_id = $2", [r[1], needAuth().id]);
        return send(200, ok);
      }
      if ((r = route("GET", /^\/api\/events\/(\d+)\.ics$/))) {
        const e = await one(`SELECT ${EVENT_COLS} FROM ain_events e WHERE e.id = $1`, [r[1]]);
        if (!e || !e.start_date) return fail("This event has no confirmed date.", 404);
        return new Response(ics(e as Parameters<typeof ics>[0]), { headers: { ...cors(origin), "Content-Type": "text/calendar; charset=utf-8", "Content-Disposition": `attachment; filename="event-${e.id}.ics"` } });
      }
      if (route("POST", /^\/api\/admin\/events$/)) {
        const a = needAdmin();
        if (!str(body.title) || !isUrl(str(body.source_url, 500))) return fail("Title and a source link are needed.");
        const row = await one(`INSERT INTO ain_events (title, organiser, detail, start_date, end_date, venue, source_url, group_label, members_only, verified_at)
          VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,current_date) RETURNING id`,
          [str(body.title), str(body.organiser), str(body.detail, 1000), isDate(body.start_date) ? body.start_date : null, isDate(body.end_date) ? body.end_date : null,
            str(body.venue) || null, str(body.source_url, 500), str(body.group_label), !!body.members_only]);
        void a;
        return send(200, { id: row!.id });
      }

      // ---- jobs
      if (route("GET", /^\/api\/jobs$/)) {
        needApproved();
        const where = ["(expires_at IS NULL OR expires_at >= current_date)"];
        const args: unknown[] = [];
        for (const k of ["speciality", "seniority"]) { const v = url.searchParams.get(k); if (v) { args.push(str(v)); where.push(`${k} = $${args.length}`); } }
        const q = url.searchParams.get("q");
        if (q) { args.push(`%${str(q, 60).replace(/[\\%_]/g, "\\$&")}%`); where.push(`(title ILIKE $${args.length} OR employer ILIKE $${args.length} OR location ILIKE $${args.length})`); }
        if (url.searchParams.get("remote") === "1") where.push("remote");
        return send(200, await query(`SELECT id, employer, title, location, speciality, seniority, remote, source_url, expires_at::text AS expires_at, created_at FROM ain_jobs WHERE ${where.join(" AND ")} ORDER BY id DESC`, args));
      }
      if ((r = route("POST", /^\/api\/jobs\/(\d+)\/click$/))) {
        const u = needApproved();
        const j = await one("SELECT source_url FROM ain_jobs WHERE id = $1", [r[1]]);
        if (!j) return fail("Job not found.", 404);
        await query("INSERT INTO ain_job_clicks (job_id, member_id) VALUES ($1,$2)", [r[1], u.id]);
        return send(200, { url: j.source_url });
      }
      if (route("POST", /^\/api\/admin\/jobs$/)) {
        const a = needAdmin();
        if (!str(body.employer) || !str(body.title) || !isUrl(str(body.source_url, 500))) return fail("Employer, title and the employer's own listing link are all needed.");
        const row = await one(`INSERT INTO ain_jobs (employer, title, location, speciality, seniority, remote, source_url, expires_at, posted_by) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id`,
          [str(body.employer), str(body.title), str(body.location), str(body.speciality), str(body.seniority), !!body.remote, str(body.source_url, 500), isDate(body.expires_at) ? body.expires_at : null, a.id]);
        return send(200, { id: row!.id });
      }
      if ((r = route("DELETE", /^\/api\/admin\/jobs\/(\d+)$/))) { needAdmin(); await query("DELETE FROM ain_jobs WHERE id = $1", [r[1]]); return send(200, ok); }

      // ---- resources
      if (route("GET", /^\/api\/resources$/)) { needApproved(); return send(200, await query("SELECT * FROM ain_resources ORDER BY id DESC")); }
      if (route("POST", /^\/api\/admin\/resources$/)) {
        needAdmin();
        if (!str(body.title) || !isUrl(str(body.url, 500))) return fail("Title and link are needed.");
        const row = await one("INSERT INTO ain_resources (title, kind, url, summary) VALUES ($1,$2,$3,$4) RETURNING id", [str(body.title), str(body.kind) || "Link", str(body.url, 500), str(body.summary, 500)]);
        return send(200, { id: row!.id });
      }
      if ((r = route("DELETE", /^\/api\/admin\/resources\/(\d+)$/))) { needAdmin(); await query("DELETE FROM ain_resources WHERE id = $1", [r[1]]); return send(200, ok); }

      // ---- directory (opt-in only)
      if (route("GET", /^\/api\/directory$/)) {
        needApproved();
        const where = ["status = 'approved'", "directory_visible"];
        const args: unknown[] = [];
        if (url.searchParams.get("mentoring") === "1") where.push("mentoring <> 'none'");
        const q = url.searchParams.get("q");
        if (q) { args.push(`%${str(q, 60).replace(/[\\%_]/g, "\\$&")}%`); where.push(`(name ILIKE $1 OR speciality ILIKE $1 OR region ILIKE $1)`); }
        return send(200, await query(`SELECT id, name, role_category, employer_type, speciality, region, mentoring FROM ain_members WHERE ${where.join(" AND ")} ORDER BY name`, args));
      }

      // ---- community
      if (route("GET", /^\/api\/channels$/)) {
        needApproved();
        return send(200, await query(`SELECT c.*, (SELECT COUNT(*)::int FROM ain_posts p WHERE p.channel_id = c.id AND p.parent_id IS NULL AND NOT p.hidden) AS threads FROM ain_channels c ORDER BY sort`));
      }
      const postCols = "p.id, p.parent_id, p.body, p.created_at, COALESCE(m.name, 'Former member') AS author, m.role_category AS author_role, p.member_id";
      if ((r = route("GET", /^\/api\/channels\/([a-z0-9-]+)\/posts$/))) {
        const u = needApproved();
        const c = await one("SELECT * FROM ain_channels WHERE slug = $1", [r[1]]);
        if (!c) return fail("Channel not found.", 404);
        const notBlocked = "(p.member_id IS NULL OR p.member_id NOT IN (SELECT blocked_id FROM ain_blocks WHERE blocker_id = $2))";
        const threads = await query(`SELECT ${postCols} FROM ain_posts p LEFT JOIN ain_members m ON m.id = p.member_id WHERE p.channel_id = $1 AND p.parent_id IS NULL AND NOT p.hidden AND ${notBlocked} ORDER BY p.id DESC LIMIT 100`, [c.id, u.id]);
        const replies = threads.length
          ? await query(`SELECT ${postCols} FROM ain_posts p LEFT JOIN ain_members m ON m.id = p.member_id WHERE p.parent_id = ANY($1::int[]) AND NOT p.hidden AND ${notBlocked} ORDER BY p.id`, [threads.map((t) => t.id), u.id])
          : [];
        return send(200, { channel: c, threads: threads.map((t) => ({ ...t, replies: replies.filter((x) => x.parent_id === t.id) })) });
      }
      if ((r = route("POST", /^\/api\/channels\/([a-z0-9-]+)\/posts$/))) {
        const u = needApproved();
        const c = await one("SELECT * FROM ain_channels WHERE slug = $1", [r[1]]);
        const text = str(body.body, 3000);
        if (!c) return fail("Channel not found.", 404);
        if (!text) return fail("Write something first.");
        let parent: Row | null = null;
        if (body.parent_id) {
          parent = await one("SELECT * FROM ain_posts WHERE id = $1 AND channel_id = $2 AND parent_id IS NULL AND NOT hidden", [Number(body.parent_id) || 0, c.id]);
          if (!parent) return fail("That thread is not available.", 404);
        }
        const row = await one("INSERT INTO ain_posts (channel_id, parent_id, member_id, body) VALUES ($1,$2,$3,$4) RETURNING id", [c.id, parent?.id ?? null, u.id, text]);
        if (parent && parent.member_id && parent.member_id !== u.id) await notify(parent.member_id, `${u.name} replied to your post in ${c.title}`, `/community/${c.slug}`);
        return send(200, { id: row!.id });
      }
      if ((r = route("DELETE", /^\/api\/posts\/(\d+)$/))) {
        const u = needApproved();
        const p = await one("SELECT * FROM ain_posts WHERE id = $1", [r[1]]);
        if (!p || (p.member_id !== u.id && !u.is_admin)) return fail("Not allowed.", 403);
        await query("UPDATE ain_posts SET hidden = true WHERE id = $1 OR parent_id = $1", [p.id]);
        return send(200, ok);
      }
      if ((r = route("POST", /^\/api\/posts\/(\d+)\/report$/))) {
        const u = needApproved();
        const p = await one("SELECT id FROM ain_posts WHERE id = $1 AND NOT hidden", [r[1]]);
        if (!p) return fail("Post not found.", 404);
        await query("INSERT INTO ain_reports (post_id, member_id, reason) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING", [p.id, u.id, str(body.reason, 300) || "No reason given"]);
        await notifyAdmins("A post was reported");
        return send(200, ok);
      }
      // Members can block anyone whose posts they do not want to see (required for apps with user-generated content).
      if ((r = route("POST", /^\/api\/members\/([0-9a-f-]{36})\/block$/))) {
        const u = needApproved();
        if (r[1] === u.id || !await one("SELECT 1 FROM ain_members WHERE id = $1", [r[1]])) return fail("Not allowed.", 400);
        await query("INSERT INTO ain_blocks (blocker_id, blocked_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", [u.id, r[1]]);
        await notifyAdmins("A member was blocked by another member");
        return send(200, ok);
      }

      // ---- admin
      if (route("GET", /^\/api\/admin\/pending$/)) {
        needAdmin();
        return send(200, await query("SELECT id, name, email, nmc_pin, role_category, employer_type, speciality, region, created_at FROM ain_members WHERE status = 'pending' ORDER BY created_at"));
      }
      if ((r = route("POST", /^\/api\/admin\/members\/([0-9a-f-]{36})\/decision$/))) {
        needAdmin();
        const approve = body.decision === "approve";
        const t = await one("SELECT * FROM ain_members WHERE id = $1", [r[1]]);
        if (!t) return fail("Member not found.", 404);
        await query("UPDATE ain_members SET status = $1, verified_at = $2 WHERE id = $3", [approve ? "approved" : "rejected", approve ? new Date().toISOString() : null, t.id]);
        if (approve) await notify(t.id, "Your membership is approved. Welcome.", "/");
        return send(200, ok);
      }
      if (route("GET", /^\/api\/admin\/reports$/)) {
        needAdmin();
        return send(200, await query(`SELECT r.id, r.reason, r.created_at, p.id AS post_id, p.body, p.hidden, COALESCE(m.name, 'Former member') AS author
          FROM ain_reports r JOIN ain_posts p ON p.id = r.post_id LEFT JOIN ain_members m ON m.id = p.member_id WHERE NOT r.resolved ORDER BY r.id`));
      }
      if ((r = route("POST", /^\/api\/admin\/reports\/(\d+)\/resolve$/))) {
        needAdmin();
        const rep = await one("SELECT * FROM ain_reports WHERE id = $1", [r[1]]);
        if (!rep) return fail("Report not found.", 404);
        if (body.hide) await query("UPDATE ain_posts SET hidden = true WHERE id = $1 OR parent_id = $1", [rep.post_id]);
        await query("UPDATE ain_reports SET resolved = true WHERE post_id = $1", [rep.post_id]);
        return send(200, ok);
      }
      if (route("GET", /^\/api\/admin\/stats$/)) {
        needAdmin();
        const c = async (sql: string) => (await one(sql))!.c as number;
        return send(200, {
          approved_members: await c("SELECT COUNT(*)::int c FROM ain_members WHERE status = 'approved'"),
          pending_members: await c("SELECT COUNT(*)::int c FROM ain_members WHERE status = 'pending'"),
          joined_last_7_days: await c("SELECT COUNT(*)::int c FROM ain_members WHERE created_at >= now() - interval '7 days'"),
          active_last_7_days: await c(`SELECT COUNT(DISTINCT member_id)::int c FROM (SELECT member_id FROM ain_posts WHERE created_at >= now() - interval '7 days' UNION ALL SELECT member_id FROM ain_job_clicks WHERE created_at >= now() - interval '7 days') x`),
          profiles_in_directory: await c("SELECT COUNT(*)::int c FROM ain_members WHERE directory_visible"),
          event_saves: await c("SELECT COUNT(*)::int c FROM ain_event_saves"),
          job_clicks: await c("SELECT COUNT(*)::int c FROM ain_job_clicks"),
          by_employer_type: await query("SELECT employer_type AS label, COUNT(*)::int AS n FROM ain_members WHERE status = 'approved' GROUP BY employer_type ORDER BY n DESC"),
          by_role: await query("SELECT role_category AS label, COUNT(*)::int AS n FROM ain_members WHERE status = 'approved' GROUP BY role_category ORDER BY n DESC"),
        });
      }

      return fail("Not found.", 404);
    } catch (e) {
      if (e instanceof HttpError) return send(e.code, { error: e.message });
      console.error(e);
      return send(500, { error: "Something went wrong. Try again." });
    }
  };
}

const pub = (m: Row): Row => {
  const { id, name, email, role_category, employer_type, speciality, region, directory_visible, mentoring, email_notifications, status, is_admin } = m;
  return { id, name, email, role_category, employer_type, speciality, region, directory_visible, mentoring, email_notifications, status, is_admin };
};
