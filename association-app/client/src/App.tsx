import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { api, type EventItem, type Member } from './api';

const ASSOC_URL = 'https://medsalesintelligencehub.co.uk/association-for-industry-professional-nurses/';

function useRoute() {
  const get = () => (location.hash.replace(/^#/, '') || '/');
  const [path, setPath] = useState(get);
  useEffect(() => {
    const f = () => { setPath(get()); window.scrollTo(0, 0); };
    window.addEventListener('hashchange', f);
    return () => window.removeEventListener('hashchange', f);
  }, []);
  return path;
}
const go = (p: string) => { location.hash = p; };

interface Session { member: Member | null; unread: number }

export function App() {
  const path = useRoute();
  const [session, setSession] = useState<Session | null>(null);
  const refresh = useCallback(() => api<Session>('GET', '/api/me').then(setSession).catch(() => setSession({ member: null, unread: 0 })), []);
  useEffect(() => { refresh(); }, [refresh, path]);
  if (!session) return <div className="wrap" style={{ padding: 40 }}>Loading…</div>;
  const m = session.member;
  const approved = m?.status === 'approved';

  let page: ReactNode;
  const seg = path.split('/').filter(Boolean);
  if (seg[0] === 'verify') page = <Verify token={seg[1]} onDone={() => { refresh(); go('/'); }} />;
  else if (seg[0] === 'join') page = <Join />;
  else if (seg[0] === 'signin') page = <SignIn />;
  else if (seg[0] === 'events') page = <Events member={m} />;
  else if (!m) page = <Landing />;
  else if (seg[0] === 'me') page = <Profile member={m} onChange={refresh} />;
  else if (m.status !== 'approved') page = <Pending member={m} />;
  else if (seg[0] === 'jobs') page = <Jobs />;
  else if (seg[0] === 'community') page = <Community slug={seg[1]} member={m} />;
  else if (seg[0] === 'people') page = <People />;
  else if (seg[0] === 'resources') page = <Resources />;
  else if (seg[0] === 'notifications') page = <Notifications onRead={refresh} />;
  else if (seg[0] === 'admin' && m.is_admin) page = <Admin />;
  else page = <Home member={m} />;

  const links: [string, string][] = approved
    ? [['/', 'Home'], ['/events', 'Events'], ['/jobs', 'Jobs'], ['/community', 'Community'], ['/people', 'People'], ['/resources', 'Resources']]
    : [['/', 'Home'], ['/events', 'Events']];
  const on = (p: string) => (p === '/' ? path === '/' : path.startsWith(p));
  return (
    <>
      <header className="top">
        <div className="wrap">
          <a className="brand" href="#/"><small>Association for</small>Industry Professional Nurses</a>
          <nav className="nav" aria-label="Main">
            {links.map(([p, l]) => <a key={p} href={'#' + p} className={on(p) ? 'on' : ''}>{l}</a>)}
            {m?.is_admin && <a href="#/admin" className={on('/admin') ? 'on' : ''}>Admin</a>}
          </nav>
          <div className="row">
            {m ? (<>
              <a className="bell" href="#/notifications" aria-label={`Notifications, ${session.unread} unread`}>Alerts{session.unread > 0 && <b>{session.unread}</b>}</a>
              <a className="btn ghost small" href="#/me">Me</a>
            </>) : (<>
              <a className="btn ghost small" href="#/signin">Sign in</a>
              <a className="btn small" href="#/join">Join free</a>
            </>)}
          </div>
        </div>
      </header>
      <main>{page}</main>
      <footer className="foot"><div className="wrap">
        <a href={ASSOC_URL}>About the Association</a> · Membership is free · Events and links are as published by each organiser; confirm on the source before you book.
      </div></footer>
      {m && (
        <nav className="tabbar" aria-label="Main">
          {(approved ? [...links.slice(0, 5), ...(m.is_admin ? [['/admin', 'Admin'] as [string, string]] : [])] : links).map(([p, l]) => <a key={p} href={'#' + p} className={on(p) ? 'on' : ''}>{l}</a>)}
        </nav>
      )}
    </>
  );
}

function Err({ text }: { text: string }) { return text ? <div className="err" role="alert">{text}</div> : null; }

function useAction() {
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const run = async (fn: () => Promise<unknown>) => {
    setErr(''); setBusy(true);
    try { await fn(); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };
  return { err, busy, run, setErr };
}

/* ---------- public ---------- */
function Landing() {
  return (<>
    <section className="band hero"><div className="wrap">
      <span className="tag">Free to join</span>
      <h1>The network for nurses working in industry</h1>
      <hr className="rule" />
      <p className="lede">Meet peers, find roles, keep track of the conferences that matter, and get advice from nurses who have made the move from the NHS into medical device, pharmaceutical and diagnostics companies.</p>
      <a className="btn" href="#/join">Join the Association</a>
      <a className="btn ghost" href="#/events">See the conferences</a>
    </div></section>
    <section className="band wine"><div className="wrap">
      <h2>What members get</h2>
      <div className="grid g3">
        <div className="card"><h3>Community</h3><p>Channels for moving into industry, clinical education, field roles and compliance. Reply, ask, and find a mentor.</p></div>
        <div className="card"><h3>Jobs</h3><p>Roles for nurses in industry, each linked to the employer's own listing.</p></div>
        <div className="card"><h3>Events</h3><p>Conferences and meetings in one diary, with a calendar file for every dated event.</p></div>
      </div>
    </div></section>
    <section className="band navy2"><div className="wrap" style={{ textAlign: 'center' }}>
      <h2>Membership is checked</h2>
      <p className="lede">We ask for your Nursing and Midwifery Council (NMC) registration number (PIN) and approve each member by hand, so the community stays nurses-only.</p>
      <a className="btn" href="#/join">Join free</a>
    </div></section>
  </>);
}

function Join() {
  const [opts, setOpts] = useState<{ roles: string[]; employers: string[] }>({ roles: [], employers: [] });
  const [f, setF] = useState<any>({ email: '', name: '', nmc_pin: '', role_category: '', employer_type: '', speciality: '', region: '', consent: false });
  const [link, setLink] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const { err, busy, run } = useAction();
  useEffect(() => { api('GET', '/api/options').then(setOpts); }, []);
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
  const submit = (e: FormEvent) => { e.preventDefault(); run(async () => { const r = await api('POST', '/api/auth/signup', f); setLink(r.devLink || null); setSent(true); }); };
  if (sent) return (<div className="wrap page-head"><h1>Check your email</h1>
    <div className="ok">We've sent a sign-in link to {f.email}. It works once and lasts 15 minutes. After you sign in, your membership waits for approval; we'll alert you when it's done.</div>
    {link && <p className="hint">Mail is not connected yet. Test sign-in link: <a href={link}>{link}</a></p>}</div>);
  return (<div className="wrap page-head" style={{ maxWidth: 640 }}>
    <span className="tag">Join free</span><h1>Join the Association</h1>
    <p>Membership is free for nurses in industry and nurses moving into industry.</p>
    <form onSubmit={submit}>
      <label htmlFor="n">Full name</label><input id="n" value={f.name} onChange={set('name')} autoComplete="name" required />
      <label htmlFor="e">Email</label><input id="e" type="email" value={f.email} onChange={set('email')} autoComplete="email" required />
      <label htmlFor="p">Nursing and Midwifery Council (NMC) registration number (PIN)</label>
      <input id="p" value={f.nmc_pin} onChange={set('nmc_pin')} placeholder="12A3456E" maxLength={8} required />
      <p className="hint">Used only to check you are on the register. Nobody else sees it.</p>
      <label htmlFor="r">Your role</label>
      <select id="r" value={f.role_category} onChange={set('role_category')} required><option value="">Choose…</option>{opts.roles.map((r) => <option key={r}>{r}</option>)}</select>
      <label htmlFor="t">Where do you work?</label>
      <select id="t" value={f.employer_type} onChange={set('employer_type')} required><option value="">Choose…</option>{opts.employers.map((r) => <option key={r}>{r}</option>)}</select>
      <label htmlFor="s">Speciality (optional)</label><input id="s" value={f.speciality} onChange={set('speciality')} placeholder="e.g. wound care, diabetes" />
      <label htmlFor="g">Region (optional)</label><input id="g" value={f.region} onChange={set('region')} placeholder="e.g. North West" />
      <p />
      <label className="check"><input type="checkbox" checked={f.consent} onChange={set('consent')} required />
        <span>I agree that the Association may store these details to run my membership. I can export or delete them at any time from my profile.</span></label>
      <Err text={err} />
      <button className="btn" disabled={busy}>{busy ? 'Joining…' : 'Join'}</button>
      <a className="btn ghost" href="#/signin">Already a member?</a>
    </form></div>);
}

function SignIn() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [link, setLink] = useState<string | null>(null);
  const { err, busy, run } = useAction();
  const submit = (e: FormEvent) => { e.preventDefault(); run(async () => { const r = await api('POST', '/api/auth/request', { email }); setLink(r.devLink || null); setSent(true); }); };
  return (<div className="wrap page-head" style={{ maxWidth: 560 }}>
    <h1>Sign in</h1>
    {sent ? <div className="ok">If that email is registered, a sign-in link is on its way. It lasts 15 minutes.</div> : (
      <form onSubmit={submit}><label htmlFor="e">Email</label><input id="e" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        <Err text={err} /><button className="btn" disabled={busy}>Email me a sign-in link</button></form>)}
    {link && <p className="hint">Mail is not connected yet. Test sign-in link: <a href={link}>{link}</a></p>}
  </div>);
}

function Verify({ token, onDone }: { token: string; onDone: () => void }) {
  const { err, run } = useAction();
  useEffect(() => { run(async () => { await api('POST', '/api/auth/verify', { token }); onDone(); }); }, []); // eslint-disable-line
  return <div className="wrap page-head"><h1>Signing you in…</h1><Err text={err} />{err && <a className="btn" href="#/signin">Get a new link</a>}</div>;
}

function Pending({ member }: { member: Member }) {
  return (<div className="wrap page-head"><span className="tag">Almost there</span><h1>Welcome, {member.name.split(' ')[0]}</h1>
    <div className="ok">Your membership is {member.status === 'rejected' ? 'not approved. Email contact@elevateandthrive.uk if you think this is a mistake.' : 'waiting for approval. We check each registration number by hand, so it can take a little while. We\'ll alert you here and by email.'}</div>
    <p>In the meantime you can browse the <a href="#/events">conferences and events</a> and complete your <a href="#/me">profile</a>.</p></div>);
}

/* ---------- member pages ---------- */
function Home({ member }: { member: Member }) {
  const [events, setEvents] = useState<EventItem[]>([]);
  useEffect(() => { api<EventItem[]>('GET', '/api/events').then((e) => setEvents(e.filter((x) => x.start_date && x.start_date >= new Date().toISOString().slice(0, 10)).slice(0, 3))); }, []);
  const cards: [string, string, string][] = [['/community', 'Community', 'Ask a question or reply to a colleague.'], ['/jobs', 'Jobs', 'Roles for nurses in industry.'], ['/people', 'People', 'Find peers and mentors.'], ['/resources', 'Resources', 'Guides and links from the Association.']];
  return (<>
    <section className="band hero"><div className="wrap"><span className="tag">Member area</span><h1>Hello, {member.name.split(' ')[0]}</h1><hr className="rule" /><p className="lede">Your network for nursing in industry.</p></div></section>
    <div className="wrap"><div className="grid g2">{cards.map(([p, t, d]) => <a key={p} href={'#' + p} className="card" style={{ textDecoration: 'none' }}><h3>{t}</h3><p style={{ color: 'var(--ink)' }}>{d}</p></a>)}</div>
      <h2>Coming up</h2><div className="grid g3">{events.map((e) => <EventCard key={e.id} e={e} member={member} />)}</div>
      <p><a className="btn ghost" href="#/events">All events</a></p></div>
  </>);
}

const fmt = (d: string) => new Date(d + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
function dateLabel(e: EventItem) {
  if (!e.start_date) return 'Date not confirmed';
  return e.end_date && e.end_date !== e.start_date ? `${fmt(e.start_date)} to ${fmt(e.end_date)}` : fmt(e.start_date);
}
function EventCard({ e, member, onToggle }: { e: EventItem; member: Member | null; onToggle?: () => void }) {
  const { err, run } = useAction();
  const toggle = () => run(async () => { await api(e.saved ? 'DELETE' : 'POST', `/api/events/${e.id}/save`); onToggle?.(); });
  return (<article className="card">
    <span className={'date' + (e.start_date ? '' : ' tbc')}>{dateLabel(e)}</span>
    <h3>{e.title}</h3>
    {e.organiser && <p className="meta">{e.organiser}</p>}
    <p>{e.detail}</p>
    {e.members_only && <span className="pill">Members only</span>}
    <p className="meta">Checked {fmt(e.verified_at.slice(0, 10))}</p>
    <Err text={err} />
    <div className="row">
      <a className="btn small" href={e.source_url} target="_blank" rel="noopener noreferrer">{e.source_label}</a>
      {member && <button className="btn ghost small" onClick={toggle} aria-pressed={e.saved}>{e.saved ? 'Saved ✓' : 'Save'}</button>}
      {e.start_date && <a className="btn ghost small" href={`/api/events/${e.id}.ics`}>Add to calendar</a>}
    </div>
  </article>);
}
function Events({ member }: { member: Member | null }) {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [saved, setSaved] = useState(false);
  const load = useCallback(() => api<EventItem[]>('GET', '/api/events').then(setEvents), []);
  useEffect(() => { load(); }, [load]);
  const shown = events.filter((e) => !saved || e.saved);
  const groups = [...new Set(shown.map((e) => e.group_label))];
  return (<div className="wrap"><div className="page-head"><span className="tag">Conferences</span><h1>Events for nurses in industry</h1>
    <p>Dates and venues are as published by each organiser. Some meetings are for members or invited guests only; check the organiser before you book.</p>
    {member && <label className="check"><input type="checkbox" checked={saved} onChange={(e) => setSaved(e.target.checked)} /> Show only my saved events</label>}</div>
    {groups.map((g) => (<section key={g}><h2 className="group">{g}</h2><div className="grid g2">{shown.filter((e) => e.group_label === g).map((e) => <EventCard key={e.id} e={e} member={member} onToggle={load} />)}</div></section>))}
    {!shown.length && <p>No events to show.</p>}
    {!member && <p><a className="btn" href="#/join">Join free to save events</a></p>}
  </div>);
}

function Jobs() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [q, setQ] = useState('');
  const [remote, setRemote] = useState(false);
  const { err, run } = useAction();
  useEffect(() => { api('GET', `/api/jobs?q=${encodeURIComponent(q)}${remote ? '&remote=1' : ''}`).then(setJobs).catch(() => {}); }, [q, remote]);
  const apply = (j: any) => run(async () => { const r = await api('POST', `/api/jobs/${j.id}/click`); window.open(r.url, '_blank', 'noopener,noreferrer'); });
  return (<div className="wrap"><div className="page-head"><span className="tag">Jobs</span><h1>Roles for nurses in industry</h1>
    <p>Each role links to the employer's own listing. Apply there.</p>
    <div className="row"><div className="grow"><label htmlFor="q" className="hint">Search title, employer or place</label><input id="q" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      <label className="check"><input type="checkbox" checked={remote} onChange={(e) => setRemote(e.target.checked)} /> Remote or home-based</label></div></div>
    <Err text={err} />
    <div className="grid g2">{jobs.map((j) => (<article key={j.id} className="card"><h3>{j.title}</h3><p className="meta">{j.employer}{j.location && ` · ${j.location}`}</p>
      {j.remote && <span className="pill">Remote</span>}{j.speciality && <span className="pill">{j.speciality}</span>}{j.seniority && <span className="pill">{j.seniority}</span>}
      {j.expires_at && <p className="meta">Closes {fmt(j.expires_at)}</p>}<button className="btn small" onClick={() => apply(j)}>View on employer site</button></article>))}</div>
    {!jobs.length && <div className="card plain"><p>No roles listed yet. We're adding employers soon. Check back, or ask in <a href="#/community">Community</a>.</p></div>}
  </div>);
}

function Community({ slug, member }: { slug?: string; member: Member }) {
  const [channels, setChannels] = useState<any[]>([]);
  useEffect(() => { if (!slug) api('GET', '/api/channels').then(setChannels); }, [slug]);
  if (slug) return <Channel slug={slug} member={member} />;
  return (<div className="wrap"><div className="page-head"><span className="tag">Community</span><h1>Channels</h1>
    <p>Be kind, be professional. Never share patient-identifiable information, and do not post confidential employer information.</p></div>
    <div className="grid g2">{channels.map((c) => <a key={c.id} href={`#/community/${c.slug}`} className="card" style={{ textDecoration: 'none' }}><h3>{c.title}</h3><p style={{ color: 'var(--ink)' }}>{c.description}</p><p className="meta">{c.threads} {c.threads === 1 ? 'thread' : 'threads'}</p></a>)}</div></div>);
}
function Channel({ slug, member }: { slug: string; member: Member }) {
  const [data, setData] = useState<any>(null);
  const [body, setBody] = useState('');
  const [reply, setReply] = useState<{ id: number; text: string } | null>(null);
  const [note, setNote] = useState('');
  const { err, busy, run } = useAction();
  const load = useCallback(() => api('GET', `/api/channels/${slug}/posts`).then(setData), [slug]);
  useEffect(() => { load(); }, [load]);
  if (!data) return <div className="wrap page-head"><Err text={err} />Loading…</div>;
  const post = (parent_id?: number, text?: string) => run(async () => { await api('POST', `/api/channels/${slug}/posts`, { body: text ?? body, parent_id }); setBody(''); setReply(null); await load(); });
  const report = (id: number) => { const reason = prompt('Why are you reporting this post?') || ''; run(async () => { await api('POST', `/api/posts/${id}/report`, { reason }); setNote('Thank you. An admin will look at it.'); }); };
  const remove = (id: number) => { if (confirm('Delete this post?')) run(async () => { await api('DELETE', `/api/posts/${id}`); await load(); }); };
  const Actions = ({ p }: { p: any }) => (<span className="row" style={{ gap: 6 }}>
    {p.member_id === member.id || member.is_admin ? <button className="btn danger small" onClick={() => remove(p.id)}>Delete</button> : <button className="btn ghost small" onClick={() => report(p.id)}>Report</button>}</span>);
  return (<div className="wrap"><div className="page-head"><a href="#/community">← All channels</a><h1>{data.channel.title}</h1><p>{data.channel.description}</p></div>
    <div className="card plain"><label htmlFor="b">Start a thread</label><textarea id="b" rows={3} value={body} onChange={(e) => setBody(e.target.value)} />
      <p className="hint">Do not include patient details or confidential employer information.</p><Err text={err} />{note && <div className="ok">{note}</div>}
      <button className="btn" disabled={busy || !body.trim()} onClick={() => post()}>Post</button></div>
    {data.threads.map((t: any) => (<div key={t.id} className="thread"><p><span className="who">{t.author}</span> <span className="meta hint">· {t.author_role} · {new Date(t.created_at + 'Z').toLocaleDateString('en-GB')}</span></p><p style={{ whiteSpace: 'pre-wrap' }}>{t.body}</p>
      <div className="row"><button className="btn ghost small" onClick={() => setReply({ id: t.id, text: '' })}>Reply</button><Actions p={t} /></div>
      {t.replies.map((r: any) => (<div key={r.id} className="reply"><p><span className="who">{r.author}</span> <span className="hint">· {r.author_role}</span></p><p style={{ whiteSpace: 'pre-wrap' }}>{r.body}</p><Actions p={r} /></div>))}
      {reply && reply.id === t.id && (<div className="reply"><label htmlFor={'r' + t.id}>Your reply</label><textarea id={'r' + t.id} rows={2} value={reply.text} onChange={(e) => setReply({ id: t.id, text: e.target.value })} />
        <button className="btn small" disabled={busy || !reply.text.trim()} onClick={() => post(t.id, reply.text)}>Send reply</button></div>)}
    </div>))}
    {!data.threads.length && <p>No threads yet. Be the first.</p>}</div>);
}

function People() {
  const [people, setPeople] = useState<any[]>([]);
  const [q, setQ] = useState('');
  const [mentors, setMentors] = useState(false);
  useEffect(() => { api('GET', `/api/directory?q=${encodeURIComponent(q)}${mentors ? '&mentoring=1' : ''}`).then(setPeople); }, [q, mentors]);
  const label: Record<string, string> = { mentor: 'Offers mentoring', mentee: 'Looking for a mentor', both: 'Mentor and mentee' };
  return (<div className="wrap"><div className="page-head"><span className="tag">People</span><h1>Member directory</h1>
    <p>Only members who have chosen to appear are listed. Switch yourself on in <a href="#/me">your profile</a>. To get in touch, use the community channels.</p>
    <div className="row"><div className="grow"><label htmlFor="q" className="hint">Search name, speciality or region</label><input id="q" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      <label className="check"><input type="checkbox" checked={mentors} onChange={(e) => setMentors(e.target.checked)} /> Mentoring only</label></div></div>
    <div className="grid g3">{people.map((p) => (<article key={p.id} className="card"><h3>{p.name}</h3><p className="meta">{p.role_category}<br />{p.employer_type}</p>
      {p.speciality && <span className="pill">{p.speciality}</span>}{p.region && <span className="pill">{p.region}</span>}{label[p.mentoring] && <span className="pill">{label[p.mentoring]}</span>}</article>))}</div>
    {!people.length && <div className="card plain"><p>No one matches yet.</p></div>}</div>);
}

function Resources() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { api('GET', '/api/resources').then(setItems); }, []);
  return (<div className="wrap"><div className="page-head"><span className="tag">Resources</span><h1>Guides and links</h1></div>
    <div className="grid g2">{items.map((r) => (<article key={r.id} className="card"><span className="pill">{r.kind}</span><h3>{r.title}</h3><p>{r.summary}</p><a className="btn small" href={r.url} target="_blank" rel="noopener noreferrer">Open</a></article>))}</div></div>);
}

function Notifications({ onRead }: { onRead: () => void }) {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { api('GET', '/api/notifications').then(setItems).then(() => api('POST', '/api/notifications/read')).then(onRead); }, []); // eslint-disable-line
  return (<div className="wrap"><div className="page-head"><h1>Alerts</h1></div>
    {items.map((n) => <div key={n.id} className="card plain" style={{ marginBottom: 10 }}><p><a href={'#' + (n.link || '/')}>{n.text}</a></p><p className="meta">{new Date(n.created_at + 'Z').toLocaleString('en-GB')}</p></div>)}
    {!items.length && <p>Nothing yet.</p>}</div>);
}

