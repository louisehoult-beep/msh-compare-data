-- Association for Industry Professional Nurses app. Added 26/10/2026.
-- Replaces the Node + SQLite server. Members are Supabase Auth users (email code
-- sign-in); every table is ain_*. Row-level security is ON with no policies, so
-- the public API (anon/authenticated keys) can read and write nothing: only the
-- `industrynurses` edge function, which connects as the database owner, touches
-- these tables, and it applies the membership rules itself.

create table public.ain_members (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  name text not null,
  nmc_pin text not null,
  role_category text not null,
  employer_type text not null,
  speciality text not null default '',
  region text not null default '',
  directory_visible boolean not null default false,
  mentoring text not null default 'none' check (mentoring in ('none','mentor','mentee','both')),
  email_notifications boolean not null default true,
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  is_admin boolean not null default false,
  verified_at timestamptz,
  consent_at timestamptz not null,
  created_at timestamptz not null default now()
);

create table public.ain_blocks (
  blocker_id uuid not null references public.ain_members(id) on delete cascade,
  blocked_id uuid not null references public.ain_members(id) on delete cascade,
  primary key (blocker_id, blocked_id)
);

create table public.ain_channels (
  id integer generated always as identity primary key,
  slug text not null unique, title text not null, description text not null, sort integer not null default 0
);

-- member_id becomes null when the author deletes their account (post text is blanked first).
create table public.ain_posts (
  id integer generated always as identity primary key,
  channel_id integer not null references public.ain_channels(id),
  parent_id integer references public.ain_posts(id),
  member_id uuid references public.ain_members(id) on delete set null,
  body text not null, hidden boolean not null default false, created_at timestamptz not null default now()
);
create index ain_posts_channel on public.ain_posts (channel_id, parent_id);

create table public.ain_reports (
  id integer generated always as identity primary key,
  post_id integer not null references public.ain_posts(id) on delete cascade,
  member_id uuid not null references public.ain_members(id) on delete cascade,
  reason text not null, resolved boolean not null default false, created_at timestamptz not null default now(),
  unique (post_id, member_id)
);

create table public.ain_events (
  id integer generated always as identity primary key,
  title text not null, organiser text not null default '', detail text not null default '',
  start_date date, end_date date, venue text, source_url text not null,
  source_label text not null default 'Visit the organiser', group_label text not null default '',
  members_only boolean not null default false, verified_at date not null
);

create table public.ain_event_saves (
  event_id integer not null references public.ain_events(id) on delete cascade,
  member_id uuid not null references public.ain_members(id) on delete cascade,
  primary key (event_id, member_id)
);

create table public.ain_jobs (
  id integer generated always as identity primary key,
  employer text not null, title text not null, location text not null default '',
  speciality text not null default '', seniority text not null default '', remote boolean not null default false,
  source_url text not null, expires_at date,
  posted_by uuid references public.ain_members(id) on delete set null,
  created_at timestamptz not null default now()
);

create table public.ain_job_clicks (
  id integer generated always as identity primary key,
  job_id integer not null references public.ain_jobs(id) on delete cascade,
  member_id uuid not null references public.ain_members(id) on delete cascade,
  created_at timestamptz not null default now()
);

create table public.ain_resources (
  id integer generated always as identity primary key,
  title text not null, kind text not null, url text not null, summary text not null default '',
  created_at timestamptz not null default now()
);

create table public.ain_notifications (
  id integer generated always as identity primary key,
  member_id uuid not null references public.ain_members(id) on delete cascade,
  text text not null, link text not null default '', read boolean not null default false,
  created_at timestamptz not null default now()
);

