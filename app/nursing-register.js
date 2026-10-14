/* Nursing Register (Clinical Hub). Added 08/10/2026.
   Nurses add their experience and skills; approved employers browse the
   register without names or contact details and ask for an introduction.

   Talks to /wp-json/msh/v1/nurse-register (WPCode snippet from
   hub/wpcode/nursing-register.php). The server is the authority: it cleans
   every save, decides who may browse, and never sends an employer a name,
   email, phone, NMC PIN or LinkedIn. The tick lists come from the server too
   (options), so they are edited in the snippet, not here.

   Mounted into #msh-nursing-register by hub/pages/nursing-register.html.
   Loaded with new Function(); require()-able under node, where only the pure
   functions (_pure) are exercised: test_nursing_register.py. */
(function (root) {
  'use strict';

  var API = '/wp-json/msh/v1/nurse-register';
  var LISTS = ['registration', 'sectors', 'specialities', 'clinicalSkills', 'qualifications', 'transferable', 'roles'];
  var FLAGS = ['relocate', 'driving', 'rightToWork', 'training', 'jobsEmail'];
  var WHY = {
    region: 'Choose the region you live in.',
    registration: 'Tick at least one part of the NMC register.',
    qualYear: 'Enter the year you qualified, for example 2014.',
    specialities: 'Tick at least one speciality you have worked in.',
    nmcPin: 'That NMC PIN does not look right. It is two numbers, a letter, four numbers and a letter, like 12A3456E.',
    linkedin: 'The LinkedIn link should look like https://www.linkedin.com/in/your-name',
    phone: 'Check the phone number.',
    consent: 'Tick the consent box to make your profile visible to employers.'
  };

  /* Marketing copy (Lou, 08/10/2026): register once, be found by recruiters
     and employers without signing up with several agencies, and get the
     Clinical Hub's careers resources. Only NHS nurses join free (Lou,
     08/10/2026), so "free" is said of them alone. Links are live Hub pages
     (checked 08/10/2026). */
  var PITCH = 'Register once and let recruiters and employers find you. No signing up with five different agencies, no telling your story over and over. Add your experience and skills, choose who can see you, and get new roles in your area in your inbox every Monday.';
  var RESOURCES = '<div class="res"><p class="sub">Your careers resources</p><div class="chips">'
    + [['Jobs', '/medical-sales-hub/clinical-jobs/'], ['Your CV', '/medical-sales-hub/clinical-cv/'],
      ['Clinical to commercial routes', '/medical-sales-hub/clinical-to-commercial-routes/'], ['Career Centre', '/medical-sales-hub/careers/'],
      ['Revalidation portfolio', '/medical-sales-hub/clinical-portfolio/'], ['Resources', '/medical-sales-hub/clinical-resources/']]
      .map(function (l) { return '<a class="chip" href="' + l[1] + '">' + l[0] + '</a>'; }).join('') + '</div></div>';
  /* How it works (Lou, 14/10/2026: explain better what it does; read the CV
     rather than relying on the nurse to type everything). */
  var HOW = '<ol class="how">'
    + '<li><strong>Add your CV.</strong> We read it and fill in your registration, specialities, skills and qualifications for you. Your CV file is read on your device and isn\'t stored.</li>'
    + '<li><strong>Check it and add what\'s missing.</strong> Untick anything that\'s wrong, and tick anything you\'ve done that isn\'t on your CV. Most nurses have done far more than their CV says.</li>'
    + '<li><strong>Choose who sees you, then submit.</strong> Approved recruiters and employers can find you by region, speciality and skill. You decide whether they see your contact details, and whether you want new roles in your area emailed every Monday.</li>'
    + '<li><strong>Get your careers pack.</strong> When you submit, we email you a copy of your choices, and you can download Beyond the Bedside, our encyclopedia of nursing careers.</li></ol>';
  /* For recruiters and employers (Lou, 14/10/2026): browsing is only for Hub
     Employers, approved by Lou. A recruiter who already uses the Hub gets it
     added to their account; nothing else about it changes. */
  var RECRUITERS = '<div class="msg info"><strong>Recruiter or employer?</strong> Approved Hub Employers can search the register by region, speciality and skill, and ask us to introduce them to a nurse. If you already use the Hub, we add it to your account. Email <a href="mailto:louisehoult@elevateandthrive.uk?subject=Nursing%20Register%20access">louisehoult@elevateandthrive.uk</a> to ask for access.</div>';
  var LANDING = '<div class="nr"><h1>Join the Nursing Register</h1>'
    + '<p class="lede">' + PITCH + '</p>'
    + '<p class="sub">How it works</p>' + HOW
    + '<ul class="pitch"><li><strong>One profile, seen by recruiters and employers.</strong> Your region, specialities and skills, in one place they can search.</li>'
    + '<li><strong>New roles in your area every Monday.</strong> Straight from the companies\' own careers pages, not recycled agency adverts.</li>'
    + '<li><strong>The best nursing careers resources in one place.</strong> Jobs, CV help, your revalidation portfolio and the real routes from clinical into industry.</li>'
    + '<li><strong>You stay in control.</strong> Hide or delete your profile, or stop the emails, any time.</li></ul>'
    + '<p class="lede"><strong>Free for NHS nurses.</strong></p>'
    + '<div class="actions"><a class="btn" href="/register/">Join the register</a><a class="btn ghost" href="/login/">I already have an account</a></div>'
    + RECRUITERS + '</div>';

  /* ---------- pure ---------- */
  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function has(list, id) { return Array.isArray(list) && list.indexOf(id) !== -1; }

  /* Profiles an employer's filters keep. f: { region, speciality, skill, role,
     availability, minYears, text }. Empty values match everything. skill
     matches a clinical skill or a qualification. availability matches that
     choice or anything sooner. */
  var SOON = ['now', '1-month', '3-months', '6-months', 'exploring'];
  function filter(profiles, f, options) {
    f = f || {};
    var minY = parseInt(f.minYears, 10);
    var text = String(f.text || '').toLowerCase().trim();
    return (profiles || []).filter(function (p) {
      if (f.region && p.region !== f.region) { return false; }
      if (f.speciality && !has(p.specialities, f.speciality)) { return false; }
      if (f.skill && !has(p.clinicalSkills, f.skill) && !has(p.qualifications, f.skill)) { return false; }
      if (f.role && !has(p.roles, f.role)) { return false; }
      if (f.availability) {
        var want = SOON.indexOf(f.availability), got = SOON.indexOf(p.availability);
        if (got === -1 || got > want) { return false; }
      }
      if (!isNaN(minY) && (p.yearsQualified || 0) < minY) { return false; }
      if (text) {
        var hay = [p.ref, p.area, p.currentRole, p.bio].join(' ');
        if (options) {
          LISTS.forEach(function (k) {
            (p[k] || []).forEach(function (id) { hay += ' ' + ((options[k] || {})[id] || ''); });
          });
        }
        if (hay.toLowerCase().indexOf(text) === -1) { return false; }
      }
      return true;
    });
  }

  /* Days until a visible profile drops off the register, or null. */
  function daysLeft(updated, today, staleDays) {
    var a = Date.parse(updated + 'T00:00:00Z'), b = Date.parse(today + 'T00:00:00Z');
    if (isNaN(a) || isNaN(b)) { return null; }
    return staleDays - Math.floor((b - a) / 86400000);
  }

  /* What the CV suggests, added to what the nurse already has. Never
     removes a tick or overwrites a field they filled in. Returns the merged
     profile, the ids the CV added (to highlight) and how many things it
     filled in. */
  var CV_LISTS = ['registration', 'sectors', 'specialities', 'clinicalSkills', 'qualifications', 'transferable'];
  var CV_FIELDS = ['qualYear', 'band', 'region', 'nmcPin'];
  function mergeSuggest(cur, s) {
    var p = {}, added = {}, n = 0;
    Object.keys(cur || {}).forEach(function (k) { p[k] = cur[k]; });
    s = s || {};
    CV_LISTS.forEach(function (k) {
      var mine = Array.isArray(p[k]) ? p[k].slice() : [];
      added[k] = [];
      (Array.isArray(s[k]) ? s[k] : []).forEach(function (id) {
        if (mine.indexOf(id) === -1) { mine.push(id); added[k].push(id); n++; }
      });
      p[k] = mine;
    });
    CV_FIELDS.forEach(function (k) {
      var v = s[k];
      if (v !== null && v !== undefined && v !== '' && (p[k] === undefined || p[k] === null || p[k] === '')) {
        p[k] = v; added[k] = true; n++;
      }
    });
    return { profile: p, added: added, count: n };
  }

  var pure = { esc: esc, filter: filter, daysLeft: daysLeft, mergeSuggest: mergeSuggest };
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { _pure: pure };
    return;
  }

  /* ---------- browser ---------- */
  var doc = root.document;
  var mount = doc.getElementById('msh-nursing-register');
  if (!mount) { return; }

  var S = { options: null, profile: null, canBrowse: false, isAdmin: false, staleDays: 365, tab: 'me', browse: null, f: {} };

  function nonce() { return root.mshRestNonce || root.mshPrefsNonce || ''; }
  function api(method, path, body) {
    var o = { method: method, credentials: 'same-origin', headers: { 'X-WP-Nonce': nonce(), 'Accept': 'application/json' } };
    if (body !== undefined) { o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(body); }
    return fetch(API + (path || ''), o).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, status: r.status, body: j }; });
    });
  }
  function today() {
    var d = new Date();
    return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
  }
  function label(k, id) { return ((S.options || {})[k] || {})[id] || id; }

  var CSS = '#msh-nursing-register{max-width:1100px;margin:0 auto;padding:32px 20px 64px;font-family:Inter,Arial,sans-serif;color:#1C2633;font-size:15px;line-height:1.5}'
    + '.nr h1{font-family:"Source Serif 4",Georgia,serif;font-size:32px;color:#14304F;margin:0 0 8px}'
    + '.nr .lede{color:#3A4656;max-width:720px;margin:0 0 24px}'
    + '.nr .tabs{display:flex;gap:8px;margin:0 0 24px;flex-wrap:wrap}'
    + '.nr .tabs button{border:1px solid #14304F;background:#fff;color:#14304F;border-radius:999px;padding:8px 18px;font:600 14px Inter,Arial,sans-serif;cursor:pointer}'
    + '.nr .tabs button[aria-selected=true]{background:#14304F;color:#fff}'
    + '.nr fieldset{border:1px solid #DAD7CE;border-radius:12px;background:#fff;margin:0 0 16px;padding:18px 20px}'
    + '.nr legend{font-weight:700;color:#14304F;padding:0 6px;font-size:16px}'
    + '.nr .hint{color:#5A6676;font-size:13px;margin:0 0 12px}'
    + '.nr .ticks{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:6px 16px}'
    + '.nr .ticks label,.nr .flag{display:flex;gap:8px;align-items:flex-start;font-size:14px;cursor:pointer}'
    + '.nr .ticks input,.nr .flag input{margin-top:3px;flex:none}'
    + '.nr .row{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px 16px;margin:0 0 12px}'
    + '.nr .row label{display:block;font-size:13px;font-weight:600;color:#3A4656}'
    + '.nr input[type=text],.nr input[type=number],.nr input[type=tel],.nr input[type=url],.nr select,.nr textarea{width:100%;box-sizing:border-box;border:1px solid #C9C5BA;border-radius:8px;padding:9px 10px;font:15px Inter,Arial,sans-serif;margin-top:4px;background:#fff;color:#1C2633}'
    + '.nr textarea{min-height:110px}'
    + '.nr .private{background:#F2F5F9}'
    + '.nr .btn{background:#14304F;color:#fff;border:0;border-radius:8px;padding:11px 22px;font:600 15px Inter,Arial,sans-serif;cursor:pointer}'
    + '.nr .btn.ghost{background:#fff;color:#14304F;border:1px solid #14304F}'
    + '.nr .btn.danger{background:#fff;color:#A3262A;border:1px solid #A3262A}'
    + '.nr .msg{border-radius:8px;padding:10px 14px;margin:0 0 16px;font-size:14px}'
    + '.nr .msg.ok{background:#E6F2EA;color:#1D5631}.nr .msg.bad{background:#FBEAEA;color:#8A1F22}.nr .msg.info{background:#EEF2F7;color:#14304F}'
    + '.nr .actions{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-top:8px}'
    + '.nr .filters{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin:0 0 16px}'
    + '.nr .card{background:#fff;border:1px solid #DAD7CE;border-radius:12px;padding:18px 20px;margin:0 0 14px}'
    + '.nr .card h3{margin:0 0 4px;font-size:17px;color:#14304F}'
    + '.nr .meta{color:#3A4656;font-size:14px;margin:0 0 10px}'
    + '.nr .chips{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 10px}'
    + '.nr .chip{background:#EEF2F7;color:#14304F;border-radius:999px;padding:3px 10px;font-size:12.5px}'
    + '.nr .chip.skill{background:#F3EFE4;color:#5B4A1E}.nr .chip.ok{background:#E6F2EA;color:#1D5631}.nr .chip.warn{background:#FBEAEA;color:#8A1F22}'
    + '.nr .sub{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#5A6676;margin:8px 0 0}'
    + '.nr .res{margin:0 0 24px}.nr .res a.chip{text-decoration:none}.nr a.btn{display:inline-block;text-decoration:none}'
    + '.nr ul.pitch{padding-left:20px;max-width:720px;margin:0 0 24px}.nr ul.pitch li{margin:0 0 10px}'
    + '.nr ol.how{padding-left:22px;max-width:760px;margin:6px 0 24px}.nr ol.how li{margin:0 0 10px}'
    + '.nr .cv{background:#FFFBEA;border-color:#E9D9A6}.nr .cv input[type=file]{margin:6px 0 4px}'
    + '.nr .ticks label.fromcv,.nr label.fromcv{background:#FFF1BF;border-radius:6px;padding:2px 4px;margin:-2px -4px}'
    + '.nr .done{margin-top:20px}.nr .done a.chip{text-decoration:none}.nr .done .links{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 8px}'
    + '@media (max-width:600px){.nr h1{font-size:26px}.nr fieldset{padding:14px}}';

  function ticks(k, chosen) {
    var o = S.options[k] || {}, h = '<div class="ticks">';
    Object.keys(o).forEach(function (id) {
      var cv = S.fromCv && has(S.fromCv[k], id);
      h += '<label' + (cv ? ' class="fromcv" title="Found in your CV"' : '') + '><input type="checkbox" name="' + k + '" value="' + esc(id) + '"' + (has(chosen, id) ? ' checked' : '') + '><span>' + esc(o[id]) + '</span></label>';
    });
    return h + '</div>';
  }
  function select(k, name, cur, blank) {
    var o = S.options[k] || {}, h = '<select name="' + name + '"><option value="">' + esc(blank) + '</option>';
    Object.keys(o).forEach(function (id) {
      h += '<option value="' + esc(id) + '"' + (cur === id ? ' selected' : '') + '>' + esc(o[id]) + '</option>';
    });
    return h + '</select>';
  }
  function flag(name, on, text) {
    return '<label class="flag"><input type="checkbox" name="' + name + '"' + (on ? ' checked' : '') + '><span>' + text + '</span></label>';
  }
  function fs(title, hint, inner, cls) {
    return '<fieldset' + (cls ? ' class="' + cls + '"' : '') + '><legend>' + title + '</legend>' + (hint ? '<p class="hint">' + hint + '</p>' : '') + inner + '</fieldset>';
  }

  function statusBox(p) {
    if (!p) { return ''; }
    if (!p.visible) {
      return '<div class="msg info">Your profile <strong>' + esc(p.ref) + '</strong> is saved but hidden. Employers can\'t see it until you make it visible below.</div>';
    }
    var left = daysLeft(p.updated, today(), S.staleDays);
    if (left !== null && left <= 0) {
      return '<div class="msg bad">Your profile <strong>' + esc(p.ref) + '</strong> has been hidden because it hasn\'t been confirmed for a year. Check it and save to show it again.</div>';
    }
    var h = '<div class="msg ok">Your profile <strong>' + esc(p.ref) + '</strong> is visible to approved employers'
      + (p.shareContact ? ', with your contact details so they can get in touch directly.' : ', without your name or contact details.');
    if (left !== null && left <= 30) { h += ' It drops off in ' + left + ' day' + (left === 1 ? '' : 's') + ' unless you save it again.'; }
    return h + '</div>';
  }

  function drawMe(note) {
    var p = S.draft || S.profile || {};
    var yr = new Date().getFullYear();
    var h = statusBox(S.profile);
    h += '<form id="nr-form" novalidate>';
    h += fs('Start with your CV', 'Upload your CV as a PDF or Word file and we\'ll fill in as much as we can. It\'s read on your device to find your skills and experience. The file itself isn\'t uploaded or kept.',
      '<input type="file" id="nr-cv" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document">'
      + '<p class="hint" id="nr-cv-status" aria-live="polite">' + (S.cvNote || 'No CV? No problem, just fill in the form below.') + '</p>', 'cv');
    h += fs('Where you are', 'Employers see your region and the area you give here. Put a county or nearest city, never your address.',
      '<div class="row"><label>Region' + select('regions', 'region', p.region, 'Choose your region') + '</label>'
      + '<label>Area<input type="text" name="area" maxlength="60" placeholder="e.g. Leeds, or North Yorkshire" value="' + esc(p.area) + '"></label>'
      + '<label>How far you\'d travel' + select('travel', 'travel', p.travel, 'Choose') + '</label></div>'
      + flag('relocate', p.relocate, 'I\'d relocate for the right role'));
    h += fs('Your registration', '',
      '<p class="sub">Part of the NMC register</p>' + ticks('registration', p.registration)
      + '<div class="row" style="margin-top:14px"><label>Year qualified<input type="number" name="qualYear" min="1960" max="' + yr + '" placeholder="e.g. 2014" value="' + esc(p.qualYear) + '"></label>'
      + '<label>Current or last band' + select('bands', 'band', p.band, 'Choose') + '</label>'
      + '<label>Current role<input type="text" name="currentRole" maxlength="80" placeholder="e.g. Tissue Viability Nurse Specialist" value="' + esc(p.currentRole) + '"></label></div>'
      + '<p class="sub">Where you\'ve worked</p>' + ticks('sectors', p.sectors));
    h += fs('Specialities you\'ve worked in', 'Tick every one with real hands-on time. Employers filter on these.', ticks('specialities', p.specialities));
    h += fs('Clinical skills', 'Skills you\'re confident doing or teaching.', ticks('clinicalSkills', p.clinicalSkills));
    h += fs('Qualifications and courses', '', ticks('qualifications', p.qualifications));
    h += fs('Skills that carry into industry', 'These are what hiring managers in medical sales look for first.', ticks('transferable', p.transferable));
    h += fs('What you\'re looking for', '',
      '<p class="sub">Roles</p>' + ticks('roles', p.roles)
      + '<div class="row" style="margin-top:14px"><label>When you could start' + select('availability', 'availability', p.availability, 'Choose') + '</label></div>'
      + flag('driving', p.driving, 'Full UK driving licence')
      + flag('rightToWork', p.rightToWork, 'Right to work in the UK')
      + flag('training', p.training, 'I\'ve completed the Elevate &amp; Thrive Medical Sales Training Programme'));
    h += fs('About you', 'A few lines in your own words: what you\'re proud of, and why industry. Don\'t include your name or contact details; they\'re removed if you do.',
      '<textarea name="bio" maxlength="600">' + esc(p.bio) + '</textarea><p class="hint" id="nr-count"></p>');
    h += fs('Private: only Elevate &amp; Thrive sees this', 'Your NMC PIN lets us check your registration on the NMC register and show employers a "registration checked" mark. Your name and email come from your Hub account.',
      '<div class="row"><label>NMC PIN<input type="text" name="nmcPin" maxlength="10" placeholder="12A3456E" value="' + esc(p.nmcPin) + '"></label>'
      + '<label>Phone<input type="tel" name="phone" maxlength="20" value="' + esc(p.phone) + '"></label>'
      + '<label>LinkedIn<input type="url" name="linkedin" maxlength="160" placeholder="https://www.linkedin.com/in/..." value="' + esc(p.linkedin) + '"></label></div>', 'private');
    h += fs('Weekly jobs email', 'Every Monday: new roles in your region from the companies\' own careers pages. Nothing new, no email.',
      flag('jobsEmail', p.jobsEmail, '<strong>Send me the weekly jobs email</strong> for my region. I can stop it from any email.'));
    h += fs('Who can see you', '',
      flag('consent', !!p.consentAt, 'I agree that Elevate &amp; Thrive may show this profile, without my name or contact details, to recruiters and employers it has approved, and contact me when one asks to be introduced. I can hide or delete it at any time.')
      + flag('shareContact', p.shareContact, '<strong>Let recruiters contact me directly.</strong> I agree that Elevate &amp; Thrive may share my name, email, phone number and LinkedIn with the recruiters and employers it has approved, so they can contact me about roles. My NMC PIN is never shared. I can untick this at any time.')
      + flag('visible', p.visible, '<strong>Make my profile visible to employers</strong>')
      + '<p class="hint" style="margin-top:10px">Profiles not confirmed for a year are hidden automatically.</p>');
    h += '<div class="actions"><button class="btn" type="submit">Save my profile</button>'
      + (S.profile ? '<button class="btn danger" type="button" id="nr-delete">Delete my profile</button>' : '') + '</div></form>';
    h += '<div id="nr-done" class="done">' + (note || '') + '</div>';
    return h;
  }

  /* Shown under the Save button once a profile is submitted (Lou,
     14/10/2026): confirmation, the email copy, the encyclopedia download,
     the Career Centre and other careers links. Links come from the server. */
  function doneBox(emailed) {
    var links = S.links || [];
    var h = '<div class="msg ok"><strong>Thank you, your profile is submitted.</strong> '
      + (emailed ? 'We\'ve emailed a copy of your choices to you.' : 'We couldn\'t send the confirmation email just now, but your profile is saved.') + '</div>'
      + '<p class="sub">Your next steps</p><div class="links">';
    links.filter(function (l) { return l.main; }).forEach(function (l) {
      h += '<a class="btn" href="' + esc(l.url) + '"' + (/\.pdf$/i.test(l.url) ? ' download' : '') + '>' + esc(l.label) + '</a>';
    });
    h += '</div><div class="chips">';
    links.filter(function (l) { return !l.main; }).forEach(function (l) {
      h += '<a class="chip" href="' + esc(l.url) + '">' + esc(l.label) + '</a>';
    });
    return h + '</div>';
  }

  /* ---------- CV reading ---------- */
  var LIBS = {
    pdf: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js',
    pdfWorker: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js',
    docx: 'https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.6.0/mammoth.browser.min.js'
  };
  function loadScript(src) {
    return new Promise(function (ok, bad) {
      if (doc.querySelector('script[src="' + src + '"]')) { ok(); return; }
      var s = doc.createElement('script');
      s.src = src; s.onload = function () { ok(); }; s.onerror = function () { bad(new Error('load ' + src)); };
      doc.head.appendChild(s);
    });
  }
  function cvText(file) {
    var name = (file.name || '').toLowerCase();
    return file.arrayBuffer().then(function (buf) {
      if (/\.docx$/.test(name)) {
        return loadScript(LIBS.docx).then(function () {
          return root.mammoth.extractRawText({ arrayBuffer: buf }).then(function (r) { return r.value || ''; });
        });
      }
      if (/\.pdf$/.test(name) || file.type === 'application/pdf') {
        return loadScript(LIBS.pdf).then(function () {
          var lib = root.pdfjsLib;
          lib.GlobalWorkerOptions.workerSrc = LIBS.pdfWorker;
          return lib.getDocument({ data: buf }).promise.then(function (pdf) {
            var pages = [];
            for (var i = 1; i <= Math.min(pdf.numPages, 12); i++) {
              pages.push(pdf.getPage(i).then(function (pg) { return pg.getTextContent(); }).then(function (c) {
                return c.items.map(function (it) { return it.str; }).join(' ');
              }));
            }
            return Promise.all(pages).then(function (t) { return t.join('\n'); });
          });
        });
      }
      throw new Error('type');
    });
  }

  function readForm(form) {
    var b = {};
    ['region', 'area', 'travel', 'qualYear', 'band', 'currentRole', 'availability', 'bio', 'nmcPin', 'phone', 'linkedin'].forEach(function (n) {
      var el = form.elements[n];
      b[n] = el ? String(el.value || '').trim() : '';
    });
    LISTS.forEach(function (k) {
      b[k] = Array.prototype.slice.call(form.querySelectorAll('input[name="' + k + '"]:checked')).map(function (i) { return i.value; });
    });
    FLAGS.concat(['consent', 'shareContact', 'visible']).forEach(function (n) { b[n] = !!(form.elements[n] && form.elements[n].checked); });
    return b;
  }

  function wireMe() {
    var form = doc.getElementById('nr-form');
    var bio = form.elements.bio, count = doc.getElementById('nr-count');
    function n() { count.textContent = (600 - bio.value.length) + ' characters left'; }
    bio.addEventListener('input', n); n();
    var cvIn = doc.getElementById('nr-cv'), cvSay = doc.getElementById('nr-cv-status');
    cvIn.addEventListener('change', function () {
      var f = cvIn.files && cvIn.files[0];
      if (!f) { return; }
      if (f.size > 15 * 1024 * 1024) { cvSay.textContent = 'That file is too big. Try a PDF or Word file under 15 MB.'; return; }
      cvSay.textContent = 'Reading your CV...';
      cvText(f).then(function (text) {
        if (String(text).replace(/\s+/g, '').length < 150) { throw new Error('empty'); }
        return api('POST', '/cv', { text: text });
      }).then(function (r) {
        if (!r.ok) { throw new Error('cv ' + r.status); }
        var m = mergeSuggest(readForm(form), r.body);
        S.draft = m.profile; S.fromCv = m.added;
        S.cvNote = m.count
          ? '<strong>We\'ve filled in ' + m.count + ' thing' + (m.count === 1 ? '' : 's') + ' from your CV</strong>, highlighted in yellow. Check each one and untick anything that\'s wrong. Then go through the lists and tick anything you\'ve done that isn\'t on your CV.'
          : 'We read your CV but couldn\'t match anything to the lists below. Please tick what applies to you.';
        render();
        var at = doc.getElementById('nr-cv-status');
        if (at) { at.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
      }).catch(function (e) {
        cvSay.textContent = (e && e.message === 'empty')
          ? 'We couldn\'t read any text in that file. It may be a scanned image. Please fill in the form below instead.'
          : (e && e.message === 'type') ? 'Please choose a PDF or a Word (.docx) file.'
          : 'Sorry, we couldn\'t read that CV just now. Please fill in the form below instead.';
      });
    });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = form.querySelector('button[type=submit]');
      btn.disabled = true; btn.textContent = 'Saving...';
      api('POST', '', readForm(form)).then(function (r) {
        if (r.ok) {
          take(r.body);
          S.draft = null; S.fromCv = null; S.cvNote = '';
          render(doneBox(!!r.body.emailed));
          var done = doc.getElementById('nr-done');
          if (done) { done.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
        } else {
          var why = r.body && r.body.data && r.body.data.field;
          btn.disabled = false; btn.textContent = 'Save my profile';
          showMsg(WHY[why] || 'That didn\'t save. Please try again.');
        }
      }, function () {
        btn.disabled = false; btn.textContent = 'Save my profile';
        showMsg('That didn\'t save. Check your connection and try again.');
      });
    });
    var del = doc.getElementById('nr-delete');
    if (del) {
      del.addEventListener('click', function () {
        if (!root.confirm('Delete your register profile? Employers will no longer see it. This can\'t be undone.')) { return; }
        api('DELETE', '').then(function (r) {
          if (r.ok) { take(r.body); render('<div class="msg ok">Your profile has been deleted.</div>'); }
          else { showMsg('That didn\'t delete. Please try again.'); }
        });
      });
    }
  }
  function showMsg(t) {
    var old = mount.querySelector('.msg.bad.live');
    if (old) { old.parentNode.removeChild(old); }
    var d = doc.createElement('div');
    d.className = 'msg bad live'; d.textContent = t;
    var form = doc.getElementById('nr-form');
    form.parentNode.insertBefore(d, form);
    d.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function card(p) {
    var reg = (p.registration || []).map(function (id) { return label('registration', id); }).join(', ');
    var meta = [reg, 'qualified ' + p.qualYear + ' (' + p.yearsQualified + ' year' + (p.yearsQualified === 1 ? '' : 's') + ')'];
    if (p.band) { meta.push(label('bands', p.band)); }
    var where = [label('regions', p.region)];
    if (p.area) { where.push(p.area); }
    if (p.travel) { where.push(label('travel', p.travel)); }
    if (p.relocate) { where.push('would relocate'); }
    function chips(k, cls) {
      var l = p[k] || [];
      if (!l.length) { return ''; }
      return '<div class="chips">' + l.map(function (id) { return '<span class="chip' + (cls ? ' ' + cls : '') + '">' + esc(label(k, id)) + '</span>'; }).join('') + '</div>';
    }
    var badges = '';
    if (p.nmcChecked) { badges += '<span class="chip ok">NMC registration checked ' + esc(p.nmcChecked) + '</span>'; }
    if (p.availability) { badges += '<span class="chip">' + esc(label('availability', p.availability)) + '</span>'; }
    if (p.driving) { badges += '<span class="chip">UK driving licence</span>'; }
    if (p.rightToWork) { badges += '<span class="chip">Right to work in UK</span>'; }
    if (p.training) { badges += '<span class="chip">Medical Sales Training Programme (self-declared)</span>'; }
    if (p.hidden) { badges += '<span class="chip warn">Hidden from employers</span>'; }

    var h = '<div class="card" data-ref="' + esc(p.ref) + '"><h3>' + esc(p.ref) + (p.currentRole ? ': ' + esc(p.currentRole) : '') + '</h3>'
      + '<p class="meta">' + esc(meta.join(' · ')) + '<br>' + esc(where.join(' · ')) + '</p>'
      + (badges ? '<div class="chips">' + badges + '</div>' : '')
      + '<p class="sub">Specialities</p>' + chips('specialities')
      + ((p.clinicalSkills || []).length || (p.qualifications || []).length ? '<p class="sub">Clinical skills and qualifications</p>' + chips('clinicalSkills', 'skill') + chips('qualifications', 'skill') : '')
      + ((p.transferable || []).length ? '<p class="sub">Transferable skills</p>' + chips('transferable', 'skill') : '')
      + ((p.roles || []).length ? '<p class="sub">Looking for</p>' + chips('roles') : '')
      + (p.bio ? '<p style="margin:10px 0 0">' + esc(p.bio) + '</p>' : '');
    if (S.isAdmin && p.private) {
      var q = p.private;
      h += '<div class="msg info" style="margin-top:12px"><strong>Admin only.</strong> ' + esc(q.name) + ' · ' + esc(q.email)
        + (q.phone ? ' · ' + esc(q.phone) : '') + '<br>NMC PIN: ' + esc(q.nmcPin || 'not given')
        + (q.linkedin ? ' · <a href="' + esc(q.linkedin) + '" target="_blank" rel="noopener">LinkedIn</a>' : '')
        + ' · last saved ' + esc(q.updated)
        + (q.nmcPin ? '<div class="actions"><a class="btn ghost" href="https://www.nmc.org.uk/registration/search-the-register/" target="_blank" rel="noopener">NMC register</a>'
          + '<button class="btn ghost" type="button" data-verify="' + (p.nmcChecked ? '0' : '1') + '">' + (p.nmcChecked ? 'Clear NMC check' : 'Mark NMC PIN checked') + '</button></div>' : '')
        + '</div>';
    }
    if (p.contact) {
      var c = p.contact;
      h += '<div class="msg ok" style="margin-top:12px"><strong>Happy to be contacted directly.</strong> ' + esc(c.name)
        + ' · <a href="mailto:' + esc(c.email) + '">' + esc(c.email) + '</a>'
        + (c.phone ? ' · ' + esc(c.phone) : '')
        + (c.linkedin ? ' · <a href="' + esc(c.linkedin) + '" target="_blank" rel="noopener">LinkedIn</a>' : '') + '</div>';
    } else if (!p.hidden) {
      h += '<div class="actions"><button class="btn" type="button" data-intro>Request introduction</button></div>';
    }
    return h + '</div>';
  }

  function drawBrowse() {
    if (!S.browse) { return '<p>Loading the register...</p>'; }
    var f = S.f;
    var skillOpts = {};
    Object.keys(S.options.clinicalSkills).forEach(function (k) { skillOpts[k] = S.options.clinicalSkills[k]; });
    Object.keys(S.options.qualifications).forEach(function (k) { skillOpts[k] = S.options.qualifications[k]; });
    S.options._skills = skillOpts;
    var h = '<p class="lede">Every nurse here has chosen to be seen. Where a nurse has agreed to direct contact, their details are on their card. For everyone else, ask for an introduction and we\'ll check with the nurse first, then put you in touch.</p>'
      + '<div class="filters">'
      + select('regions', 'region', f.region, 'Any region')
      + select('specialities', 'speciality', f.speciality, 'Any speciality')
      + select('_skills', 'skill', f.skill, 'Any skill or qualification')
      + select('roles', 'role', f.role, 'Any role')
      + select('availability', 'availability', f.availability, 'Any start date')
      + '<input type="number" name="minYears" min="0" max="60" placeholder="Min. years qualified" value="' + esc(f.minYears) + '">'
      + '<input type="text" name="text" placeholder="Search" value="' + esc(f.text) + '"></div>';
    var list = filter(S.browse, f, S.options);
    h += '<p class="hint">' + list.length + ' of ' + S.browse.length + ' nurse' + (S.browse.length === 1 ? '' : 's') + '</p>';
    h += list.length ? list.map(card).join('') : '<p>No one matches those filters yet.</p>';
    return h;
  }

  function wireBrowse() {
    var box = mount.querySelector('.filters');
    if (box) {
      box.addEventListener('change', onFilter);
      box.addEventListener('input', function (e) { if (e.target.name === 'text' || e.target.name === 'minYears') { onFilter(e); } });
    }
    function onFilter(e) {
      S.f[e.target.name] = e.target.value;
      var at = e.target.name, pos = e.target.selectionStart;
      render();
      var el = mount.querySelector('.filters [name="' + at + '"]');
      if (el) { el.focus(); try { if (pos !== null && pos !== undefined) { el.setSelectionRange(pos, pos); } } catch (x) {} }
    }
    mount.querySelectorAll('[data-intro]').forEach(function (b) {
      b.addEventListener('click', function () {
        var c = b.closest('.card'), ref = c.getAttribute('data-ref');
        var wrap = doc.createElement('div');
        wrap.innerHTML = '<textarea maxlength="1000" placeholder="Tell us about the role: title, company, territory and anything else that helps."></textarea>'
          + '<div class="actions"><button class="btn" type="button">Send request</button><span class="hint"></span></div>';
        b.parentNode.replaceWith(wrap);
        var send = wrap.querySelector('button'), note = wrap.querySelector('.hint');
        send.addEventListener('click', function () {
          send.disabled = true; note.textContent = 'Sending...';
          api('POST', '/intro', { ref: ref, message: wrap.querySelector('textarea').value }).then(function (r) {
            if (r.ok) { wrap.innerHTML = '<div class="msg ok">Request sent. We\'ll check with the nurse and come back to you.</div>'; return; }
            send.disabled = false;
            note.textContent = r.status === 429 ? 'You\'ve reached today\'s limit of introduction requests. Try again tomorrow.' : 'That didn\'t send. Please try again.';
          });
        });
      });
    });
    mount.querySelectorAll('[data-verify]').forEach(function (b) {
      b.addEventListener('click', function () {
        var ref = b.closest('.card').getAttribute('data-ref');
        b.disabled = true;
        api('POST', '/verify', { ref: ref, checked: b.getAttribute('data-verify') === '1' }).then(function (r) {
          if (!r.ok) { b.disabled = false; return; }
          S.browse.forEach(function (p) { if (p.ref === ref) { p.nmcChecked = r.body.nmcChecked; } });
          render();
        });
      });
    });
  }

  function loadBrowse() {
    api('GET', '/browse').then(function (r) {
      S.browse = r.ok && r.body && Array.isArray(r.body.profiles) ? r.body.profiles : [];
      if (S.tab === 'browse') { render(); }
    });
  }

  function take(b) {
    S.options = b.options; S.profile = b.profile; S.canBrowse = !!b.canBrowse; S.isAdmin = !!b.isAdmin;
    S.staleDays = b.staleDays || 365; S.links = Array.isArray(b.links) ? b.links : [];
  }

  function render(note) {
    var h = '<div class="nr"><h1>Nursing Register</h1>';
    if (S.tab === 'me') {
      h += '<p class="lede">' + PITCH + '</p>' + (S.profile ? '' : '<p class="sub">How it works</p>' + HOW) + RESOURCES;
    }
    if (S.canBrowse) {
      h += '<div class="tabs" role="tablist"><button type="button" role="tab" data-tab="me" aria-selected="' + (S.tab === 'me') + '">My profile</button>'
        + '<button type="button" role="tab" data-tab="browse" aria-selected="' + (S.tab === 'browse') + '">Browse nurses</button></div>';
    }
    h += (S.tab === 'browse' ? drawBrowse() : drawMe(note)) + (S.canBrowse ? '' : RECRUITERS) + '</div>';
    mount.innerHTML = h;
    mount.querySelectorAll('[data-tab]').forEach(function (b) {
      b.addEventListener('click', function () {
        S.tab = b.getAttribute('data-tab');
        if (S.tab === 'browse' && !S.browse) { loadBrowse(); }
        render();
      });
    });
    if (S.tab === 'browse') { wireBrowse(); } else { wireMe(); }
  }

  if (!doc.getElementById('msh-nr-css')) {
    var st = doc.createElement('style');
    st.id = 'msh-nr-css'; st.textContent = CSS;
    doc.head.appendChild(st);
  }

  api('GET', '').then(function (r) {
    if (r.status === 401 || r.status === 403) {
      mount.innerHTML = LANDING;
      return;
    }
    if (!r.ok || !r.body || !r.body.options) { throw new Error('nurse-register ' + r.status); }
    take(r.body);
    render();
  }).catch(function () {
    mount.innerHTML = '<div class="nr"><h1>Nursing Register</h1><p class="lede">The register is unavailable just now. Please try again shortly.</p></div>';
  });
})(typeof window !== 'undefined' ? window : this);
