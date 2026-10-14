/* Medical Sales Register. Added 14/10/2026, modelled on the Nursing Register
   (app/nursing-register.js). Anyone working in medical sales, or moving into
   it, saves their experience, level and the roles they want; Hub Employers
   browse without names or contact details and ask for an introduction.

   Talks to /wp-json/msh/v1/sales-register (WPCode snippet from
   hub/wpcode/sales-register.php). The server is the authority: it cleans every
   save, decides who may browse, and never sends an employer a name, email,
   phone, LinkedIn or current employer unless the member ticked the share
   consent. The tick lists come from the server (options).

   Mounted into #msh-sales-register by hub/pages/sales-register.html.
   Loaded with new Function(); require()-able under node, where only the pure
   functions (_pure) are exercised: test_sales_register.py. */
(function (root) {
  'use strict';

  var API = '/wp-json/msh/v1/sales-register';
  var LISTS = ['rolesDone', 'roles', 'background', 'areas', 'customers', 'skills', 'qualifications'];
  var OPT_OF = { rolesDone: 'roles' };
  var FLAGS = ['relocate', 'overnights', 'driving', 'rightToWork', 'jobsEmail'];
  var FIELDS = ['region', 'area', 'travel', 'level', 'yearsInSales', 'currentRole', 'targetPct', 'achievement',
    'availability', 'notice', 'salary', 'bio', 'employer', 'phone', 'linkedin'];
  var WHY = {
    region: 'Choose the region you live in.',
    level: 'Choose the level you are at now.',
    roles: 'Tick at least one role you want next.',
    yearsInSales: 'Years in sales should be a whole number, for example 4.',
    targetPct: 'Enter last year\'s result against target as a number, for example 112.',
    linkedin: 'The LinkedIn link should look like https://www.linkedin.com/in/your-name',
    phone: 'Check the phone number.',
    consent: 'Tick the consent box to make your profile visible to employers.'
  };

  /* Where each fundamental comes from (14/10/2026): 14 live UK medical sales
     adverts read in full that day (Abbott, Alcon, Elekta, via the companies'
     own careers pages) and one specialist recruiter's registration form.
     Counts out of 14: travel 12, presentation 12, degree 11, healthcare or
     device sales experience 9, results against target 6, NHS knowledge 6,
     clinical setting 5, negotiation 5, business cases 5, customer relationship
     management systems 4. Right to work and a full driving licence are asked
     on the recruiter's form. Never add a claim here without a source. */
  var FUND_NOTE = 'We read 14 live UK medical sales adverts in October 2026, straight from the companies\' own careers pages. Most asked about travel, a degree, presentation skills and healthcare sales experience. Almost half asked for results against target and knowledge of the NHS. Answer these well and you answer a recruiter\'s first questions.';

  var PITCH = 'One profile, seen by the recruiters and employers who hire in medical sales. Tell us what you have sold, who you sold it to and where you want to go next, then let the right roles come to you.';
  var HOW = [
    ['Add your CV', 'We read it and fill in your roles, therapy areas, customers, skills and qualifications. The file is read on your device and never stored.'],
    ['Check it and add more', 'Untick anything wrong and tick what your CV leaves out. Most people have done more than their CV says.'],
    ['Answer the fundamentals', 'Travel, licence, right to work, results against target. The details recruiters ask first.'],
    ['Choose who sees you', 'Visible to approved employers without your name, or with your contact details. Hide or delete it any time.']
  ];
  var RECRUITERS = '<div class="sr-recruit"><div><p class="sr-eyebrow dark">For recruiters and employers</p>'
    + '<p>A Hub Employer subscription lets you search the register by region, level, role, therapy area and customer, and ask us to introduce you. One subscription covers this register and the Nursing Register. If you already use the Hub, it\'s an add-on to your account.</p></div>'
    + '<a class="sr-btn ghost" href="/hub-employer/">Become a Hub Employer</a></div>';

  /* ---------- pure ---------- */
  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function has(list, id) { return Array.isArray(list) && list.indexOf(id) !== -1; }

  /* Profiles an employer's filters keep. f: { region, level, role, area,
     customer, skill, availability, minYears, text }. Empty matches all.
     role matches a role wanted or done. availability: that or sooner. */
  var SOON = ['now', '1-month', '3-months', '6-months', 'exploring'];
  function filter(profiles, f, options) {
    f = f || {};
    var minY = parseInt(f.minYears, 10);
    var text = String(f.text || '').toLowerCase().trim();
    return (profiles || []).filter(function (p) {
      if (f.region && p.region !== f.region) { return false; }
      if (f.level && p.level !== f.level) { return false; }
      if (f.role && !has(p.roles, f.role) && !has(p.rolesDone, f.role)) { return false; }
      if (f.area && !has(p.areas, f.area)) { return false; }
      if (f.customer && !has(p.customers, f.customer)) { return false; }
      if (f.skill && !has(p.skills, f.skill)) { return false; }
      if (f.availability) {
        var want = SOON.indexOf(f.availability), got = SOON.indexOf(p.availability);
        if (got === -1 || got > want) { return false; }
      }
      if (!isNaN(minY) && (p.yearsInSales || 0) < minY) { return false; }
      if (text) {
        var hay = [p.ref, p.area, p.currentRole, p.bio, p.achievement].join(' ');
        if (options) {
          LISTS.forEach(function (k) {
            (p[k] || []).forEach(function (id) { hay += ' ' + ((options[OPT_OF[k] || k] || {})[id] || ''); });
          });
        }
        if (hay.toLowerCase().indexOf(text) === -1) { return false; }
      }
      return true;
    });
  }

  /* Live roles for one member: the role types they want, in their region
     or UK-wide (any region when they'd travel UK-wide). Each gets a score:
     in region 2, UK-wide 1; +1 when the level read from the title matches
     theirs. Highest first. Roles are { title, company, location, url,
     regions, type, level }. */
  function rolesFor(roles, p) {
    if (!p) { return []; }
    var anywhere = p.travel === 'national' || !!p.relocate;
    var out = [];
    (roles || []).forEach(function (r) {
      if (!has(p.roles, r.type)) { return; }
      var local = has(r.regions, p.region);
      var uk = !r.regions || !r.regions.length;
      if (!local && !uk && !anywhere) { return; }
      var score = local ? 2 : (uk ? 1 : 0);
      if (r.level && r.level === p.level) { score += 1; }
      out.push({ role: r, local: local, levelMatch: !!r.level && r.level === p.level, score: score });
    });
    out.sort(function (a, b) { return b.score - a.score || String(a.role.title).localeCompare(String(b.role.title)); });
    return out;
  }

  function daysLeft(updated, today, staleDays) {
    var a = Date.parse(updated + 'T00:00:00Z'), b = Date.parse(today + 'T00:00:00Z');
    if (isNaN(a) || isNaN(b)) { return null; }
    return staleDays - Math.floor((b - a) / 86400000);
  }

  /* What the CV suggests, added to what the member already has. Never
     removes a tick or overwrites a field they filled in. */
  var CV_LISTS = ['rolesDone', 'background', 'areas', 'customers', 'skills', 'qualifications'];
  var CV_FIELDS = ['yearsInSales', 'region'];
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

  var pure = { esc: esc, filter: filter, rolesFor: rolesFor, daysLeft: daysLeft, mergeSuggest: mergeSuggest };
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { _pure: pure };
    return;
  }

  /* ---------- browser ---------- */
  var doc = root.document;
  var mount = doc.getElementById('msh-sales-register');
  if (!mount) { return; }

  var S = { options: null, profile: null, canBrowse: false, isAdmin: false, staleDays: 365, tab: 'me', browse: null, roles: null, f: {} };

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
  function opts(k) { return (S.options || {})[OPT_OF[k] || k] || {}; }
  function label(k, id) { return opts(k)[id] || id; }

  /* Brand (00-Resources/brand-guide.md): navy #0B1C33, deep navy #14304F,
     gold #A8842C on light (borders, rules and large type only), #E0BE8E on
     navy, warm white #EDE7DC. Light text on navy, #1D2733 on light. */
  var CSS = '#msh-sales-register{font-family:Inter,Arial,sans-serif;color:#1D2733;font-size:15px;line-height:1.55;background:#F6F5F1}'
    + '.sr *{box-sizing:border-box}.sr-wrap{max-width:1080px;margin:0 auto;padding:0 40px}'
    + '.sr-hero{background:radial-gradient(1200px 500px at 85% -10%,rgba(224,190,142,.18),transparent 60%),linear-gradient(135deg,#0B1C33 0%,#14304F 100%);color:#F5F1E8;padding:72px 0 64px;position:relative;overflow:hidden}'
    + '.sr-hero:after{content:"";position:absolute;left:0;right:0;bottom:0;height:3px;background:linear-gradient(90deg,transparent,#E0BE8E,transparent)}'
    + '.sr-eyebrow{font-size:12px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#E0BE8E;margin:0 0 14px}.sr-eyebrow.dark{color:#14304F}'
    + '.sr h1{font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:48px;line-height:1.08;margin:0 0 18px;color:#FFFFFF;max-width:760px}'
    + '.sr-hero .lede{font-size:18px;color:#DBE3EE;max-width:680px;margin:0 0 28px}'
    + '.sr-btn{display:inline-block;background:#E0BE8E;color:#0B1C33;border:0;border-radius:6px;padding:13px 26px;font:700 15px Inter,Arial,sans-serif;cursor:pointer;text-decoration:none;letter-spacing:.01em}'
    + '.sr-btn:hover{background:#EDE7DC}.sr-btn.ghost{background:transparent;color:#14304F;border:1.5px solid #14304F}.sr-btn.ghost:hover{background:#14304F;color:#FFFFFF}'
    + '.sr-hero .sr-btn.ghost{color:#F5F1E8;border-color:#E0BE8E}.sr-hero .sr-btn.ghost:hover{background:#E0BE8E;color:#0B1C33}'
    + '.sr-btn.navy{background:#14304F;color:#FFFFFF}.sr-btn.navy:hover{background:#0B1C33}.sr-btn.danger{background:#FFFFFF;color:#8A1F22;border:1.5px solid #8A1F22}'
    + '.sr-actions{display:flex;gap:12px;flex-wrap:wrap;align-items:center}'
    + '.sr-band{padding:56px 0}.sr-band.white{background:#FFFFFF}'
    + '.sr h2{font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:30px;color:#14304F;margin:0 0 8px}'
    + '.sr .sub{color:#4A5666;max-width:720px;margin:0 0 28px}'
    + '.sr-steps{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;counter-reset:st}'
    + '.sr-step{background:#FFFFFF;border:1px solid #E2DED3;border-top:3px solid #A8842C;padding:22px 20px;counter-increment:st}'
    + '.sr-step:before{content:counter(st,decimal-leading-zero);display:block;font-family:"Source Serif 4",Georgia,serif;font-size:28px;font-weight:600;color:#A8842C;margin-bottom:6px}'
    + '.sr-step h3{font-size:16px;margin:0 0 6px;color:#14304F}.sr-step p{margin:0;font-size:14px;color:#3A4656}'
    + '.sr-recruit{display:flex;gap:24px;align-items:center;justify-content:space-between;border:1px solid #E2DED3;border-left:4px solid #A8842C;background:#FFFFFF;padding:22px 26px;margin:32px 0 0}'
    + '.sr-recruit p{margin:0;color:#1D2733;max-width:720px}'
    + '.sr-tabs{display:flex;gap:0;border-bottom:1px solid #D9D4C7;margin:0 0 28px;flex-wrap:wrap}'
    + '.sr-tabs button{background:none;border:0;border-bottom:3px solid transparent;padding:12px 18px;font:600 15px Inter,Arial,sans-serif;color:#4A5666;cursor:pointer;margin-bottom:-1px}'
    + '.sr-tabs button[aria-selected=true]{color:#14304F;border-bottom-color:#A8842C}'
    + '.sr fieldset{border:1px solid #E2DED3;background:#FFFFFF;margin:0 0 18px;padding:26px 28px}'
    + '.sr legend{font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:21px;color:#14304F;padding:0 8px;margin-left:-8px}'
    + '.sr .num{display:inline-block;min-width:30px;color:#A8842C}'
    + '.sr .hint{color:#4A5666;font-size:13.5px;margin:2px 0 14px}'
    + '.sr .lab{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#14304F;margin:18px 0 8px}'
    + '.sr .ticks{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:4px 18px}'
    + '.sr .ticks label,.sr .flag{display:flex;gap:9px;align-items:flex-start;font-size:14.5px;cursor:pointer;padding:5px 6px;border-radius:4px}'
    + '.sr .ticks label:hover,.sr .flag:hover{background:#F6F5F1}'
    + '.sr input[type=checkbox]{margin-top:3px;flex:none;accent-color:#14304F;width:16px;height:16px}'
    + '.sr .row{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px 18px;margin:0 0 10px}'
    + '.sr .row label{display:block;font-size:13px;font-weight:600;color:#3A4656}'
    + '.sr input[type=text],.sr input[type=number],.sr input[type=tel],.sr input[type=url],.sr select,.sr textarea{width:100%;border:1px solid #C9C5BA;border-radius:4px;padding:10px 12px;font:15px Inter,Arial,sans-serif;margin-top:5px;background:#FFFFFF;color:#1D2733}'
    + '.sr input:focus,.sr select:focus,.sr textarea:focus{outline:2px solid #14304F;outline-offset:1px}'
    + '.sr textarea{min-height:110px}'
    + '.sr .fund{border:1px solid #A8842C;background:linear-gradient(180deg,#FBF8F1,#FFFFFF)}'
    + '.sr .fund .note{background:#14304F;color:#F5F1E8;padding:14px 18px;font-size:14px;margin:4px 0 18px}'
    + '.sr .private{background:#F2F5F9}'
    + '.sr .cv{border:1.5px dashed #A8842C;background:#FFFFFF}.sr .cv input[type=file]{margin:8px 0 4px;font:14px Inter,Arial,sans-serif}'
    + '.sr label.fromcv{background:#FBF1D6}'
    + '.sr .msg{padding:12px 16px;margin:0 0 18px;font-size:14.5px;border-left:4px solid}'
    + '.sr .msg.ok{background:#E9F3EC;color:#1D5631;border-color:#2E7D4A}.sr .msg.bad{background:#FBEAEA;color:#8A1F22;border-color:#8A1F22}.sr .msg.info{background:#EEF2F7;color:#14304F;border-color:#14304F}'
    + '.sr .chips{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 10px}'
    + '.sr .chip{background:#EEF2F7;color:#14304F;border-radius:3px;padding:3px 9px;font-size:12.5px;text-decoration:none}'
    + '.sr .chip.gold{background:#F6EEDC;color:#5B4A1E}.sr .chip.ok{background:#E9F3EC;color:#1D5631}.sr .chip.warn{background:#FBEAEA;color:#8A1F22}'
    + '.sr .card{background:#FFFFFF;border:1px solid #E2DED3;padding:22px 24px;margin:0 0 14px}'
    + '.sr .card h3{margin:0 0 4px;font-size:18px;color:#14304F}.sr .meta{color:#3A4656;font-size:14px;margin:0 0 10px}'
    + '.sr .filters{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;margin:0 0 18px}'
    + '.sr .job{display:flex;justify-content:space-between;gap:16px;align-items:center;background:#FFFFFF;border:1px solid #E2DED3;padding:16px 20px;margin:0 0 10px}'
    + '.sr .job a.t{font-weight:700;color:#14304F;text-decoration:none;font-size:16px}.sr .job a.t:hover{text-decoration:underline}'
    + '.sr .job .m{color:#4A5666;font-size:13.5px;margin-top:2px}'
    + '.sr .done .links{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 8px}'
    + '@media (max-width:860px){.sr-steps{grid-template-columns:1fr 1fr}}'
    + '@media (max-width:600px){.sr-wrap{padding:0 20px}.sr h1{font-size:34px}.sr-hero{padding:52px 0 44px}.sr-steps{grid-template-columns:1fr}.sr fieldset{padding:18px}.sr-recruit{flex-direction:column;align-items:flex-start}.sr .job{flex-direction:column;align-items:flex-start}}';

  function hero(signedIn) {
    return '<section class="sr-hero"><div class="sr-wrap"><p class="sr-eyebrow">Medical Sales Hub &middot; Talent</p>'
      + '<h1>The Medical Sales Register</h1><p class="lede">' + PITCH + '</p>'
      + (signedIn ? '' : '<div class="sr-actions"><a class="sr-btn" href="/register/">Join and register</a><a class="sr-btn ghost" href="/login/?redirect_to=' + encodeURIComponent(root.location ? root.location.pathname : '/') + '">Log in to register</a></div>')
      + '</div></section>';
  }
  function steps() {
    return '<div class="sr-steps">' + HOW.map(function (s) { return '<div class="sr-step"><h3>' + s[0] + '</h3><p>' + s[1] + '</p></div>'; }).join('') + '</div>';
  }
  var LANDING_BODY = '<section class="sr-band"><div class="sr-wrap"><h2>How it works</h2>'
    + '<p class="sub">Territory managers, key account managers, clinical specialists, trainers, sales managers, product managers, market access and directors: every commercial role in medical sales, at every level, including people moving in from clinical or other sales careers.</p>'
    + steps()
    + '</div></section><section class="sr-band white"><div class="sr-wrap"><h2>What you get</h2>'
    + '<div class="sr-steps" style="counter-reset:none">'
    + '<div class="sr-step" style="counter-increment:none"><h3>Found, not filed</h3><p>Recruiters and employers search by region, level, role, therapy area and the customers you sell to.</p></div>'
    + '<div class="sr-step" style="counter-increment:none"><h3>Roles every Tuesday</h3><p>New roles in your region, grouped by role type and level, straight from the companies\' own careers pages.</p></div>'
    + '<div class="sr-step" style="counter-increment:none"><h3>Roles for you</h3><p>A live list of roles matched to the jobs you want, ranked by region and level.</p></div>'
    + '<div class="sr-step" style="counter-increment:none"><h3>You stay in control</h3><p>Anonymous by default. Share your contact details only if you choose. Hide or delete any time.</p></div>'
    + '</div>' + RECRUITERS + '</div></section>';

  function ticks(k, chosen) {
    var o = opts(k), h = '<div class="ticks">';
    Object.keys(o).forEach(function (id) {
      var cv = S.fromCv && has(S.fromCv[k], id);
      h += '<label' + (cv ? ' class="fromcv" title="Found in your CV"' : '') + '><input type="checkbox" name="' + k + '" value="' + esc(id) + '"' + (has(chosen, id) ? ' checked' : '') + '><span>' + esc(o[id]) + '</span></label>';
    });
    return h + '</div>';
  }
  function select(k, name, cur, blank) {
    var o = opts(k), h = '<select name="' + name + '"><option value="">' + esc(blank) + '</option>';
    Object.keys(o).forEach(function (id) {
      h += '<option value="' + esc(id) + '"' + (cur === id ? ' selected' : '') + '>' + esc(o[id]) + '</option>';
    });
    return h + '</select>';
  }
  function flag(name, on, text) {
    return '<label class="flag"><input type="checkbox" name="' + name + '"' + (on ? ' checked' : '') + '><span>' + text + '</span></label>';
  }
  var nFs = 0;
  function fs(title, hint, inner, cls) {
    nFs++;
    return '<fieldset' + (cls ? ' class="' + cls + '"' : '') + '><legend><span class="num">' + ('0' + nFs).slice(-2) + '</span>' + title + '</legend>' + (hint ? '<p class="hint">' + hint + '</p>' : '') + inner + '</fieldset>';
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
    nFs = 0;
    var h = statusBox(S.profile) + '<form id="sr-form" novalidate>';
    h += fs('Start with your CV', 'Upload your CV as a PDF or Word file and we\'ll fill in as much as we can. It\'s read on your device; the file itself isn\'t uploaded or kept.',
      '<input type="file" id="sr-cv" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document">'
      + '<p class="hint" id="sr-cv-status" aria-live="polite">' + (S.cvNote || 'No CV to hand? Fill in the form below instead.') + '</p>', 'cv');
    h += fs('Where you are and your level', 'Employers see your region and the area you give here. Put a county or nearest city, never your address.',
      '<div class="row"><label>Region' + select('regions', 'region', p.region, 'Choose your region') + '</label>'
      + '<label>Area<input type="text" name="area" maxlength="60" placeholder="e.g. Leeds, or North Yorkshire" value="' + esc(p.area) + '"></label>'
      + '<label>Your level now' + select('levels', 'level', p.level, 'Choose your level') + '</label>'
      + '<label>Years in sales<input type="number" name="yearsInSales" min="0" max="50" placeholder="e.g. 4" value="' + esc(p.yearsInSales) + '"></label>'
      + '<label>Current job title<input type="text" name="currentRole" maxlength="80" placeholder="e.g. Territory Manager, Wound Care" value="' + esc(p.currentRole) + '"></label></div>');
    h += fs('The roles you want next', 'Tick every role you\'d consider. Your weekly email and your "Roles for you" list follow these.', ticks('roles', p.roles));
    h += fs('Your experience', 'Roles you\'ve done, where you came from, and what you\'ve sold.',
      '<p class="lab">Roles you\'ve done</p>' + ticks('rolesDone', p.rolesDone)
      + '<p class="lab">Your background</p>' + ticks('background', p.background)
      + '<p class="lab">Therapy and product areas</p>' + ticks('areas', p.areas)
      + '<p class="lab">Customers you\'ve sold to</p>' + ticks('customers', p.customers));
    h += fs('The fundamentals recruiters look for', '',
      '<div class="note">' + FUND_NOTE + '</div>'
      + '<div class="row"><label>How far you\'d travel' + select('travel', 'travel', p.travel, 'Choose') + '</label>'
      + '<label>Last full year against target (%)<input type="number" name="targetPct" min="0" max="500" placeholder="e.g. 112" value="' + esc(p.targetPct) + '"></label>'
      + '<label>When you could start' + select('availability', 'availability', p.availability, 'Choose') + '</label>'
      + '<label>Notice period' + select('notice', 'notice', p.notice, 'Choose') + '</label>'
      + '<label>Base salary you\'re looking for' + select('salary', 'salary', p.salary, 'Choose') + '</label></div>'
      + '<label class="row" style="display:block"><span style="font-size:13px;font-weight:600;color:#3A4656">Your best result, in one line</span><input type="text" name="achievement" maxlength="200" placeholder="e.g. Grew territory 34% in 2025; won a two-year trust contract" value="' + esc(p.achievement) + '"></label>'
      + flag('driving', p.driving, 'Full UK driving licence')
      + flag('rightToWork', p.rightToWork, 'Right to work in the UK')
      + flag('overnights', p.overnights, 'Happy with overnight stays')
      + flag('relocate', p.relocate, 'I\'d relocate for the right role')
      + '<p class="lab">Skills</p>' + ticks('skills', p.skills)
      + '<p class="lab">Qualifications</p>' + ticks('qualifications', p.qualifications), 'fund');
    h += fs('About you', 'A few lines in your own words: what you\'re proud of, and what you want next. Don\'t include your name or contact details; they\'re removed if you do.',
      '<textarea name="bio" maxlength="600">' + esc(p.bio) + '</textarea><p class="hint" id="sr-count"></p>');
    h += fs('Private: only Elevate &amp; Thrive sees this', 'Shared with an employer only if you tick "Let recruiters contact me directly" below. Your name and email come from your Hub account.',
      '<div class="row"><label>Current employer<input type="text" name="employer" maxlength="80" value="' + esc(p.employer) + '"></label>'
      + '<label>Phone<input type="tel" name="phone" maxlength="20" value="' + esc(p.phone) + '"></label>'
      + '<label>LinkedIn<input type="url" name="linkedin" maxlength="160" placeholder="https://www.linkedin.com/in/..." value="' + esc(p.linkedin) + '"></label></div>', 'private');
    h += fs('Weekly jobs email', 'Every Tuesday: new roles in your region and UK-wide roles, grouped by role type and level, from the companies\' own careers pages. Nothing new, no email.',
      flag('jobsEmail', p.jobsEmail, '<strong>Send me the weekly jobs email</strong> for my region. I can unsubscribe from any email.'));
    h += fs('Who can see you', '',
      flag('consent', !!p.consentAt, 'I agree that Elevate &amp; Thrive may show this profile, without my name or contact details, to recruiters and employers it has approved, and contact me when one asks to be introduced. I can hide or delete it at any time.')
      + flag('shareContact', p.shareContact, '<strong>Let recruiters contact me directly.</strong> I agree that Elevate &amp; Thrive may share my name, email, phone number, LinkedIn and current employer with the recruiters and employers it has approved, so they can contact me about roles. I can untick this at any time.')
      + flag('visible', p.visible, '<strong>Make my profile visible to employers</strong>')
      + '<p class="hint" style="margin-top:10px">Profiles not confirmed for a year are hidden automatically.</p>');
    h += '<div class="sr-actions"><button class="sr-btn navy" type="submit">Save my profile</button>'
      + (S.profile ? '<button class="sr-btn danger" type="button" id="sr-delete">Delete my profile</button>' : '') + '</div></form>';
    h += '<div id="sr-done" class="done" style="margin-top:22px">' + (note || '') + '</div>';
    return h;
  }

  function doneBox(emailed) {
    var links = S.links || [];
    var h = '<div class="msg ok"><strong>Thank you, your profile is submitted.</strong> '
      + (emailed ? 'We\'ve emailed a copy of your choices to you.' : 'We couldn\'t send the confirmation email just now, but your profile is saved.') + '</div>'
      + '<p class="lab">Your next steps</p><div class="links"><button class="sr-btn navy" type="button" data-tab="roles">See roles for you</button>';
    links.filter(function (l) { return l.main; }).forEach(function (l) {
      h += '<a class="sr-btn ghost" href="' + esc(l.url) + '">' + esc(l.label) + '</a>';
    });
    h += '</div><div class="chips">';
    links.filter(function (l) { return !l.main; }).forEach(function (l) {
      h += '<a class="chip" href="' + esc(l.url) + '">' + esc(l.label) + '</a>';
    });
    return h + '</div>';
  }

  /* ---------- CV reading (same libraries as the Nursing Register) ---------- */
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
    FIELDS.forEach(function (n) {
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
    var form = doc.getElementById('sr-form');
    var bio = form.elements.bio, count = doc.getElementById('sr-count');
    function n() { count.textContent = (600 - bio.value.length) + ' characters left'; }
    bio.addEventListener('input', n); n();
    var cvIn = doc.getElementById('sr-cv'), cvSay = doc.getElementById('sr-cv-status');
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
          ? '<strong>We\'ve filled in ' + m.count + ' thing' + (m.count === 1 ? '' : 's') + ' from your CV</strong>, highlighted in gold. Check each one and untick anything that\'s wrong, then tick anything you\'ve done that isn\'t on your CV.'
          : 'We read your CV but couldn\'t match anything to the lists below. Please tick what applies to you.';
        render();
        var at = doc.getElementById('sr-cv-status');
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
          var done = doc.getElementById('sr-done');
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
    var del = doc.getElementById('sr-delete');
    if (del) {
      del.addEventListener('click', function () {
        if (!root.confirm('Delete your register profile? Employers will no longer see it and the weekly jobs email stops. This can\'t be undone.')) { return; }
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
    var form = doc.getElementById('sr-form');
    form.parentNode.insertBefore(d, form);
    d.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  /* ---------- roles for you ---------- */
  function drawRoles() {
    if (!S.profile) { return '<div class="msg info">Save your profile first, with the roles you want next, and we\'ll match live roles to you here.</div>'; }
    if (!S.roles) { return '<p>Loading live roles...</p>'; }
    if (S.roles.error) { return '<div class="msg bad">Live roles are unavailable just now. Please try again shortly.</div>'; }
    var list = rolesFor(S.roles.roles, S.profile);
    var h = '<h2>Roles for you</h2><p class="sub">Live roles from the companies\' own careers pages, matched to the roles you want, in ' + esc(label('regions', S.profile.region))
      + ' or UK-wide' + (S.profile.travel === 'national' || S.profile.relocate ? ', and anywhere in the UK because you\'d travel or relocate' : '') + '. Role type and level are read from each job title, so check the advert for the detail.'
      + (S.roles.generatedOn ? ' Careers pages last read ' + esc(S.roles.generatedOn) + '.' : '') + '</p>';
    if (!list.length) {
      return h + '<div class="msg info">No live roles match right now. Tick more roles you\'d consider, or widen how far you\'d travel. You\'ll also get new ones by email if you\'ve ticked the weekly jobs email.</div>'
        + '<a class="sr-btn ghost" href="/medical-sales-hub/careers/">See every role on the Career Centre</a>';
    }
    list.forEach(function (m) {
      var r = m.role;
      h += '<div class="job"><div><a class="t" href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.title) + '</a>'
        + '<div class="m">' + esc(r.company) + (r.location ? ' &middot; ' + esc(r.location) : '') + '</div>'
        + '<div class="chips" style="margin:6px 0 0"><span class="chip">' + esc(label('roles', r.type)) + '</span>'
        + (r.level ? '<span class="chip' + (m.levelMatch ? ' ok' : '') + '">' + esc(label('levels', r.level)) + '</span>' : '')
        + (m.local ? '<span class="chip gold">In your region</span>' : '<span class="chip">UK-wide or elsewhere</span>') + '</div></div>'
        + '<a class="sr-btn ghost" href="' + esc(r.url) + '" target="_blank" rel="noopener">View advert</a></div>';
    });
    return h + '<p style="margin-top:18px"><a class="sr-btn ghost" href="/medical-sales-hub/careers/">See every role on the Career Centre</a></p>';
  }
  function loadRoles() {
    api('GET', '/roles').then(function (r) {
      S.roles = r.ok && r.body && Array.isArray(r.body.roles) ? r.body : { error: true };
      if (S.tab === 'roles') { render(); }
    });
  }

  /* ---------- browse (Hub Employers) ---------- */
  function card(p) {
    var meta = [label('levels', p.level)];
    if (p.yearsInSales !== null && p.yearsInSales !== undefined && p.yearsInSales !== '') { meta.push(p.yearsInSales + ' year' + (p.yearsInSales === 1 ? '' : 's') + ' in sales'); }
    if (p.targetPct !== null && p.targetPct !== undefined && p.targetPct !== '') { meta.push(p.targetPct + '% of target last full year (self-declared)'); }
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
    if (p.availability) { badges += '<span class="chip">' + esc(label('availability', p.availability)) + '</span>'; }
    if (p.notice) { badges += '<span class="chip">Notice: ' + esc(label('notice', p.notice)) + '</span>'; }
    if (p.salary) { badges += '<span class="chip">Base: ' + esc(label('salary', p.salary)) + '</span>'; }
    if (p.driving) { badges += '<span class="chip">UK driving licence</span>'; }
    if (p.rightToWork) { badges += '<span class="chip">Right to work in UK</span>'; }
    if (p.overnights) { badges += '<span class="chip">Overnights fine</span>'; }
    if (p.hidden) { badges += '<span class="chip warn">Hidden from employers</span>'; }

    var h = '<div class="card" data-ref="' + esc(p.ref) + '"><h3>' + esc(p.ref) + (p.currentRole ? ': ' + esc(p.currentRole) : '') + '</h3>'
      + '<p class="meta">' + esc(meta.join(' · ')) + '<br>' + esc(where.join(' · ')) + '</p>'
      + (badges ? '<div class="chips">' + badges + '</div>' : '')
      + '<p class="lab">Wants</p>' + chips('roles')
      + ((p.rolesDone || []).length ? '<p class="lab">Has done</p>' + chips('rolesDone') : '')
      + ((p.areas || []).length ? '<p class="lab">Therapy and product areas</p>' + chips('areas', 'gold') : '')
      + ((p.customers || []).length ? '<p class="lab">Sells to</p>' + chips('customers', 'gold') : '')
      + ((p.skills || []).length || (p.qualifications || []).length ? '<p class="lab">Skills and qualifications</p>' + chips('skills') + chips('qualifications') : '')
      + (p.achievement ? '<p style="margin:10px 0 0"><strong>Best result:</strong> ' + esc(p.achievement) + '</p>' : '')
      + (p.bio ? '<p style="margin:10px 0 0">' + esc(p.bio) + '</p>' : '');
    if (S.isAdmin && p.private) {
      var q = p.private;
      h += '<div class="msg info" style="margin-top:12px"><strong>Admin only.</strong> ' + esc(q.name) + ' · ' + esc(q.email)
        + (q.phone ? ' · ' + esc(q.phone) : '') + (q.employer ? ' · ' + esc(q.employer) : '')
        + (q.linkedin ? ' · <a href="' + esc(q.linkedin) + '" target="_blank" rel="noopener">LinkedIn</a>' : '')
        + ' · last saved ' + esc(q.updated) + '</div>';
    }
    if (p.contact) {
      var c = p.contact;
      h += '<div class="msg ok" style="margin-top:12px"><strong>Happy to be contacted directly.</strong> ' + esc(c.name)
        + ' · <a href="mailto:' + esc(c.email) + '">' + esc(c.email) + '</a>'
        + (c.phone ? ' · ' + esc(c.phone) : '') + (c.employer ? ' · ' + esc(c.employer) : '')
        + (c.linkedin ? ' · <a href="' + esc(c.linkedin) + '" target="_blank" rel="noopener">LinkedIn</a>' : '') + '</div>';
    } else if (!p.hidden) {
      h += '<div class="sr-actions" style="margin-top:12px"><button class="sr-btn navy" type="button" data-intro>Request introduction</button></div>';
    }
    return h + '</div>';
  }

  function drawBrowse() {
    if (!S.browse) { return '<p>Loading the register...</p>'; }
    var f = S.f;
    var h = '<h2>Browse the register</h2><p class="sub">Everyone here has chosen to be seen. Where someone has agreed to direct contact, their details are on their card. For everyone else, ask for an introduction and we\'ll check with them first, then put you in touch.</p>'
      + '<div class="filters">'
      + select('regions', 'region', f.region, 'Any region')
      + select('levels', 'level', f.level, 'Any level')
      + select('roles', 'role', f.role, 'Any role')
      + select('areas', 'area', f.area, 'Any therapy area')
      + select('customers', 'customer', f.customer, 'Any customer')
      + select('skills', 'skill', f.skill, 'Any skill')
      + select('availability', 'availability', f.availability, 'Any start date')
      + '<input type="number" name="minYears" min="0" max="50" placeholder="Min. years in sales" value="' + esc(f.minYears) + '">'
      + '<input type="text" name="text" placeholder="Search" value="' + esc(f.text) + '"></div>';
    var list = filter(S.browse, f, S.options);
    h += '<p class="hint">' + list.length + ' of ' + S.browse.length + ' profile' + (S.browse.length === 1 ? '' : 's') + '</p>';
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
          + '<div class="sr-actions" style="margin-top:10px"><button class="sr-btn navy" type="button">Send request</button><span class="hint"></span></div>';
        b.parentNode.replaceWith(wrap);
        var send = wrap.querySelector('button'), note = wrap.querySelector('.hint');
        send.addEventListener('click', function () {
          send.disabled = true; note.textContent = 'Sending...';
          api('POST', '/intro', { ref: ref, message: wrap.querySelector('textarea').value }).then(function (r) {
            if (r.ok) { wrap.innerHTML = '<div class="msg ok">Request sent. We\'ll check with them and come back to you.</div>'; return; }
            send.disabled = false;
            note.textContent = r.status === 429 ? 'You\'ve reached today\'s limit of introduction requests. Try again tomorrow.' : 'That didn\'t send. Please try again.';
          });
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
    var tabs = [['me', 'My profile'], ['roles', 'Roles for you']];
    if (S.canBrowse) { tabs.push(['browse', 'Browse the register']); }
    var h = '<div class="sr">' + hero(true) + '<section class="sr-band"><div class="sr-wrap">';
    if (S.tab === 'me' && !S.profile) { h += '<h2>How it works</h2><p class="sub">Have your CV to hand.</p>' + steps() + '<div style="height:36px"></div>'; }
    h += '<div class="sr-tabs" role="tablist">' + tabs.map(function (t) {
      return '<button type="button" role="tab" data-tab="' + t[0] + '" aria-selected="' + (S.tab === t[0]) + '">' + t[1] + '</button>';
    }).join('') + '</div>';
    h += S.tab === 'browse' ? drawBrowse() : S.tab === 'roles' ? drawRoles() : drawMe(note);
    h += (S.canBrowse ? '' : RECRUITERS) + '</div></section></div>';
    mount.innerHTML = h;
    mount.querySelectorAll('[data-tab]').forEach(function (b) {
      b.addEventListener('click', function () {
        S.tab = b.getAttribute('data-tab');
        if (S.tab === 'browse' && !S.browse) { loadBrowse(); }
        if (S.tab === 'roles' && !S.roles) { loadRoles(); }
        render();
        var t = mount.querySelector('.sr-tabs');
        if (t) { t.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      });
    });
    if (S.tab === 'browse') { wireBrowse(); } else if (S.tab === 'me') { wireMe(); }
  }

  if (!doc.getElementById('msh-sr-css')) {
    var st = doc.createElement('style');
    st.id = 'msh-sr-css'; st.textContent = CSS;
    doc.head.appendChild(st);
  }

  api('GET', '').then(function (r) {
    if (r.status === 401 || r.status === 403) {
      mount.innerHTML = '<div class="sr">' + hero(false) + LANDING_BODY + '</div>';
      return;
    }
    if (!r.ok || !r.body || !r.body.options) { throw new Error('sales-register ' + r.status); }
    take(r.body);
    render();
  }).catch(function () {
    mount.innerHTML = '<div class="sr">' + hero(true) + '<section class="sr-band"><div class="sr-wrap"><p>The register is unavailable just now. Please try again shortly.</p></div></section></div>';
  });
})(typeof window !== 'undefined' ? window : this);