function Profile({ member, onChange }: { member: Member; onChange: () => void }) {
  const [f, setF] = useState<any>(member);
  const [opts, setOpts] = useState<{ roles: string[]; employers: string[] }>({ roles: [], employers: [] });
  const [saved, setSaved] = useState(false);
  const { err, busy, run } = useAction();
  useEffect(() => { api('GET', '/api/options').then(setOpts); }, []);
  const set = (k: string) => (e: any) => { setSaved(false); setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }); };
  const save = (e: FormEvent) => { e.preventDefault(); run(async () => { await api('PATCH', '/api/me', f); setSaved(true); onChange(); }); };
  const exportData = () => run(async () => {
    const d = await api('GET', '/api/me/export');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' })); a.download = 'my-association-data.json'; a.click();
  });
  const del = () => { if (confirm('Delete your account and personal details? This cannot be undone.')) run(async () => { await api('DELETE', '/api/me'); onChange(); go('/'); }); };
  const out = () => run(async () => { await api('POST', '/api/auth/logout'); onChange(); go('/'); });
  return (<div className="wrap page-head" style={{ maxWidth: 680 }}><h1>My profile</h1>
    <form onSubmit={save}>
      <label htmlFor="n">Name</label><input id="n" value={f.name} onChange={set('name')} />
      <label htmlFor="r">Role</label><select id="r" value={f.role_category} onChange={set('role_category')}>{opts.roles.map((r) => <option key={r}>{r}</option>)}</select>
      <label htmlFor="t">Where do you work?</label><select id="t" value={f.employer_type} onChange={set('employer_type')}>{opts.employers.map((r) => <option key={r}>{r}</option>)}</select>
      <label htmlFor="s">Speciality</label><input id="s" value={f.speciality} onChange={set('speciality')} />
      <label htmlFor="g">Region</label><input id="g" value={f.region} onChange={set('region')} />
      <label htmlFor="m">Mentoring</label><select id="m" value={f.mentoring} onChange={set('mentoring')}><option value="none">Not now</option><option value="mentor">I can mentor</option><option value="mentee">I'd like a mentor</option><option value="both">Both</option></select>
      <p /><label className="check"><input type="checkbox" checked={f.directory_visible} onChange={set('directory_visible')} /><span>Show me in the member directory (name, role, employer type, speciality, region). Your email and registration number are never shown.</span></label>
      <label className="check"><input type="checkbox" checked={f.email_notifications} onChange={set('email_notifications')} /><span>Email me about replies and approvals</span></label>
      <Err text={err} />{saved && <div className="ok">Saved.</div>}
      <button className="btn" disabled={busy}>Save</button>
    </form>
    <hr style={{ borderColor: 'var(--line)', margin: '28px 0' }} />
    <div className="row"><button className="btn ghost" onClick={exportData}>Download my data</button><button className="btn ghost" onClick={out}>Sign out</button><button className="btn danger" onClick={del}>Delete my account</button></div>
  </div>);
}

