// Events below are copied from the live conferences page
// (medsalesintelligencehub.co.uk/association-conferences/), checked 26/10/2026.
// Undated events keep start_date NULL and show "date not confirmed". Never guess a date.
const VERIFIED = '2026-10-26';
const events = [
  ['ANTT 18th Aseptic Non Touch Technique (ANTT) UK & International Conference', 'ANTT', 'Cavendish Conference Rooms, 22 Duchess Mews, London W1G 9DT. In person, or by live stream and on demand. Tickets are paid.', '2026-10-30', null, 'Cavendish Conference Rooms, London', 'This autumn', 'Visit the organiser'],
  ['NAMDET North West Regional Meeting', 'National Association of Medical Device Educators and Trainers (NAMDET)', '9:30 to 1:00pm, Halton Hospital Education Centre Seminar Room, Hospital Way, Palacefields, Runcorn WA7 2DA.', '2026-10-30', null, 'Halton Hospital Education Centre, Runcorn', 'This autumn', 'Visit the organiser'],
  ['Nursing Live 2026', 'Nursing Live', 'Hall 2, NEC Birmingham. Free visitor tickets.', '2026-11-09', '2026-11-10', 'NEC Birmingham', 'This autumn', 'Get a free ticket'],
  ['The ABHI UK HealthTech Conference 2026', 'Association of British HealthTech Industries (ABHI)', 'Cavendish Conference Centre, 22 Duchess Mews, London W1G 9DT. For leaders from industry, government, the NHS and regulation.', '2026-11-09', '2026-11-10', 'Cavendish Conference Centre, London', 'This autumn', 'Visit the organiser'],
  ['Wounds UK Conference', 'Wounds UK', 'Harrogate Convention Centre. Face to face. Theme: "Redefining the landscape: science, systems and solutions."', '2026-11-09', '2026-11-11', 'Harrogate Convention Centre', 'This autumn', 'Visit the organiser'],
  ['BAPEN Annual Conference 2026', 'BAPEN', 'Bournemouth International Centre. A Medical Masterclass and a paediatric nutrition and intestinal failure network day run on 9 Nov.', '2026-11-10', '2026-11-11', 'Bournemouth International Centre', 'This autumn', 'Visit the organiser'],
  ['NAMDET Networking Dinner and Awards Night', 'NAMDET', 'From 7pm, County Hotel, Neville Street, Newcastle NE1 5DF. Tickets through Eventbrite.', '2026-11-11', null, 'County Hotel, Newcastle', 'This autumn', 'Visit the organiser'],
  ['NAMDET Conference 2026', 'NAMDET', 'The Catalyst, 3 Helix, Science Square, Newcastle upon Tyne NE4 5TG. Speakers and theme to be announced. Tickets through Eventbrite. NAMDET membership is free and includes nurses, company representatives and clinical educators.', '2026-11-12', null, 'The Catalyst, Newcastle upon Tyne', 'This autumn', 'Visit the organiser'],
  ['HCSA Annual Conference "Setting the Agenda"', 'Health Care Supply Association (HCSA)', 'The NHS procurement network. Venue not stated on the events page.', '2026-11-18', '2026-11-19', null, 'This autumn', 'Visit the organiser'],
  ['ABHI Wound Care Group', 'Association of British HealthTech Industries (ABHI)', 'Members only. A working group of ABHI member companies: industry nurses in wound care companies should ask their ABHI company contact.', '2026-12-09', null, null, 'This autumn', 'Visit the organiser', 1],
  ['Royal College of Nursing (RCN) Congress', 'Royal College of Nursing', 'Liverpool. Venue not stated in the page text.', '2027-05-24', '2027-05-27', 'Liverpool', 'Plan ahead 2027', 'Visit the organiser'],
  ['NHS ConfedExpo', 'NHS Confederation', 'Manchester Central Convention Complex, Windmill Street, Manchester M2 3GX.', '2027-06-16', '2027-06-17', 'Manchester Central', 'Plan ahead 2027', 'Visit the organiser'],
  ['Med-Tech Innovation Expo', 'Med-Tech Innovation Expo', 'Birmingham NEC, Hall 3A, North Avenue, Marston Green B40 1NT.', '2027-09-15', '2027-09-16', 'Birmingham NEC', 'Plan ahead 2027', 'Visit the organiser'],
  ['Association of the British Pharmaceutical Industry (ABPI) Annual Conference', 'ABPI', 'The 2026 conference was held on 23 April 2026, for members and invited guests. A 2027 save-the-date page exists with no date or venue yet.', null, null, null, 'Date to be confirmed', 'Check the organiser'],
  ['Infection Prevention Society (IPS) Annual Conference', 'IPS', 'The IPS site lists "IP2027 - Announcement coming soon." No date or venue yet.', null, null, null, 'Date to be confirmed', 'Check the organiser'],
  ['Diabetes UK Professional Conference', 'Diabetes UK', 'Not verified: no 2027 date found. Check the conference site before planning.', null, null, null, 'Date to be confirmed', 'Check the organiser'],
];
// Organiser links, in the same order as the events above, copied from the live page.
const URLS = ['https://www.antt.org/conference2026.html', 'https://www.namdet.org', 'https://www.nursinglive.com/', 'https://www.abhi.org.uk/events/abhi-events/the-abhi-uk-healthtech-conference-2026/', 'https://wounds-uk.com/', 'https://www.bapen.org.uk/conference/', 'https://www.namdet.org', 'https://www.namdet.org', 'https://www.nhsprocurement.org.uk/events', 'https://www.abhi.org.uk/events/', 'https://www.rcn.org.uk/congress', 'https://www.nhsconfedexpo.org/', 'https://med-techexpo.com/', 'https://www.abpi.org.uk/membership2/events/2027/04-april/save-the-date-abpi-annual-conference-2027/', 'https://www.ips.uk.net/', 'https://dukpc.diabetes.org.uk'];
const SOURCE = 'https://medsalesintelligencehub.co.uk/association-conferences/';