alter table public.ain_members enable row level security;
alter table public.ain_blocks enable row level security;
alter table public.ain_channels enable row level security;
alter table public.ain_posts enable row level security;
alter table public.ain_reports enable row level security;
alter table public.ain_events enable row level security;
alter table public.ain_event_saves enable row level security;
alter table public.ain_jobs enable row level security;
alter table public.ain_job_clicks enable row level security;
alter table public.ain_resources enable row level security;
alter table public.ain_notifications enable row level security;
revoke all on public.ain_members, public.ain_blocks, public.ain_channels, public.ain_posts, public.ain_reports,
  public.ain_events, public.ain_event_saves, public.ain_jobs, public.ain_job_clicks, public.ain_resources,
  public.ain_notifications from anon, authenticated;

-- Seed: events copied from the live conferences page (medsalesintelligencehub.co.uk/association-conferences/), checked 26/10/2026.
-- Undated events keep start_date null. Never guess a date.
insert into public.ain_events (title, organiser, detail, start_date, end_date, venue, source_url, source_label, group_label, members_only, verified_at) values
  ('ANTT 18th Aseptic Non Touch Technique (ANTT) UK & International Conference', 'ANTT', 'Cavendish Conference Rooms, 22 Duchess Mews, London W1G 9DT. In person, or by live stream and on demand. Tickets are paid.', '2026-10-30', null, 'Cavendish Conference Rooms, London', 'https://www.antt.org/conference2026.html', 'Visit the organiser', 'This autumn', false, '2026-10-26'),
  ('NAMDET North West Regional Meeting', 'National Association of Medical Device Educators and Trainers (NAMDET)', '9:30 to 1:00pm, Halton Hospital Education Centre Seminar Room, Hospital Way, Palacefields, Runcorn WA7 2DA.', '2026-10-30', null, 'Halton Hospital Education Centre, Runcorn', 'https://www.namdet.org', 'Visit the organiser', 'This autumn', false, '2026-10-26'),
  ('Nursing Live 2026', 'Nursing Live', 'Hall 2, NEC Birmingham. Free visitor tickets.', '2026-11-09', '2026-11-10', 'NEC Birmingham', 'https://www.nursinglive.com/', 'Get a free ticket', 'This autumn', false, '2026-10-26'),
  ('The ABHI UK HealthTech Conference 2026', 'Association of British HealthTech Industries (ABHI)', 'Cavendish Conference Centre, 22 Duchess Mews, London W1G 9DT. For leaders from industry, government, the NHS and regulation.', '2026-11-09', '2026-11-10', 'Cavendish Conference Centre, London', 'https://www.abhi.org.uk/events/abhi-events/the-abhi-uk-healthtech-conference-2026/', 'Visit the organiser', 'This autumn', false, '2026-10-26'),
  ('Wounds UK Conference', 'Wounds UK', 'Harrogate Convention Centre. Face to face. Theme: "Redefining the landscape: science, systems and solutions."', '2026-11-09', '2026-11-11', 'Harrogate Convention Centre', 'https://wounds-uk.com/', 'Visit the organiser', 'This autumn', false, '2026-10-26'),
  ('BAPEN Annual Conference 2026', 'BAPEN', 'Bournemouth International Centre. A Medical Masterclass and a paediatric nutrition and intestinal failure network day run on 9 Nov.', '2026-11-10', '2026-11-11', 'Bournemouth International Centre', 'https://www.bapen.org.uk/conference/', 'Visit the organiser', 'This autumn', false, '2026-10-26'),
  ('NAMDET Networking Dinner and Awards Night', 'NAMDET', 'From 7pm, County Hotel, Neville Street, Newcastle NE1 5DF. Tickets through Eventbrite.', '2026-11-11', null, 'County Hotel, Newcastle', 'https://www.namdet.org', 'Visit the organiser', 'This autumn', false, '2026-10-26'),
  ('NAMDET Conference 2026', 'NAMDET', 'The Catalyst, 3 Helix, Science Square, Newcastle upon Tyne NE4 5TG. Speakers and theme to be announced. Tickets through Eventbrite. NAMDET membership is free and includes nurses, company representatives and clinical educators.', '2026-11-12', null, 'The Catalyst, Newcastle upon Tyne', 'https://www.namdet.org', 'Visit the organiser', 'This autumn', false, '2026-10-26'),
  ('HCSA Annual Conference "Setting the Agenda"', 'Health Care Supply Association (HCSA)', 'The NHS procurement network. Venue not stated on the events page.', '2026-11-18', '2026-11-19', null, 'https://www.nhsprocurement.org.uk/events', 'Visit the organiser', 'This autumn', false, '2026-10-26'),
  ('ABHI Wound Care Group', 'Association of British HealthTech Industries (ABHI)', 'Members only. A working group of ABHI member companies: industry nurses in wound care companies should ask their ABHI company contact.', '2026-12-09', null, null, 'https://www.abhi.org.uk/events/', 'Visit the organiser', 'This autumn', true, '2026-10-26'),
  ('Royal College of Nursing (RCN) Congress', 'Royal College of Nursing', 'Liverpool. Venue not stated in the page text.', '2027-05-24', '2027-05-27', 'Liverpool', 'https://www.rcn.org.uk/congress', 'Visit the organiser', 'Plan ahead 2027', false, '2026-10-26'),
  ('NHS ConfedExpo', 'NHS Confederation', 'Manchester Central Convention Complex, Windmill Street, Manchester M2 3GX.', '2027-06-16', '2027-06-17', 'Manchester Central', 'https://www.nhsconfedexpo.org/', 'Visit the organiser', 'Plan ahead 2027', false, '2026-10-26'),
  ('Med-Tech Innovation Expo', 'Med-Tech Innovation Expo', 'Birmingham NEC, Hall 3A, North Avenue, Marston Green B40 1NT.', '2027-09-15', '2027-09-16', 'Birmingham NEC', 'https://med-techexpo.com/', 'Visit the organiser', 'Plan ahead 2027', false, '2026-10-26'),
  ('Association of the British Pharmaceutical Industry (ABPI) Annual Conference', 'ABPI', 'The 2026 conference was held on 23 April 2026, for members and invited guests. A 2027 save-the-date page exists with no date or venue yet.', null, null, null, 'https://www.abpi.org.uk/membership2/events/2027/04-april/save-the-date-abpi-annual-conference-2027/', 'Check the organiser', 'Date to be confirmed', false, '2026-10-26'),
  ('Infection Prevention Society (IPS) Annual Conference', 'IPS', 'The IPS site lists "IP2027 - Announcement coming soon." No date or venue yet.', null, null, null, 'https://www.ips.uk.net/', 'Check the organiser', 'Date to be confirmed', false, '2026-10-26'),
  ('Diabetes UK Professional Conference', 'Diabetes UK', 'Not verified: no 2027 date found. Check the conference site before planning.', null, null, null, 'https://dukpc.diabetes.org.uk', 'Check the organiser', 'Date to be confirmed', false, '2026-10-26');

insert into public.ain_channels (slug, title, description, sort) values
  ('moving-into-industry', 'Moving into industry', 'Questions and advice for nurses making the move from the NHS or care.', 0),
  ('clinical-education', 'Clinical education and training', 'Training customers, running study days and building education programmes.', 1),
  ('clinical-specialists', 'Clinical specialists and field roles', 'Day-to-day life as a clinical specialist, application specialist or field nurse.', 2),
  ('compliance', 'Compliance and codes of practice', 'Working within industry codes, NMC standards and company policy.', 3),
  ('regional', 'Regional meet-ups', 'Find colleagues near you and organise catch-ups.', 4);

insert into public.ain_resources (title, kind, url, summary) values
  ('Conferences for nurses in industry', 'Page', 'https://medsalesintelligencehub.co.uk/association-conferences/', 'Dates and venues as published by each organiser.'),
  ('Medical Sales Hub, clinical section', 'Site', 'https://medsalesintelligencehub.co.uk/medical-sales-hub/clinical/', 'Free for NHS staff.');