/* ---------- admin ---------- */
function Admin() {
  const [pending, setPending] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const { err, run } = useAction();
  const load = useCallback(() => {
    api('GET', '/api/admin/pending').then(setPending); api('GET', '/api/admin/reports').then(setReports); api('GET', '/api/admin/stats').then(setStats);
  }, []);
  useEffect(() => { load(); }, [load]);
  const decide = (id: number, decision: string) => run(async () => { await api('POST', `/api/admin/members/${id}/decision`, { decision }); load(); });
  const resolve = (id: number, hide: boolean) => run(async () => { await api('POST', `/api/admin/reports/${id}/resolve`, { hide }); load(); });
  return (<div className="wrap"><div className="page-head"><span className="tag">Admin</span><h1>Admin</h1></div><Err text={err} />
    {stats && <div className="grid g3">{([['Approved members', stats.approved_members], ['Waiting', stats.pending_members], ['Joined, last 7 days', stats.joined_last_7_days], ['Active, last 7 days', stats.active_last_7_days], ['In directory', stats.profiles_in_directory], ['Event saves', stats.event_saves], ['Job clicks', stats.job_clicks]] as [string, number][]).map(([l, n]) => <div key={l} className="card"><div className="stat">{n}</div><p className="meta">{l}</p></div>)}</div>}
    <h2>Approve members</h2>
    <p className="hint">Check each registration number on the Nursing and Midwifery Council (NMC) register before approving.</p>
    {pending.map((p) => (<div key={p.id} className="card plain" style={{ marginBottom: 12 }}><h3>{p.name}</h3><p>{p.email} · PIN <b>{p.nmc_pin}</b></p><p className="meta">{p.role_category} · {p.employer_type}{p.region && ` · ${p.region}`}</p>
      <div className="row"><button className="btn small" onClick={() => decide(p.id, 'approve')}>Approve</button><button className="btn danger small" onClick={() => decide(p.id, 'reject')}>Reject</button></div></div>))}
    {!pending.length && <p>No one waiting.</p>}
    <h2>Reported posts</h2>
    {reports.map((r) => (<div key={r.id} className="card plain" style={{ marginBottom: 12 }}><p><b>{r.author}</b>: {r.body}</p><p className="meta">Reason: {r.reason}</p>
      <div className="row"><button className="btn danger small" onClick={() => resolve(r.id, true)}>Hide post</button><button className="btn ghost small" onClick={() => resolve(r.id, false)}>Dismiss</button></div></div>))}
    {!reports.length && <p>No reports.</p>}
    <AddForms onDone={load} />
    {stats && <><h2>Who is joining</h2><div className="grid g2">
      <table><thead><tr><th>Employer type</th><th>Members</th></tr></thead><tbody>{stats.by_employer_type.map((x: any) => <tr key={x.label}><td>{x.label}</td><td>{x.n}</td></tr>)}</tbody></table>
      <table><thead><tr><th>Role</th><th>Members</th></tr></thead><tbody>{stats.by_role.map((x: any) => <tr key={x.label}><td>{x.label}</td><td>{x.n}</td></tr>)}</tbody></table></div>
      <p className="hint">Self-declared by members who joined. This is not a count of all nurses in industry.</p></>}
  </div>);
}