const channels = [
  ['moving-into-industry', 'Moving into industry', 'Questions and advice for nurses making the move from the NHS or care.'],
  ['clinical-education', 'Clinical education and training', 'Training customers, running study days and building education programmes.'],
  ['clinical-specialists', 'Clinical specialists and field roles', 'Day-to-day life as a clinical specialist, application specialist or field nurse.'],
  ['compliance', 'Compliance and codes of practice', 'Working within industry codes, NMC standards and company policy.'],
  ['regional', 'Regional meet-ups', 'Find colleagues near you and organise catch-ups.'],
];

const resources = [
  ['Conferences for nurses in industry', 'Page', SOURCE, 'Dates and venues as published by each organiser.'],
  ['Medical Sales Hub, clinical section', 'Site', 'https://medsalesintelligencehub.co.uk/medical-sales-hub/clinical/', 'Free for NHS staff.'],
];

export function seed(db) {
  if (db.prepare('SELECT COUNT(*) c FROM events').get().c === 0) {
    const ins = db.prepare(`INSERT INTO events (title, organiser, detail, start_date, end_date, venue, source_url, source_label, group_label, members_only, verified_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?)`);
    events.forEach((e, i) => ins.run(e[0], e[1], e[2], e[3], e[4], e[5], URLS[i], e[7], e[6], e[8] || 0, VERIFIED));
  }
  if (db.prepare('SELECT COUNT(*) c FROM channels').get().c === 0) {
    const ins = db.prepare('INSERT INTO channels (slug, title, description, sort) VALUES (?,?,?,?)');
    channels.forEach((c, i) => ins.run(c[0], c[1], c[2], i));
  }
  if (db.prepare('SELECT COUNT(*) c FROM resources').get().c === 0) {
    const ins = db.prepare('INSERT INTO resources (title, kind, url, summary) VALUES (?,?,?,?)');
    for (const r of resources) ins.run(...r);
  }
}