function AddForms({ onDone }: { onDone: () => void }) {
  const blank = { job: { employer: '', title: '', location: '', speciality: '', seniority: '', source_url: '', expires_at: '', remote: false }, res: { title: '', kind: 'Link', url: '', summary: '' }, ev: { title: '', organiser: '', detail: '', start_date: '', end_date: '', venue: '', source_url: '', group_label: '' } };
  const [job, setJob] = useState<any>(blank.job);
  const [res, setRes] = useState<any>(blank.res);
  const [ev, setEv] = useState<any>(blank.ev);
  const [done, setDone] = useState('');
  const { err, run } = useAction();
  const send = (path: string, body: any, reset: () => void, text: string) => (e: FormEvent) => { e.preventDefault(); run(async () => { await api('POST', path, body); reset(); setDone(text); onDone(); }); };
  const field = (o: any, set: (v: any) => void, k: string, label: string, type = 'text') => (<><label htmlFor={'f' + k + label}>{label}</label><input id={'f' + k + label} type={type} value={o[k]} onChange={(e) => set({ ...o, [k]: e.target.value })} /></>);
  return (<><h2>Add content</h2><Err text={err} />{done && <div className="ok">{done}</div>}
    <div className="grid g3">
      <form className="card plain" onSubmit={send('/api/admin/jobs', job, () => setJob(blank.job), 'Job added.')}><h3>Job</h3>
        {field(job, setJob, 'employer', 'Employer')}{field(job, setJob, 'title', 'Title')}{field(job, setJob, 'location', 'Location')}{field(job, setJob, 'speciality', 'Speciality')}{field(job, setJob, 'source_url', "Employer's own listing link", 'url')}{field(job, setJob, 'expires_at', 'Closing date', 'date')}
        <label className="check"><input type="checkbox" checked={job.remote} onChange={(e) => setJob({ ...job, remote: e.target.checked })} /> Remote</label><button className="btn small">Add job</button></form>
      <form className="card plain" onSubmit={send('/api/admin/events', ev, () => setEv(blank.ev), 'Event added.')}><h3>Event</h3>
        {field(ev, setEv, 'title', 'Title')}{field(ev, setEv, 'organiser', 'Organiser')}{field(ev, setEv, 'start_date', 'Start (leave empty if not confirmed)', 'date')}{field(ev, setEv, 'end_date', 'End', 'date')}{field(ev, setEv, 'venue', 'Venue')}{field(ev, setEv, 'source_url', 'Organiser link', 'url')}{field(ev, setEv, 'group_label', 'Group heading')}
        <label htmlFor="evd">Details</label><textarea id="evd" rows={2} value={ev.detail} onChange={(e) => setEv({ ...ev, detail: e.target.value })} /><button className="btn small">Add event</button></form>
      <form className="card plain" onSubmit={send('/api/admin/resources', res, () => setRes(blank.res), 'Resource added.')}><h3>Resource</h3>
        {field(res, setRes, 'title', 'Title')}{field(res, setRes, 'kind', 'Type (Guide, Template, Video)')}{field(res, setRes, 'url', 'Link', 'url')}
        <label htmlFor="rs">Summary</label><textarea id="rs" rows={2} value={res.summary} onChange={(e) => setRes({ ...res, summary: e.target.value })} /><button className="btn small">Add resource</button></form>
    </div></>);
}
