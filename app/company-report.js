/* Medical Sales Hub — Company Report (Stages 1–5)
   Mounts on #msh-company-report. Member types or picks a company; the page
   renders one report card, and Stage 5 turns that card into a printable
   interview pack — one document per supplier, sectioned by speciality.

   SPEC: docs/COMPANY-REPORT-METHOD.md. That document was written before this
   code and governs it — if this file and that document disagree, THIS FILE IS
   WRONG. Read it before changing anything below the Stage 2 divider.

   Stage 1 panels are READ FROM SOURCE (supplier-index.json merged with the
   human-curated supplier-seed.json). Stage 3 is also read from source
   (data/company-financials.json — Companies House facts, manual interim until
   the API key exists). Stages 2 and 4 are DERIVED, so per root rule 14 each
   one prints the rule it was derived under, refuses to fire on thin evidence,
   and has an honest empty state naming what is missing. Stage 5 adds no new
   claims: it re-presents panels 1–4, and a refused panel stays refused in the
   printed pack — named, never blanked.

   WHAT THIS FILE STILL DELIBERATELY DOES NOT DO
   ---------------------------------------------
   No market-share percentage, ever, and no arithmetic that could become one.
   Stage 4 publishes a FILING PROFILE: the count on the lot and each confirmed
   supplier's statutory accounts filing. Only matchConfidence === "confirmed"
   records feed it; a probable name-search match is shown as identity-not-
   confirmed and carries no figures. Inventing more than that is precisely the
   class of error that put 145 false job changes in front of paying members on
   24/07/2026. An absent panel here means "not built yet" or "refused on thin
   evidence" — the panel says which — never "nothing found". */
(function () {
  var MOUNT = document.getElementById('msh-company-report');
  if (!MOUNT) return;

  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var CB = '?cb=' + Date.now();
  var IDX = BASE + 'data/supplier-index.json' + CB;
  var SEED = BASE + 'data/supplier-seed.json' + CB;
  var SPECMAP = BASE + 'data/speciality-map.json' + CB;
  var PRODUCTS = BASE + 'data/supplier-products.json' + CB;
  var FIN = BASE + 'data/company-financials.json' + CB;
  var NHSSC = BASE + 'data/nhssc-cache.json' + CB;
  var FWDATA = BASE + 'data/frameworks.json' + CB;

  /* Same palette constants as app/supplier-search.js — one house style. */
  var G = '#a8842c', INK = '#1d2733', DIM = '#75808d', LINE = '#e6e0d4',
      RED = '#b84a5c', GREEN = '#2e7d5b', SOFT = '#f7f4ee';

  /* Speciality lists run to the low hundreds. Rendering 164 names is not a
     report, it is a phone book — so the list is capped and the cap is stated
     in the prose next to the true total, never silently applied. */
  var MAX_SPEC_ROWS = 24;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim(); }

  /* Company-name key for matching OUR supplier records against the names NHS
     Supply Chain prints on its own contract launch briefs. The two vocabularies
     were never the same: the briefs say "GBUK Ltd", "GBUK Healthcare",
     "GBUK Enteral Limited" for one group we hold as "GBUK Group".
     Deliberately shallow — it drops only legal-form and generic trade words.
     Stripping more would start merging genuinely different companies, and
     medtech is full of similarly-named entities. */
  var CO_SUFFIX = /\b(ltd|limited|plc|llp|inc|corp|corporation|co|company|group|holdings|international|uk|u k|gb|healthcare|health care|health|medical|medica|med|products|solutions|systems|technologies|technology|devices|device)\b/g;
  function coKey(s) {
    var k = norm(s).replace(CO_SUFFIX, ' ');
    return k.replace(/\s+/g, ' ').trim();
  }
  function cmpName(a, b) {
    var x = String(a || '').toLowerCase(), y = String(b || '').toLowerCase();
    return x < y ? -1 : (x > y ? 1 : 0);
  }

  function sec(title, html) {
    return '<div style="margin:16px 0 0;">' +
      '<div style="font-size:11px;letter-spacing:1.4px;text-transform:uppercase;font-weight:700;color:' + DIM + ';margin-bottom:6px;">' + title + '</div>' +
      html + '</div>';
  }
  /* Every honest empty state goes through here, so they all look the same and
     none of them can be mistaken for a zero finding. */
  function gap(text) {
    return '<div style="font-size:13px;color:' + DIM + ';line-height:1.55;">' + text + '</div>';
  }
  function good(text) {
    return '<div style="font-size:13px;color:' + GREEN + ';line-height:1.55;">' + text + '</div>';
  }
  /* The printed derivation. Stage 2 panels are computed claims; this box is
     the reader's means of judging them. It is not decoration — do not drop it
     to save space. */
  function rule(text) {
    return '<div style="margin:0 0 9px;padding:8px 11px;background:' + SOFT + ';border-left:3px solid ' + G + ';border-radius:0 7px 7px 0;font-size:12px;color:#4a5766;line-height:1.55;">' +
      '<b style="color:' + G + ';letter-spacing:.06em;">HOW THIS WAS DERIVED</b><br>' + text + '</div>';
  }

  /* ---------------------------------------------------------------------
     Merge: index + human-curated seed.
     Same rule as app/meeting-prep.js — supplier-seed.json is human-owned and
     is never overwritten by the index build, so where the seed has a curated
     value it wins; a supplier present only in the seed is unioned in so a new
     entry shows immediately, independent of the refresh cadence.
     --------------------------------------------------------------------- */
  function mergeSuppliers(index, seed) {
    var suppliers = (index && index.suppliers) ? index.suppliers.slice() : [];
    var seedList = (seed && seed.suppliers) || [];
    var seedMap = {};
    seedList.forEach(function (s) { seedMap[s.name] = s; });
    suppliers.forEach(function (s) {
      var sd = seedMap[s.name];
      if (!sd) return;
      if (sd.voice) s.voice = sd.voice;
      if (sd.note) s.note = sd.note;
      if (sd.image) s.image = sd.image;
      if (sd.deepDive) s.deepDive = sd.deepDive;
      if (sd.brand) s.brand = sd.brand;
      if (sd.products && sd.products.length) s.products = sd.products;
      if (sd.frameworks && sd.frameworks.length) s.frameworks = sd.frameworks;
      if (sd.specialities && sd.specialities.length) s.specialities = sd.specialities;
    });
    var have = {};
    suppliers.forEach(function (s) { have[s.name] = 1; });
    seedList.forEach(function (s) { if (!have[s.name]) { s.curated = true; suppliers.push(s); } });
    return suppliers;
  }

  /* ---------------------------------------------------------------------
     Speciality canonicalisation — lifted from app/meeting-prep.js on purpose.
     Three speciality vocabularies had drifted apart and were being matched by
     exact string equality, so a lookup miss came back as an EMPTY LIST. On a
     panel like "Same speciality, no shared framework" an empty list reads as
     "nobody else sells this", when the truth was "the lookup failed". That is
     a false finding dressed as a finding, so the same reconciliation is used
     here. It falls back to exact matching if the map cannot be loaded, and
     says so in the panel when it does.
     --------------------------------------------------------------------- */
  function specCtx(specMap, prodFile) {
    var CANON = (specMap && specMap.canonicalSpecialities) || null;
    var SMAP = (specMap && specMap.supplierSpecialityMap) || null;
    var PRODS = (prodFile && prodFile.suppliers) || null;
    var LABEL_TO_ID = {}, ID_TO_LABEL = {};
    if (CANON) CANON.forEach(function (c) { LABEL_TO_ID[c.label] = c.id; ID_TO_LABEL[c.id] = c.label; });

    function verifiedRangeFor(name) {
      if (!PRODS || !name) return null;
      if (PRODS[name]) return PRODS[name];
      for (var k in PRODS) {
        var al = PRODS[k].aliases || [];
        if (al.indexOf(name) !== -1) return PRODS[k];
      }
      return null;
    }
    /* A supplier string may map to SEVERAL canonical ids where it genuinely
       spans both, so a supplier stays reachable from either side of its real
       market rather than an arbitrary single pick. Child specialities roll up
       into their parent (blood collection sits under vascular access, with a
       different buying stakeholder) — without the rollup, picking the parent
       silently misses every child-only supplier. */
    function canonIds(list) {
      var out = {};
      (list || []).forEach(function (s) {
        var m = SMAP && SMAP[s];
        if (m && m.to) m.to.forEach(function (id) { out[id] = 1; });
        else if (LABEL_TO_ID[s]) out[LABEL_TO_ID[s]] = 1;
      });
      if (CANON) CANON.forEach(function (c) { if (c.parent && out[c.parent]) out[c.id] = 1; });
      return Object.keys(out);
    }
    /* A supplier's specialities and its verified product tags were
       unconnected, so a supplier could sell a whole category and still be
       unreachable from it. Deriving the extra ids from the tagged range fixes
       that without editing the curated seed. */
    function supplierSpecIds(s) {
      var ids = canonIds(s && s.specialities);
      var v = verifiedRangeFor(s && s.name);
      if (v) {
        var seen = {};
        ids.forEach(function (i) { seen[i] = 1; });
        (v.products || []).forEach(function (p) { if (p.s) seen[p.s] = 1; });
        ids = Object.keys(seen);
      }
      return ids;
    }
    function sharedWith(subIds, other) {
      var B = supplierSpecIds(other), out = [];
      subIds.forEach(function (id) { if (B.indexOf(id) !== -1) out.push(id); });
      return out;
    }
    return {
      canonical: !!SMAP,
      count: CANON ? CANON.length : 0,
      label: function (id) { return ID_TO_LABEL[id] || id; },
      ids: supplierSpecIds,
      shared: sharedWith
    };
  }

  /* Exact-string fallback, used only when speciality-map.json is unreachable.
     Named separately so the panel can say which route produced the list. */
  function rawShared(sub, other) {
    var a = (sub && sub.specialities) || [], b = (other && other.specialities) || [], out = [];
    a.forEach(function (x) { if (b.indexOf(x) !== -1) out.push(x); });
    return out;
  }

  /* ---------------------------------------------------------------------
     STAGE 1 — read from source, nothing computed.
     --------------------------------------------------------------------- */
  function chip(text, tone) {
    var bg = tone === 'gold' ? '#f3ead2' : '#ffffff';
    var fg = tone === 'gold' ? '#7a5b14' : '#37485a';
    var bd = tone === 'gold' ? '#f3ead2' : LINE;
    return '<span style="display:inline-block;background:' + bg + ';color:' + fg + ';border:1px solid ' + bd +
      ';border-radius:99px;padding:3px 10px;font-size:11.5px;font-weight:600;margin:0 6px 6px 0;">' + esc(text) + '</span>';
  }

  function identity(s) {
    /* Image with monogram fallback — copied from supplier-search.js so the two
       tools cannot drift apart visually. */
    var _w = String(s.name || '').replace(/^the\s+/i, '').split(/[\s\-—,\.]+/).filter(Boolean);
    var inits = esc((/^[A-Za-z0-9]{2,4}$/.test(_w[0] || '') ? _w[0] : _w.slice(0, 2).map(function (w) { return w[0]; }).join('')).toUpperCase());
    var ph = '<div style="width:56px;height:56px;flex:0 0 56px;border-radius:10px;background:#efe9db;border:1px solid ' + LINE + ';display:flex;align-items:center;justify-content:center;font-weight:700;color:' + G + ';font-size:16px;">' + inits + '</div>';
    var thumb = s.image
      ? '<img src="' + esc(s.image) + '" alt="" referrerpolicy="no-referrer" loading="lazy" style="width:56px;height:56px;flex:0 0 56px;border-radius:10px;object-fit:contain;background:#fff;border:1px solid ' + LINE + ';" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';"><div style="display:none;width:56px;height:56px;flex:0 0 56px;border-radius:10px;background:#efe9db;border:1px solid ' + LINE + ';align-items:center;justify-content:center;font-weight:700;color:' + G + ';font-size:16px;">' + inits + '</div>'
      : ph;
    var h = '<div style="display:flex;gap:13px;align-items:flex-start;">' + thumb + '<div><div style="font-size:21px;font-weight:700;color:' + INK + ';line-height:1.25;">' + esc(s.name) +
      (s.autoDetected ? ' <span style="font-size:10px;font-weight:700;letter-spacing:.06em;color:#7a5b14;background:#f3e8cf;border-radius:99px;padding:2px 8px;vertical-align:3px;">AUTO — VERIFY AT SOURCE</span>' : '') + '</div>' +
      (s.note ? '<p style="margin:5px 0 0;font-size:13.5px;color:#37485a;line-height:1.55;">' + esc(s.note) + '</p>' : '') +
      '</div></div>';

    if (s.specialities && s.specialities.length) {
      h += '<div style="margin-top:9px;">' + s.specialities.map(function (x) { return chip(x, 'gold'); }).join('') + '</div>';
    } else {
      h += '<div style="margin-top:9px;">' + gap('No speciality recorded for this company yet.') + '</div>';
    }

    if (s.voice && (s.voice.line || s.voice.angle)) {
      h += sec('How they sell', '<div style="font-size:13.5px;color:#37485a;line-height:1.6;">' +
        (s.voice.angle ? '<b style="color:' + INK + ';">' + esc(s.voice.angle) + '</b><br>' : '') +
        esc(s.voice.line || '') + '</div>');
    }
    return h;
  }

  /* ---------------------------------------------------------------------
     PRODUCT LISTING — scope set by Lou, 06/08/2026:
       tier 1  catalogue-verified — rows read from the NHS Supply Chain
               catalogue (NPC code, description, pack), via nhssc-cache.json;
       tier 2  also supply, not on a framework — items confirmed on the
               company's own website but absent from the catalogue
               (nhssc-cache notCatalogue, with the reason recorded);
       tier 3  the deep verified range where a full site crawl exists
               (supplier-products.json — GBUK so far), grouped by the
               company's own divisions;
       plus the curated headline products from the index, which for most of
       the 459 suppliers is currently ALL we hold — and the panel says so
       rather than letting five chips read as a complete range.
     --------------------------------------------------------------------- */
  function cacheRowsFor(s, cache) {
    var out = { items: [], notCat: [] };
    if (!cache) return out;
    var names = {}; names[s.name] = 1;
    (s.aliases || []).forEach(function (a) { names[a] = 1; });
    var prods = cache.products || {};
    for (var k in prods) {
      var rec = prods[k];
      if (rec && names[rec.supplier]) {
        (rec.items || []).forEach(function (it) { out.items.push(it); });
      }
    }
    var nc = cache.notCatalogue || {};
    for (var k2 in nc) {
      var r2 = nc[k2];
      if (r2 && names[r2.supplier]) out.notCat.push({ name: k2, reason: r2.reason || '' });
    }
    return out;
  }

  function deepRangeFor(s, prodFile) {
    var P = (prodFile && prodFile.suppliers) || null;
    if (!P) return null;
    if (P[s.name]) return P[s.name];
    for (var k in P) {
      if ((P[k].aliases || []).indexOf(s.name) !== -1) return P[k];
    }
    return null;
  }

  function productListing(s, ctx) {
    var cr = cacheRowsFor(s, ctx.cache);
    var deep = deepRangeFor(s, ctx.prodFile);
    var body = '';

    /* Coverage statement first, built from the same arrays rendered below,
       so the claim about completeness cannot drift from the rows. */
    var bits = [];
    if (cr.items.length) {
      var _n = {};
      cr.items.forEach(function (it) { _n[it.npc || (it.name + '|' + it.desc)] = 1; });
      bits.push(Object.keys(_n).length + ' catalogue-verified line(s)');
    }
    if (cr.notCat.length) bits.push(cr.notCat.length + ' item(s) confirmed off-catalogue');
    if (deep) bits.push((deep.products || []).length + ' product(s) from a full crawl of the company’s own site' + (deep.verified ? ' (verified ' + esc(deep.verified) + ')' : ''));
    if (bits.length) {
      body += '<div style="font-size:12px;color:' + DIM + ';margin:0 0 8px;">' + bits.join(' · ') + '.</div>';
    }

    if (cr.items.length) {
      /* The cache is keyed by SEARCH QUERY, so one catalogue line is reached by
         several queries and arrives several times: 113 rows for GBUK held only
         85 distinct NPCs. The NPC is the catalogue's own product code, so it is
         the identity. Dedupe on it, then group by the catalogue's product name
         and sort, because an unsorted table with repeats is not a listing. */
      var byNpc = {}, order = [];
      cr.items.forEach(function (it) {
        var k = it.npc || (it.name + '|' + it.desc);
        if (!byNpc[k]) { byNpc[k] = it; order.push(k); }
      });
      var uniq = order.map(function (k) { return byNpc[k]; });
      var fams = {}, famOrder = [];
      uniq.forEach(function (it) {
        var f = it.name || 'Other';
        if (!fams[f]) { fams[f] = []; famOrder.push(f); }
        fams[f].push(it);
      });
      famOrder.sort(cmpName);

      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:8px 0 4px;">In the NHS Supply Chain catalogue &mdash; verified entries</div>' +
        '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 8px;">' + uniq.length + ' distinct catalogue lines across ' + famOrder.length +
        ' product families, grouped by the catalogue&rsquo;s own product name and sorted. ' +
        (cr.items.length !== uniq.length ? (cr.items.length - uniq.length) + ' duplicate rows removed (the same NPC reached by more than one search). ' : '') +
        'The catalogue does not state which framework each line sits on, so these are grouped by product family, not by framework; the framework list above is the sourced answer to that question.</div>';

      body += famOrder.map(function (fam) {
        var rows = fams[fam].slice().sort(function (a, b) { return cmpName(a.desc, b.desc); }).map(function (it) {
          return '<tr>' +
            '<td style="padding:5px 8px;border-bottom:1px solid #f0ece3;font-size:12.5px;color:#37485a;">' + esc(it.desc) + '</td>' +
            '<td style="padding:5px 8px;border-bottom:1px solid #f0ece3;font-size:12px;color:' + G + ';font-weight:600;white-space:nowrap;">' + esc(it.npc) + '</td>' +
            '<td style="padding:5px 8px;border-bottom:1px solid #f0ece3;font-size:12px;color:' + DIM + ';white-space:nowrap;">' + esc(it.pack) + '</td>' +
            '</tr>';
        }).join('');
        return '<div style="margin:0 0 10px;border:1px solid ' + LINE + ';border-radius:8px;background:#fff;overflow:hidden;">' +
          '<div style="padding:7px 10px;background:' + SOFT + ';font-size:12.5px;font-weight:700;color:' + INK + ';border-bottom:1px solid ' + LINE + ';">' +
          esc(fam) + ' <span style="font-weight:400;color:' + DIM + ';">&middot; ' + fams[fam].length + ' line(s)</span></div>' +
          '<div style="overflow-x:auto;"><table style="border-collapse:collapse;width:100%;min-width:460px;">' +
          '<tr><th style="text-align:left;padding:6px 8px;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">CATALOGUE DESCRIPTION</th>' +
          '<th style="text-align:left;padding:6px 8px;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">NPC</th>' +
          '<th style="text-align:left;padding:6px 8px;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">PACK</th></tr>' +
          rows + '</table></div></div>';
      }).join('');
    }

    if (cr.notCat.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:12px 0 4px;">Also supply — not in the NHSSC catalogue</div>' +
        '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 6px;">Confirmed on the company’s own site or in its published range, absent from the catalogue — typically capital equipment or direct-supply lines. The recorded reason is shown; “not on a framework yet” is a statement about the catalogue, not about the product.</div>' +
        cr.notCat.map(function (n) {
          return '<div style="padding:6px 0;border-bottom:1px solid #f0ece3;font-size:13px;"><b style="color:' + INK + ';">' + esc(n.name) + '</b>' +
            (n.reason ? ' <span style="color:' + DIM + ';">· ' + esc(n.reason) + '</span>' : '') + '</div>';
        }).join('');
    }

    if (deep && deep.divisions && deep.divisions.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:12px 0 4px;">Full verified range, by the company’s own divisions</div>' +
        (deep.filingRule ? '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 6px;">' + esc(deep.filingRule) + '</div>' : '') +
        deep.divisions.map(function (d) {
          return '<div style="padding:6px 0;border-bottom:1px solid #f0ece3;font-size:13px;"><b style="color:' + INK + ';">' + esc(d.name) + '</b>' +
            ' <span style="color:' + DIM + ';">· ' + d.products + ' product(s)' +
            (d.specialities && d.specialities.length ? ' · ' + d.specialities.map(esc).join(', ') : '') + '</span></div>';
        }).join('') +
        (deep.notSold ? '<div style="font-size:11.5px;color:#8a4a58;margin:6px 0 0;"><b>Verified absences:</b> ' + esc(deep.notSold) + '</div>' : '');
    }

    if (s.products && s.products.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:12px 0 4px;">Headline products (curated)</div>' +
        s.products.map(function (p) { return chip(typeof p === 'string' ? p : (p && p.n) || '', ''); }).join('');
    }

    if (!body) {
      return sec('Products', gap('No product or brand indexed for this company yet — the range has not been captured, which is not the same as a company with no products.'));
    }

    /* The honest partial: headline chips alone are NOT a product listing. */
    if (!cr.items.length && !deep) {
      body += '<div style="font-size:11.5px;color:' + DIM + ';margin-top:8px;">The full listing for this company has not been captured yet: no catalogue match has been run and no site crawl exists. What is above is the curated headline set, not the range.</div>';
    }
    return sec('Products', body);
  }

  /* ---------------------------------------------------------------------
     FRAMEWORKS — read from NHS Supply Chain's own contract launch briefs
     (data/frameworks.json), not from our hand-curated tags.

     This replaced a hand-curated list that was badly incomplete: GBUK Group
     carried two frameworks while NHSSC's own briefs name it on twenty-four.
     That mattered beyond this panel, because the competitor panels are derived
     from framework co-listing — an incomplete framework list produced an
     incomplete competitor list, stated with the same confidence.
     --------------------------------------------------------------------- */
  function fwIndex(fwDoc) {
    var byKey = {};
    ((fwDoc && fwDoc.frameworks) || []).forEach(function (f) {
      (f.suppliers || []).forEach(function (nm) {
        var k = coKey(nm);
        if (!k) return;
        if (!byKey[k]) byKey[k] = [];
        byKey[k].push({ fw: f, matched: nm });
      });
    });
    return byKey;
  }

  /* Every framework whose brief names this company, under any of its recorded
     names. The verbatim string the brief used is kept and shown — a group that
     appears as "GBUK Enteral Limited" on one framework and "GBUK Ltd" on
     another is a fact about the register, not noise to tidy away. */
  function supplierFrameworks(s, ctx) {
    if (!ctx.fwByKey) return [];
    var keys = {}, out = [], seen = {};
    [s.name].concat(s.aliases || []).forEach(function (n) {
      var k = coKey(n);
      if (k) keys[k] = 1;
    });
    Object.keys(keys).forEach(function (k) {
      (ctx.fwByKey[k] || []).forEach(function (hit) {
        if (seen[hit.fw.url]) {
          if (seen[hit.fw.url].matched.indexOf(hit.matched) === -1) {
            seen[hit.fw.url].matched.push(hit.matched);
          }
          return;
        }
        seen[hit.fw.url] = { fw: hit.fw, matched: [hit.matched] };
        out.push(seen[hit.fw.url]);
      });
    });
    out.sort(function (a, b) { return cmpName(a.fw.name, b.fw.name); });
    return out;
  }

  function frameworks(s, ctx) {
    var hits = supplierFrameworks(s, ctx);
    var curated = (s.frameworks || []);

    if (!hits.length && !curated.length) {
      return sec('Frameworks', gap('No NHS Supply Chain contract launch brief names this company, and nothing is curated for it. Plenty of ranges are sold direct, off framework, and NHS Supply Chain is only one buying route, so read this as "not named on the briefs captured so far", never as proof they hold no place anywhere.'));
    }

    var body = '';
    if (hits.length) {
      body += rule('Every framework below names this company <b>on NHS Supply Chain&rsquo;s own contract launch brief</b> for that framework, the buying organisation&rsquo;s own page, captured ' +
        esc((ctx.fwDoc && ctx.fwDoc.dataAsOf) || 'date not recorded') + '. Nothing here is inferred from product ranges or specialities. The name in brackets is the exact wording the brief uses, which is often a group company rather than the group.' +
        (ctx.fwDoc && ctx.fwDoc.unparsedCount
          ? ' <b>Coverage:</b> ' + ctx.fwDoc.frameworkCount + ' of ' + (ctx.fwDoc.briefsSeen || 0) +
            ' published briefs parsed; ' + ctx.fwDoc.unparsedCount + ' refused because the supplier list did not match the count the page itself states. A framework in that group cannot appear here even if this company is on it.'
          : ''));

      body += '<div style="font-size:12px;color:' + DIM + ';margin:0 0 8px;">' + hits.length + ' framework(s) name this company.</div>';

      body += hits.map(function (h) {
        var f = h.fw;
        var lots = (f.supplierLots || {});
        var myLots = [];
        h.matched.forEach(function (m) { if (lots[m]) { myLots = myLots.concat(lots[m]); } });
        return '<div style="padding:9px 0;border-bottom:1px solid #f0ece3;font-size:13.5px;line-height:1.55;">' +
          '<b>' + esc(f.name) + '</b>' +
          ' <span style="color:' + DIM + ';">(as &ldquo;' + h.matched.map(esc).join('&rdquo;, &ldquo;') + '&rdquo;)</span>' +
          '<br><span style="font-size:12.5px;color:#37485a;">' +
          (f.category ? esc(f.category) + ' &middot; ' : '') +
          (f.reference ? 'ref ' + esc(f.reference) + ' &middot; ' : '') +
          (f.starts ? esc(f.starts) : '') + (f.ends ? ' to ' + esc(f.ends) : '') +
          (f.supplyRoute ? ' &middot; ' + esc(f.supplyRoute) : '') +
          '</span>' +
          '<br><span style="font-size:12.5px;color:' + DIM + ';">' + f.supplierCount + ' suppliers on this framework' +
          (myLots.length ? ' &middot; this company on ' + myLots.map(esc).join(', ') : '') +
          ' &middot; <a href="' + esc(f.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">contract launch brief &#8599;</a></span>' +
          '</div>';
      }).join('');
    }

    if (curated.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:14px 0 4px;">Also tracked by hand</div>' +
        '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 6px;">Tender-watch notes: re-tender values, award criteria and award dates, which the launch briefs do not carry. Curated, not read from a brief.</div>' +
        curated.map(function (f) {
          return '<div style="padding:8px 0;border-bottom:1px solid #f0ece3;font-size:13.5px;line-height:1.55;"><b>' + esc(f.name) + '</b>' +
            (f.value ? ' <span style="color:' + GREEN + ';font-weight:700;">' + esc(f.value) + '</span>' : '') +
            (f.dates ? ' <span style="color:' + DIM + ';">&middot; ' + esc(f.dates) + '</span>' : '') +
            (f.note ? '<br><span style="color:#37485a;font-size:12.5px;">' + esc(f.note) + '</span>' : '') + '</div>';
        }).join('');
    }
    return sec('Frameworks', body);
  }

  function alerts(s) {
    if (!(s.alerts && s.alerts.length)) {
      return sec('Alerts &amp; recalls', good('No current alert indexed for this company.'));
    }
    return sec('Alerts &amp; recalls', s.alerts.map(function (a) {
      /* 169 of the indexed alerts are plain strings (a curated research note)
         rather than the {date,title,detail} object. Rendering a string through
         the object path prints an empty date and an empty title, so the two
         shapes are handled separately. */
      if (typeof a === 'string') {
        return '<div style="padding:9px 11px;margin:0 0 7px;border-left:3px solid ' + LINE + ';background:#fff;border-radius:7px;font-size:13px;color:#37485a;line-height:1.6;">' + esc(a) + '</div>';
      }
      return '<div style="padding:9px 11px;margin:0 0 7px;border-left:3px solid ' + RED + ';background:#fff;border-radius:7px;font-size:13px;line-height:1.55;">' +
        '<b style="color:' + RED + ';">' + esc(a.date) + '</b> — <b>' + esc(a.title) + '</b>' +
        '<br><span style="color:#37485a;">' + esc(a.detail) + '</span>' +
        (a.use ? '<br><span style="color:' + G + ';">▸ ' + esc(a.use) + '</span>' : '') +
        (a.url ? ' <a href="' + esc(a.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">source ↗</a>' : '') +
        '</div>';
    }).join(''));
  }

  function press(s) {
    var all = s.news || [];
    /* The heading asserts two sources. A story carrying one would make that
       heading a false claim, so it is filtered out here rather than trusted to
       have been filtered upstream, and the drop is stated. */
    var ok = all.filter(function (n) { return ((n && n.sources) || []).length >= 2; });
    var dropped = all.length - ok.length;
    if (!ok.length) {
      return sec('Press · verified by 2+ sources',
        gap(all.length
          ? 'No story for this company clears the two-source bar. ' + all.length + ' single-sourced item(s) were held back rather than shown here.'
          : 'No corroborated press indexed. A story appears here only once two independent reputable outlets carry it, so an empty panel means nothing has cleared that bar — not that nothing was written.'));
    }
    var body = ok.map(function (nw) {
      var srcs = (nw.sources || []).map(function (x) {
        return x.url
          ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">' + esc(x.publisher) + ' ↗</a>'
          : esc(x.publisher);
      }).join(' · ');
      return '<div style="padding:8px 0;border-bottom:1px solid #f0ece3;font-size:13px;line-height:1.55;">' +
        '<span style="color:' + GREEN + ';font-weight:700;">✓</span> <b>' + esc(nw.headline) + '</b>' +
        (nw.date ? ' <span style="color:' + DIM + ';">· ' + esc(nw.date) + '</span>' : '') +
        '<br><span style="color:' + DIM + ';font-size:12px;">Corroborated by: </span>' + srcs + '</div>';
    }).join('');
    if (dropped > 0) {
      body += '<div style="font-size:12px;color:' + DIM + ';margin-top:6px;">' + dropped + ' further item(s) held back — single-sourced.</div>';
    }
    return sec('Press · verified by 2+ sources', body);
  }

  /* =====================================================================
     STAGE 2 — DERIVED. Everything below carries its rule and its floor.
     ===================================================================== */

  /* Frameworks the subject holds, keyed on a normalised name. Framework names
     are recorded free-text across 459 supplier records, so an exact-string key
     would split "NHS Supply Chain — IV Cannula" from the same framework typed
     with a hyphen and quietly halve every co-listing. */
  function fwList(s) {
    var out = [], seen = {};
    (s.frameworks || []).forEach(function (f) {
      var nm = f && f.name;
      if (!nm) return;
      var k = norm(nm);
      if (!k || seen[k]) return;
      seen[k] = 1;
      out.push({ name: nm, key: k });
    });
    return out;
  }
  function holdsFramework(rec, key) {
    var fs = (rec && rec.frameworks) || [];
    for (var i = 0; i < fs.length; i++) { if (fs[i] && norm(fs[i].name) === key) return true; }
    return false;
  }

  /* Returns either a renderable set of groups, or a refusal carrying the
     reason. It never returns a half-answer: the whole panel is withheld if any
     rendered name fails to resolve, per the method doc's invariant. */
  function coListing(sub, ctx) {
    var hits = supplierFrameworks(sub, ctx);
    if (!hits.length) return { ok: false, why: 'nofw' };
    var asOf = (ctx.fwDoc && ctx.fwDoc.dataAsOf) || '';
    /* A co-listing that cannot say when it was read is an undated claim. */
    if (!asOf) return { ok: false, why: 'nodate' };

    var groups = [], thin = [];
    hits.forEach(function (h) {
      var f = h.fw;
      var all = f.suppliers || [];
      /* EVIDENCE FLOOR. One supplier on a framework is a framework with one
         supplier, not a competitive field. */
      if (all.length < 2) { thin.push(f.name); return; }
      var mine = {};
      h.matched.forEach(function (m) { mine[String(m).toLowerCase()] = 1; });
      var others = all.filter(function (n) { return !mine[String(n).toLowerCase()]; });
      others.sort(cmpName);
      groups.push({
        name: f.name, total: all.length, others: others, url: f.url,
        reference: f.reference, ends: f.ends, lots: f.supplierLots || null
      });
    });
    if (!groups.length) return { ok: false, why: 'thin', thin: thin };
    return { ok: true, groups: groups, thin: thin, asOf: asOf };
  }

  function panelCoListed(sub, ctx, res) {
    var TITLE = 'Also on this framework';
    if (!res.ok) {
      if (res.why === 'nofw') {
        return sec(TITLE, gap('No NHS Supply Chain contract launch brief captured so far names ' + esc(sub.name) + ', so there is nothing to co-list. Ranges sold direct, off framework, appear on no brief at all, and NHS Supply Chain is only one buying route. Read this as a gap in what has been captured, not as a company standing alone in its market.'));
      }
      if (res.why === 'nodate') {
        return sec(TITLE, gap('The framework capture arrived without a capture date. A co-listing that cannot say when the data was read is an undated claim, so this panel is withheld.'));
      }
      var names = (res.thin || []).map(function (n) { return '<b>' + esc(n) + '</b>'; }).join(', ');
      return sec(TITLE, gap('Not shown. ' + esc(sub.name) + ' is named on ' + (res.thin || []).length +
        ' framework(s) &mdash; ' + names + ' &mdash; each naming only one supplier, which is a framework with only one supplier on it rather than a field, so the panel does not render.'));
    }

    var body = rule('Every company below is named on the <b>same NHS Supply Chain contract launch brief</b> as ' +
      esc(sub.name) + ', that framework&rsquo;s own page on NHS Supply Chain, captured <b>' + esc(res.asOf) + '</b>. ' +
      'The list is the brief&rsquo;s list in full, minus this company: it is not filtered down to the companies this Hub happens to hold records for, so a name here may have no Hub profile yet. ' +
      'Where the brief breaks the framework into lots, the lot is shown; otherwise the match is at framework level, so check the lot before you use it in a call. ' +
      'Sharing a framework is not the same as competing: a framework can carry companies selling into entirely different clinical niches, and a genuine competitor may be on no framework at all.');

    res.groups.forEach(function (grp) {
      /* The count in the prose comes from the same array rendered beneath it,
         so prose and list cannot drift apart. */
      var known = grp.others.filter(function (n) {
        return !!(ctx.byName[n] || (ctx.byKey && ctx.byKey[coKey(n)]));
      }).length;
      body += '<div style="margin:0 0 12px;border:1px solid ' + LINE + ';border-radius:10px;padding:11px 13px;background:#fff;">' +
        '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';">' + esc(grp.name) + '</div>' +
        '<div style="font-size:12px;color:' + DIM + ';margin:3px 0 8px;">' + grp.others.length +
        ' other supplier(s) on this framework &middot; ' + grp.total + ' in total, including ' + esc(sub.name) + '.' +
        (grp.reference ? ' &middot; ref ' + esc(grp.reference) : '') +
        (grp.ends ? ' &middot; runs to ' + esc(grp.ends) : '') +
        ' &middot; <a href="' + esc(grp.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">brief &#8599;</a></div>' +
        '<div>' + grp.others.map(function (n) {
          var lots = grp.lots && grp.lots[n];
          var hub = ctx.byName[n] || (ctx.byKey && ctx.byKey[coKey(n)]);
          return chip(n + (lots && lots.length ? ' &middot; ' + lots.join(', ') : ''), hub ? 'gold' : '');
        }).join('') + '</div>' +
        '<div style="font-size:11px;color:' + DIM + ';margin-top:7px;">' + known + ' of these ' + grp.others.length +
        ' have a profile in this Hub (gold); the rest are named on the brief but not yet indexed here.</div>' +
        '</div>';
    });

    if (res.thin && res.thin.length) {
      body += gap('Held back: ' + res.thin.map(function (n) { return esc(n); }).join(', ') +
        ' &mdash; each naming only one supplier, which is below the evidence floor for this panel.');
    }
    return sec(TITLE, body);
  }

  /* Same speciality, no shared framework. A SEPARATE list — never merged into
     the panel above, because "sells into the same clinical area" and "is on the
     same piece of paper" are different claims and a reader must be able to tell
     which one they are looking at. */
  function panelSameSpeciality(sub, ctx, coRes) {
    var TITLE = 'Same speciality, no shared framework';

    /* Everyone already named above is excluded, so a company appears in one
       list or the other, never both. */
    var already = {};
    already[sub.name] = 1;
    if (coRes.ok) {
      coRes.groups.forEach(function (g) { g.others.forEach(function (n) { already[n] = 1; }); });
    }

    var subIds = ctx.spec.ids(sub);
    var usingCanon = ctx.spec.canonical;
    if (usingCanon && !subIds.length) {
      return sec(TITLE, gap('No speciality for ' + esc(sub.name) + ' could be reconciled against the canonical speciality map, so this list cannot be built. That is a lookup gap — treat it as "not looked up", never as "nobody else sells this".'));
    }
    if (!usingCanon && !((sub.specialities || []).length)) {
      return sec(TITLE, gap('No speciality is recorded for ' + esc(sub.name) + ', so there is nothing to match on.'));
    }

    var rows = [];
    ctx.all.forEach(function (o) {
      if (already[o.name]) return;
      var shared = usingCanon ? ctx.spec.shared(subIds, o) : rawShared(sub, o);
      if (!shared.length) return;
      rows.push({
        name: o.name,
        labels: shared.map(function (id) { return usingCanon ? ctx.spec.label(id) : id; }),
        fwCount: fwList(o).length
      });
    });
    rows.sort(function (a, b) { return cmpName(a.name, b.name); });

    if (!rows.length) {
      return sec(TITLE, gap('Nothing to show. Every indexed supplier sharing a speciality with ' + esc(sub.name) +
        ' also shares a framework with them and is already named above — or no other indexed supplier covers these specialities at all. Coverage is the tracked-supplier set, so this is a statement about what is indexed, not about the market.'));
    }

    var shown = rows.slice(0, MAX_SPEC_ROWS);
    var body = rule('Companies below share at least one speciality with ' + esc(sub.name) +
      ' and are on <b>none</b> of the frameworks listed above. ' +
      (usingCanon
        ? 'Specialities are reconciled through the canonical speciality map (' + ctx.spec.count + ' canonical specialities), because the free-text speciality strings across supplier records were never one vocabulary — matching them literally returns an empty list that reads as "no one else", when what actually happened is that the lookup missed.'
        : 'The canonical speciality map could not be loaded, so this fell back to matching speciality strings exactly. That under-reports: read this list as a floor, not a field.') +
      ' A shared speciality is not a shared market — it means both sell somewhere inside the same clinical area.');

    body += '<div style="font-size:12px;color:' + DIM + ';margin:0 0 8px;">' +
      rows.length + ' indexed supplier(s) match. ' +
      (rows.length > shown.length ? ('The ' + shown.length + ' listed below are the first ' + shown.length + ' alphabetically.') : ('All ' + shown.length + ' are listed below.')) +
      '</div>';

    body += shown.map(function (r) {
      return '<div style="padding:8px 0;border-bottom:1px solid #f0ece3;font-size:13px;line-height:1.5;">' +
        '<b style="color:' + INK + ';">' + esc(r.name) + '</b>' +
        '<span style="color:' + DIM + ';"> · ' + (r.fwCount ? r.fwCount + ' framework(s) indexed, none shared with ' + esc(sub.name) : 'no framework indexed') + '</span>' +
        '<br>' + r.labels.map(function (l) { return chip(l, 'gold'); }).join('') +
        '</div>';
    }).join('');

    return sec(TITLE, body);
  }

  /* =====================================================================
     STAGE 3 — Companies House facts, READ FROM SOURCE.
     data/company-financials.json is a manual interim (public register read
     by hand, 06/08/2026) until COMPANIES_HOUSE_KEY exists; its `coverage`
     field says exactly which companies it holds. Everything rendered here is
     a register fact with its source link. Nothing is computed.
     ===================================================================== */
  function finRecFor(s, fin) {
    var C = (fin && fin.companies) || null;
    if (!C) return null;
    if (C[s.name]) return C[s.name];
    var al = s.aliases || [];
    for (var k in C) { if (al.indexOf(k) !== -1) return C[k]; }
    return null;
  }
  function isProbable(rec) {
    return String((rec && rec.matchConfidence) || '').toLowerCase() === 'probable';
  }

  function fact(label, value) {
    return '<tr><td style="padding:4px 10px 4px 0;font-size:12px;color:' + DIM + ';white-space:nowrap;vertical-align:top;">' + label + '</td>' +
      '<td style="padding:4px 0;font-size:13px;color:' + INK + ';line-height:1.5;">' + value + '</td></tr>';
  }

  function panelCompanyFacts(s, ctx) {
    var TITLE = 'Company facts · Companies House';
    var fin = ctx.fin;
    if (!fin) {
      return sec(TITLE, gap('Companies House facts are not loaded — the financials feed was unreachable. Nothing is missing from the register; the page could not read it.'));
    }
    var rec = finRecFor(s, fin);
    if (!rec) {
      return sec(TITLE, gap('Not yet fetched for this company. The current file is a manual interim covering ' +
        esc(fin.coverage || 'a small set of companies') +
        ' The full register fetch runs when the Companies House API key arrives — absence here is a coverage gap, not a company without filings.'));
    }

    var probable = isProbable(rec);
    var rows = '';
    if (rec.registeredName) rows += fact('Registered name', '<b>' + esc(rec.registeredName) + '</b>' + (rec.companyNumber ? ' · ' + esc(rec.companyNumber) : ''));
    if (rec.status) rows += fact('Status', esc(rec.status));
    if (rec.incorporated) rows += fact('Incorporated', esc(rec.incorporated));
    if (rec.registeredOffice) rows += fact('Registered office', esc(rec.registeredOffice));
    if (rec.sic && rec.sic.length) rows += fact('SIC', rec.sic.map(esc).join(', '));
    if (rec.accountsFilingVerbatim) rows += fact('Latest accounts', esc(rec.accountsFilingVerbatim));

    /* Turnover has three honest states and they must not blur:
       a figure (with its made-up-to date), disclosed-but-not-extracted, or
       not disclosed at all (legally permitted below the small thresholds). */
    if (!probable) {
      if (rec.turnoverGBP != null) {
        rows += fact('Turnover', '£' + Number(rec.turnoverGBP).toLocaleString('en-GB') +
          ' <span style="color:' + DIM + ';">· accounts made up to ' + esc(rec.accountsMadeUpTo || '') + '</span>');
      } else if (rec.turnoverNote) {
        rows += fact('Turnover', '<span style="color:' + DIM + ';">' + esc(rec.turnoverNote) + '</span>');
      } else {
        rows += fact('Turnover', '<span style="color:' + DIM + ';">not disclosed in the filed accounts (legally permitted)</span>');
      }

      /* Headcount is tagged far more often than turnover — small companies must
         disclose it even when they omit the profit and loss account — so it is
         frequently the only size figure this report can show at all. */
      if (rec.employees != null) {
        rows += fact('Employees', esc(String(rec.employees)) +
          (rec.employeesNote ? ' <span style="color:' + DIM + ';">· ' + esc(rec.employeesNote) + '</span>' : ''));
      } else if (rec.employeesNote) {
        rows += fact('Employees', '<span style="color:' + DIM + ';">' + esc(rec.employeesNote) + '</span>');
      }
    }

    var body = '';
    if (probable) {
      body += '<div style="margin:0 0 9px;padding:8px 11px;background:#f7ecdc;border-left:3px solid #b98a2e;border-radius:0 7px 7px 0;font-size:12px;color:#6b5518;line-height:1.55;">' +
        '<b>IDENTITY NOT CONFIRMED.</b> This is a probable match only — ' + esc(rec.matchedOn || 'matched by name search') +
        ' Register facts are shown for orientation; no figure is carried and this company is excluded from the field filing profile below.</div>';
    } else if (rec.matchedOn) {
      body += '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 8px;">Matched on: ' + esc(rec.matchedOn) + '</div>';
    }
    body += rows ? ('<table style="border-collapse:collapse;">' + rows + '</table>') : gap('The record carries no register facts.');
    if (rec.sourceUrl) {
      body += '<div style="font-size:11.5px;margin-top:7px;"><a href="' + esc(rec.sourceUrl) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">Companies House record ↗</a>' +
        ' <span style="color:' + DIM + ';">· read ' + esc(fin.dataAsOf || '') + '</span></div>';
    }
    return sec(TITLE, body);
  }

  /* Officers — statutory register facts, dated events only. The file's own
     note is printed with the list: nobody is ever said to have replaced
     anybody, because succession is not a register fact and asserting it is
     the 24/07/2026 error with different names in it. */
  function panelPeople(s, ctx) {
    var TITLE = 'Notable people · statutory register';
    var rec = ctx.fin ? finRecFor(s, ctx.fin) : null;
    var off = rec && rec.officers;
    if (!off) {
      return sec(TITLE, gap('Officer data has not been fetched for this company yet. It comes from the Companies House officers register (public), company by company — absence here is a coverage gap, not a company without directors.'));
    }
    var body = off.note ? '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 8px;">' + esc(off.note) + '</div>' : '';
    if (off.current && off.current.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:4px 0 4px;">Current officers</div>' +
        off.current.map(function (o) {
          return '<div style="padding:5px 0;border-bottom:1px solid #f0ece3;font-size:13px;"><b style="color:' + INK + ';">' + esc(o.name) + '</b>' +
            ' <span style="color:' + DIM + ';">· ' + esc(o.role) + ' · appointed ' + esc(o.appointed) + '</span></div>';
        }).join('');
    }
    if (off.recentChanges && off.recentChanges.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:12px 0 4px;">Recent changes</div>' +
        off.recentChanges.map(function (o) {
          var col = o.event === 'appointed' ? GREEN : '#8a4a58';
          return '<div style="padding:5px 0;border-bottom:1px solid #f0ece3;font-size:13px;"><b style="color:' + col + ';">' + esc(o.event) + '</b>' +
            ' <b style="color:' + INK + ';">' + esc(o.name) + '</b>' +
            ' <span style="color:' + DIM + ';">· ' + esc(o.role) + ' · ' + esc(o.date) + '</span></div>';
        }).join('');
    }
    if (off.sourceUrl) {
      body += '<div style="font-size:11.5px;margin-top:7px;"><a href="' + esc(off.sourceUrl) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">Officers register ↗</a>' +
        ' <span style="color:' + DIM + ';">· read ' + esc(off.readOn || '') + '</span></div>';
    }
    return sec(TITLE, body || gap('The officers record is empty.'));
  }

  /* =====================================================================
     STAGE 4 — FIELD FILING PROFILE. DERIVED, and the most restrained panel
     on the page. It answers "how big are the players on this lot" with the
     only two things we can actually source: the count on the lot, and each
     CONFIRMED supplier's statutory accounts filing. It never prints a
     percentage and never invents a rank.
     ===================================================================== */
  function panelFieldProfile(sub, ctx, coRes) {
    var TITLE = 'Field filing profile';
    if (!ctx.fin) {
      return sec(TITLE, gap('Not built for this view — the company financials feed was unreachable, and a size comparison without the filings is a guess.'));
    }
    if (!coRes.ok) {
      return sec(TITLE, gap('Withheld, because the framework co-listing above is withheld — this panel profiles that field, and there is no field to profile.'));
    }

    var body = rule('For each framework above: every supplier whose identity is <b>confirmed</b> against a Companies House record (matchConfidence === "confirmed") is listed with the exact wording of its most recent accounts filing on the public register. ' +
      'Suppliers whose identity is only probable, or who file outside the UK, are named as unresolved and feed nothing. ' +
      'The panel refuses any framework where fewer than half the suppliers resolve — a size comparison built on a third of the lot is not a size comparison. ' +
      'No percentage appears here because nobody holds market-share data: what a filing tells you is which statutory regime the company files under (thresholds quoted below), not its share of anything. ' +
      'Register read ' + esc(ctx.fin.dataAsOf || 'date not recorded') + '; framework data captured ' + esc(ctx.asOf) + '.');

    var rendered = 0;
    coRes.groups.forEach(function (grp) {
      var everyone = [sub.name].concat(grp.others);
      var resolved = [], unresolved = [];
      everyone.forEach(function (n) {
        var rec = ctx.byName[n] || (ctx.byKey ? ctx.byKey[coKey(n)] : null);
        var r = rec ? finRecFor(rec, ctx.fin) : null;
        if (r && !isProbable(r) && String(r.accountsCategory || '').trim()) {
          resolved.push({ name: n, rec: r });
        } else {
          unresolved.push({ name: n, rec: r });
        }
      });

      /* THE HALF-THE-FIELD FLOOR. resolved * 2 < total refuses the panel. */
      if (resolved.length * 2 < everyone.length) {
        body += '<div style="margin:0 0 12px;border:1px dashed ' + LINE + ';border-radius:10px;padding:11px 13px;background:#fff;">' +
          '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';">' + esc(grp.name) + '</div>' +
          gap('Refused: of the ' + everyone.length + ' suppliers on this framework, only ' + resolved.length +
            ' resolve to a confirmed Companies House record with an accounts filing. That is below half the field, and a size profile of under half a field misleads more than it informs. Unresolved: ' +
            unresolved.map(function (u) { return esc(u.name); }).join(', ') + '. Confirming identities is what fixes this; lowering the bar is not.') +
          '</div>';
        return;
      }
      rendered += 1;

      var rows = resolved.map(function (r) {
        var me = r.name === sub.name;
        return '<tr>' +
          '<td style="padding:5px 8px;border-bottom:1px solid #f0ece3;font-size:12.5px;color:' + INK + ';' + (me ? 'font-weight:700;' : '') + '">' + esc(r.name) + (me ? ' ◂' : '') + '</td>' +
          '<td style="padding:5px 8px;border-bottom:1px solid #f0ece3;font-size:12.5px;color:#37485a;">' + esc(r.rec.accountsFilingVerbatim || r.rec.accountsCategory) + '</td>' +
          '<td style="padding:5px 8px;border-bottom:1px solid #f0ece3;font-size:12px;color:' + DIM + ';white-space:nowrap;">' + esc(r.rec.incorporated ? ('inc. ' + r.rec.incorporated.slice(0, 4)) : '') + '</td>' +
          '</tr>';
      }).join('');

      body += '<div style="margin:0 0 12px;border:1px solid ' + LINE + ';border-radius:10px;padding:11px 13px;background:#fff;">' +
        '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';">' + esc(grp.name) + '</div>' +
        '<div style="font-size:12px;color:' + DIM + ';margin:3px 0 8px;">' + everyone.length + ' supplier(s) on this framework · ' +
        resolved.length + ' resolved to a confirmed filing · ' + unresolved.length + ' unresolved.</div>' +
        '<div style="overflow-x:auto;"><table style="border-collapse:collapse;width:100%;min-width:420px;">' +
        '<tr><th style="text-align:left;padding:5px 8px;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">SUPPLIER</th>' +
        '<th style="text-align:left;padding:5px 8px;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">MOST RECENT ACCOUNTS FILING</th>' +
        '<th style="text-align:left;padding:5px 8px;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';"></th></tr>' +
        rows + '</table></div>';

      if (unresolved.length) {
        body += '<div style="font-size:12px;color:' + DIM + ';margin-top:7px;">Unresolved, feeding nothing: ' +
          unresolved.map(function (u) {
            var why = u.rec ? (isProbable(u.rec) ? 'identity not confirmed' : 'no accounts filing recorded') : 'no Companies House record fetched';
            return '<b>' + esc(u.name) + '</b> (' + why + ')';
          }).join(' · ') + '.</div>';
      }
      body += '</div>';
    });

    /* What "full accounts" does and does not mean, with the statutory
       thresholds quoted from the file that carries their source. */
    var th = ctx.fin.thresholds;
    if (th && th.bands) {
      var t = [];
      if (th.bands.small && th.bands.small.verbatim) t.push(esc(th.bands.small.verbatim));
      if (th.bands.medium && th.bands.medium.verbatim) t.push('Medium-sized (Companies Act 2006 s465(3)): ' + esc(th.bands.medium.verbatim));
      body += '<div style="font-size:11.5px;color:' + DIM + ';line-height:1.6;margin-top:4px;"><b style="color:#4a5766;">Reading the filings.</b> ' +
        'A company entitled to the small-companies or micro-entity regime may file reduced accounts; a FULL filing is the one made when those exemptions are not used. It does not by itself state the company’s size — the disclosed turnover inside the filed document does, and extracting those figures is the next step. Thresholds in force (' + esc(th.appliesTo || '') + '): ' +
        t.join(' — ') + '</div>';
    }

    if (!rendered) {
      body += gap('No framework on this report cleared the half-the-field floor, so no profile is shown. The refusals above name what is missing.');
    }
    return sec(TITLE, body);
  }

  /* =====================================================================
     PRESENTATION LAYER — redesigned 06/08/2026 to Lou's spec, folding in
     the Employer Intelligence deep dives (WP drafts 2423/2425) so those
     standalone pages can be retired. Section order is hers: company
     information first (with the growth chart near the top), then
     specialities/divisions as cards, then competitors by speciality, then
     news and people, then working-there, and the full catalogue + own-site
     listings LAST. Brand-guide defaults: navy #0B1C33 gradient where a
     company has no recorded brand colour; gold carries labels and rules,
     never body copy.
     ===================================================================== */
  var NAVY_GRAD = 'linear-gradient(135deg,#0B1C33 0%,#132B4A 55%,#1B3A5F 100%)';

  function deepFor(s) { return s.deepDive || null; }
  /* Company colour, in order of how well we can stand behind it:
       1. a colour a human checked against the brand (deepDive.brand);
       2. a colour SAMPLED from the company's own logo, carrying the URL and
          date it was read from (supplier-seed `brand`, written by
          scripts/refresh_brand_colours.py);
       3. the house navy.
     A monochrome logo yields no sample at all and falls through to 3 rather
     than publishing "this company's colour is grey", which a 128px favicon
     cannot support. */
  function brandOf(s) {
    var d = deepFor(s);
    if (d && d.brand && d.brand.c1 && d.brand.c2) return d.brand;
    if (s.brand && s.brand.c1 && s.brand.c2) return s.brand;
    return null;
  }
  function brandGrad(s) {
    var b = brandOf(s);
    return b ? ('linear-gradient(120deg,' + b.c1 + ',' + b.c2 + ')') : NAVY_GRAD;
  }
  function logoImg(s, px) {
    var d = deepFor(s);
    var src = (d && d.domain) ? ('https://logo.clearbit.com/' + d.domain) : (s.image || '');
    var _w = String(s.name || '').replace(/^the\s+/i, '').split(/[\s\-—,\.]+/).filter(Boolean);
    var inits = esc((/^[A-Za-z0-9]{2,4}$/.test(_w[0] || '') ? _w[0] : _w.slice(0, 2).map(function (w) { return w[0]; }).join('')).toUpperCase());
    var fb = '<div style="display:none;width:' + px + 'px;height:' + px + 'px;border-radius:12px;background:#efe9db;align-items:center;justify-content:center;font-weight:700;color:' + G + ';font-size:' + Math.round(px / 3.4) + 'px;">' + inits + '</div>';
    if (!src) {
      return fb.replace('display:none', 'display:flex');
    }
    return '<img src="' + esc(src) + '" alt="" referrerpolicy="no-referrer" loading="lazy" style="max-width:' + (px - 14) + 'px;max-height:' + (px - 14) + 'px;object-fit:contain;" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';">' + fb;
  }

  function heroBand(s) {
    var d = deepFor(s);
    var links = (d && d.links) || [];
    return '<div style="background:' + brandGrad(s) + ';border-radius:11px 11px 0 0;padding:30px 26px;display:flex;align-items:center;gap:18px;flex-wrap:wrap;-webkit-print-color-adjust:exact;print-color-adjust:exact;">' +
      '<span style="width:72px;height:72px;border-radius:14px;background:#fff;display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 3px 10px rgba(0,0,0,.18);">' + logoImg(s, 72) + '</span>' +
      '<div style="min-width:220px;"><div style="color:#fff;font-size:25px;font-weight:700;letter-spacing:.3px;line-height:1.2;">' + esc(s.name) + '</div>' +
      (d && d.tagline ? '<div style="color:rgba(255,255,255,.88);font-size:12.5px;font-weight:600;margin-top:5px;">' + esc(d.tagline) + '</div>' : '') +
      '</div>' +
      (links.length ? '<span style="margin-left:auto;display:flex;gap:8px;flex-wrap:wrap;">' + links.map(function (l) {
        return '<a href="' + esc(l.url) + '" target="_blank" rel="noopener" style="font-size:11px;font-weight:700;letter-spacing:.4px;padding:8px 15px;border-radius:99px;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.35);color:#fff;white-space:nowrap;text-decoration:none;">' + esc(l.label) + '</a>';
      }).join('') + '</span>' : '') +
      '</div>';
  }

  function ledeBox(s) {
    var d = deepFor(s);
    if (!(d && d.lede)) return '';
    var c1 = (brandOf(s) || {}).c1 || '#0B1C33';
    return '<div style="font-size:14.5px;line-height:1.7;background:#fff;border:1px solid ' + LINE + ';border-left:4px solid ' + c1 + ';border-radius:10px;padding:18px 22px;margin:16px 0 0;">' + esc(d.lede) + '</div>';
  }

  function statGrid(s) {
    var d = deepFor(s);
    if (!(d && d.stats && d.stats.length)) return '';
    return '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px;margin:14px 0 0;">' +
      d.stats.map(function (st) {
        return '<div style="background:#fff;border:1px solid ' + LINE + ';border-top:3px solid ' + G + ';border-radius:10px;padding:14px 14px;">' +
          '<div style="font-size:18px;font-weight:800;color:' + INK + ';line-height:1.2;">' + esc(st.v) + '</div>' +
          '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:' + DIM + ';font-weight:700;margin-top:4px;">' + esc(st.l) + '</div>' +
          (st.n ? '<div style="font-size:10.5px;color:' + DIM + ';margin-top:3px;">' + esc(st.n) + '</div>' : '') +
          '</div>';
      }).join('') + '</div>';
  }

  /* The growth chart. Bars are drawn ONLY for figures actually read from a
     named filing; every other year in the frame renders as an empty slot
     labelled as unread. An empty slot is "not yet extracted", never zero —
     drawing a zero-height bar for an unread year would publish a figure
     nobody sourced, which is the whole class of error this repo gates. */
  /* Build a growth series from the FILED ACCOUNTS where one was extracted.
     This is the sourced route: every point came from a tagged (iXBRL) filing,
     and carries the period, the tag and the document it was read from. It is
     preferred over a hand-written deep-dive series because it can be traced. */
  function filedSeries(s, ctx) {
    var rec = ctx.fin ? finRecFor(s, ctx.fin) : null;
    var pts = rec && rec.turnoverSeries;
    if (!(pts && pts.length)) return null;
    var years = pts.map(function (p) { return parseInt(String(p.periodEnd).slice(0, 4), 10); });
    return {
      label: 'Turnover, from the filed accounts',
      currency: '£', unit: 'm',
      axis: { from: Math.min.apply(null, years), to: Math.max.apply(null, years) },
      axisNote: 'Each bar is the turnover tagged in that year\u2019s filed accounts at Companies House. A year with no bar is a year whose accounts carry no tagged turnover, not a year of no trading.',
      points: pts.map(function (p) {
        return { y: 'FY' + String(p.periodEnd).slice(0, 4),
                 v: Math.round(p.value / 1e6 * 10) / 10,
                 src: 'filed ' + (p.filedOn || '') };
      }),
      source: 'the iXBRL (tagged) accounts filed at Companies House' +
              (ctx.fin && ctx.fin.figuresAsOf ? ', read ' + ctx.fin.figuresAsOf : '')
    };
  }

  function growthChart(s, ctx) {
    var d = deepFor(s);
    var g = d && d.growth;
    var filed = filedSeries(s, ctx);
    if (filed) {
      /* A sourced series wins over a curated one; the curated prose is kept
         because it explains what the numbers mean. */
      g = { series: filed, prose: (g && g.prose) || null };
    }
    if (!(g && g.series && g.series.points && g.series.points.length)) {
      var frec = ctx.fin ? finRecFor(s, ctx.fin) : null;
      var why = frec && frec.turnoverNote;
      return sec('Growth', gap(why
        ? ('No turnover series can be shown for this company: ' + esc(why) +
           ' Turnover exists only inside the filed accounts, so where the accounts do not disclose it in a readable form there is nothing to chart. That is a fact about the filing, not about the company\u2019s size.')
        : 'No growth series has been extracted for this company yet. Turnover lives in the filed accounts (Companies House for UK companies, investor filings for listed groups); reading those documents is the extraction step, and it has not run here — a coverage gap, not a company that is not growing.'));
    }
    var se = g.series;
    var byYear = {};
    se.points.forEach(function (p) { byYear[p.y] = p; });
    var years = [];
    for (var y = se.axis.from; y <= se.axis.to; y++) years.push('FY' + y);
    var max = 0;
    se.points.forEach(function (p) { if (p.v > max) max = p.v; });
    /* The column is three stacked things: the value label, the bar, and the year.
       The bar must therefore be sized against the height left AFTER the two
       labels, not against the whole row — sizing it against the row pushed the
       value label off the top of the tallest bar, which is exactly what it was
       doing before 07/08/2026. */
    var H = 150;                 // row height
    var LABELS = 46;             // value label + year label + the gaps between
    var BAR_MAX = H - LABELS;
    var cols = years.map(function (yr) {
      var p = byYear[yr];
      if (p) {
        var h = Math.max(8, Math.round(p.v / max * BAR_MAX));
        return '<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:4px;min-width:44px;">' +
          '<div style="font-size:10.5px;font-weight:800;color:' + INK + ';white-space:nowrap;line-height:1.2;flex:0 0 auto;">' + esc(se.currency) + p.v + esc(se.unit) + '</div>' +
          '<div style="width:70%;height:' + h + 'px;background:linear-gradient(180deg,#D4AF7A,#B8935A);border-radius:4px 4px 0 0;-webkit-print-color-adjust:exact;print-color-adjust:exact;"></div>' +
          '<div style="font-size:9.5px;font-weight:700;color:' + DIM + ';">' + esc(yr) + '</div></div>';
      }
      return '<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:4px;min-width:44px;">' +
        '<div style="width:70%;height:14px;border:1px dashed ' + LINE + ';border-bottom:0;border-radius:4px 4px 0 0;"></div>' +
        '<div style="font-size:9.5px;color:#b8b0a0;">' + esc(yr) + '</div></div>';
    }).join('');

    var body = '<div style="background:#fff;border:1px solid ' + LINE + ';border-radius:10px;padding:16px 16px 12px;">' +
      '<div style="font-size:12px;font-weight:700;color:' + INK + ';margin-bottom:10px;">' + esc(se.label) + ' <span style="color:' + DIM + ';font-weight:600;">(' + esc(se.currency) + esc(se.unit) + ')</span></div>' +
      '<div style="display:flex;align-items:flex-end;gap:6px;height:' + H + 'px;border-bottom:2px solid ' + LINE + ';overflow-x:auto;overflow-y:visible;padding-top:4px;">' + cols + '</div>' +
      '<div style="font-size:10.5px;color:' + DIM + ';margin-top:8px;line-height:1.55;">Solid bars are figures read from ' + esc(se.source) + '. Dashed slots are years not yet extracted — an empty slot is unread, never zero. ' + esc(se.axisNote || '') + (se.pending ? ' ' + esc(se.pending) : '') + '</div>' +
      '</div>';

    if (g.prose && g.prose.length) {
      body += '<div style="font-size:13.5px;line-height:1.7;color:#37485a;margin-top:12px;">' +
        g.prose.map(function (p) { return '<p style="margin:0 0 10px;">' + esc(p) + '</p>'; }).join('') + '</div>';
    }
    return sec('Growth', body);
  }

  function ownershipBlock(s) {
    var d = deepFor(s);
    if (!(d && d.ownership && d.ownership.length)) return '';
    return sec('Structure &amp; ownership', '<div style="background:#fff;border:1px solid ' + LINE + ';border-radius:10px;padding:16px 20px;font-size:13.5px;line-height:1.7;color:#37485a;">' +
      d.ownership.map(function (p) { return '<p style="margin:0 0 10px;">' + esc(p) + '</p>'; }).join('') + '</div>');
  }

  /* Divisions / specialities as cards — Lou's spec: they must visually
     stand out, one card each, not a chip row. Uses the company's own
     division tree where a full crawl exists; otherwise one card per
     recorded speciality. */
  function divisionCards(s, ctx) {
    var deep = deepRangeFor(s, ctx.prodFile);
    var grad = brandGrad(s);
    var cards = '';
    if (deep && deep.divisions && deep.divisions.length) {
      cards = deep.divisions.map(function (dv) {
        return '<div style="background:#fff;border:1px solid ' + LINE + ';border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(29,39,51,.06);">' +
          '<div style="background:' + grad + ';padding:12px 16px;color:#fff;font-size:13.5px;font-weight:700;-webkit-print-color-adjust:exact;print-color-adjust:exact;">' + esc(dv.name) + '</div>' +
          '<div style="padding:12px 16px;font-size:12.5px;color:' + DIM + ';line-height:1.6;">' + dv.products + ' product(s) in the verified range' +
          (dv.specialities && dv.specialities.length ? '<br>Specialities: ' + dv.specialities.map(esc).join(', ') : '') +
          '</div></div>';
      }).join('');
      return sec('Divisions &amp; specialities', '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 10px;">The company’s own division structure, from the full crawl of its site; product counts come from the verified range at the bottom of this report.</div>' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;">' + cards + '</div>');
    }
    if (s.specialities && s.specialities.length) {
      cards = s.specialities.map(function (sp) {
        return '<div style="background:#fff;border:1px solid ' + LINE + ';border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(29,39,51,.06);">' +
          '<div style="background:' + grad + ';padding:12px 16px;color:#fff;font-size:13.5px;font-weight:700;-webkit-print-color-adjust:exact;print-color-adjust:exact;">' + esc(sp) + '</div>' +
          '<div style="padding:10px 16px;font-size:12px;color:' + DIM + ';">Recorded speciality · division-level product counts arrive with the full site crawl.</div>' +
          '</div>';
      }).join('');
      return sec('Divisions &amp; specialities', '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;">' + cards + '</div>');
    }
    return sec('Divisions &amp; specialities', gap('No speciality recorded for this company yet.'));
  }

  function deepPeopleCards(s) {
    var d = deepFor(s);
    if (!(d && d.people && d.people.length)) return '';
    var h = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;">' +
      d.people.map(function (p) {
        return '<div style="background:#fff;border:1px solid ' + LINE + ';border-radius:10px;padding:15px 16px;' + (p.out ? 'opacity:.72;' : '') + '">' +
          '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';">' + esc(p.name) + '</div>' +
          '<div style="font-size:11px;color:' + (p.out ? DIM : G) + ';font-weight:700;margin-top:2px;">' + esc(p.role) + '</div>' +
          (p.note ? '<div style="font-size:12px;color:' + DIM + ';margin-top:6px;line-height:1.55;">' + esc(p.note) + '</div>' : '') +
          '</div>';
      }).join('') + '</div>';
    if (d.peopleNote) {
      h += '<div style="font-size:11.5px;color:' + DIM + ';background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:8px;padding:9px 13px;margin-top:10px;">' + esc(d.peopleNote) + '</div>';
    }
    return h;
  }

  function deepPress(s) {
    var d = deepFor(s);
    if (!(d && d.press && d.press.length)) return '';
    var c1 = (brandOf(s) || {}).c1 || G;
    return d.press.map(function (n) {
      return '<div style="background:#fff;border:1px solid ' + LINE + ';border-radius:10px;padding:13px 17px;margin:0 0 10px;' + (n.flagged ? 'border-left:4px solid ' + c1 + ';' : '') + '">' +
        '<div style="font-size:10px;font-weight:700;letter-spacing:.6px;color:' + c1 + ';text-transform:uppercase;margin-bottom:4px;">' + esc(n.date) + '</div>' +
        '<div style="font-size:13px;line-height:1.6;color:#37485a;">' + esc(n.text) + '</div></div>';
    }).join('');
  }

  function workingThere(s) {
    var d = deepFor(s);
    if (!d) return '';
    var left = '', right = '';
    if (d.place && d.place.embed) {
      left += '<div style="border-radius:10px;overflow:hidden;border:1px solid ' + LINE + ';background:#eee;"><iframe src="' + esc(d.place.embed) + '" loading="lazy" referrerpolicy="no-referrer-when-downgrade" style="display:block;width:100%;height:210px;border:0;" title="Site location"></iframe></div>' +
        (d.place.caption ? '<div style="font-size:11px;color:' + DIM + ';margin-top:6px;line-height:1.5;">' + esc(d.place.caption) + '</div>' : '');
    }
    if (d.linkedinPeople) {
      left += '<div style="margin-top:12px;"><a href="' + esc(d.linkedinPeople) + '" target="_blank" rel="noopener" style="display:inline-block;background:#39689e;color:#fff;font-size:12px;font-weight:700;padding:9px 18px;border-radius:99px;text-decoration:none;">See who works there ↗</a></div>';
    }
    if (d.glassdoor) {
      right += '<div style="background:' + SOFT + ';border:1px solid ' + LINE + ';border-left:4px solid ' + G + ';border-radius:8px;padding:13px 15px;">' +
        '<div style="display:flex;align-items:center;gap:9px;margin-bottom:7px;"><span style="font-size:21px;font-weight:800;color:' + G + ';">' + esc(d.glassdoor.rating) + '</span><span style="font-size:11.5px;color:' + DIM + ';font-weight:600;">' + esc(d.glassdoor.scale) + '</span></div>' +
        '<div style="font-size:13px;line-height:1.6;color:' + INK + ';font-style:italic;">' + esc(d.glassdoor.summary) + '</div>' +
        '<div style="margin-top:7px;font-size:10.5px;color:' + DIM + ';">Editorial summary of public reviews, checked ' + esc(d.glassdoor.checked) + '. <a href="' + esc(d.glassdoor.url) + '" target="_blank" rel="noopener" style="color:#39689e;font-weight:600;">Read them yourself ↗</a></div></div>';
    }
    if (d.interview) {
      right += '<div style="margin-top:12px;background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:10px;padding:12px 15px;">' +
        '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1.4px;font-weight:700;color:' + DIM + ';margin-bottom:5px;">Before you walk in</div>' +
        '<div style="font-size:13px;line-height:1.65;color:#37485a;">' + esc(d.interview) + '</div></div>';
    }
    if (d.hiring && d.hiring.length) {
      right += '<div style="margin-top:12px;font-size:13px;line-height:1.65;color:#37485a;">' +
        d.hiring.map(function (p) { return '<p style="margin:0 0 8px;">' + esc(p) + '</p>'; }).join('') + '</div>';
    }
    if (!left && !right) return '';
    return sec('Working there', '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;">' +
      '<div>' + (left || '') + '</div><div>' + (right || '') + '</div></div>');
  }

  /* ---------------------------------------------------------------------
     Report card
     --------------------------------------------------------------------- */
  /* One composer for both surfaces. The on-page card and the printed pack
     render THIS, so they cannot drift — and a panel refused here is refused
     everywhere. Section order is Lou's (06/08/2026): company information
     (with growth near the top), specialities/divisions as cards, competitors
     by speciality, news and people, working-there, and the full listings
     LAST. */
  function composeSections(sub, ctx) {
    var d = deepFor(sub);
    var h = '';

    h += ledeBox(sub);

    /* -- 1 · Company information ---------------------------------------- */
    var info = statGrid(sub);
    if (sub.note) {
      info += '<div style="font-size:13.5px;color:#37485a;line-height:1.6;margin:14px 0 0;">' + esc(sub.note) + '</div>';
    }
    if (sub.voice && (sub.voice.line || sub.voice.angle)) {
      info += '<div style="font-size:13px;color:#37485a;line-height:1.6;margin:10px 0 0;"><b style="color:' + INK + ';">How they sell' + (sub.voice.angle ? ' — ' + esc(sub.voice.angle) : '') + '.</b> ' + esc(sub.voice.line || '') + '</div>';
    }
    h += sec('Company information', info || gap('Nothing curated for this company yet beyond the panels below.'));
    h += panelCompanyFacts(sub, ctx);
    h += ownershipBlock(sub);

    /* -- 2 · Growth, near the top by design ----------------------------- */
    h += growthChart(sub, ctx);

    /* -- 3 · Specialities / divisions as cards -------------------------- */
    h += divisionCards(sub, ctx);
    h += frameworks(sub, ctx);

    /* -- 4 · Competitors ------------------------------------------------ */
    h += '<div style="margin:20px 0 0;padding-top:14px;border-top:2px solid ' + LINE + ';">' +
      '<div style="font-size:11px;letter-spacing:2px;font-weight:700;color:' + G + ';">DERIVED — READ THE RULE BEFORE YOU QUOTE IT</div>' +
      '<div style="font-size:12.5px;color:' + DIM + ';margin-top:4px;line-height:1.55;">The panels below are computed by this page, not read from a source. Each prints the rule it was computed under and refuses to render on thin evidence. None of them ranks anyone, and none of them prints a market-share figure — the filing profile shows which statutory regime each confirmed supplier files under, which is the sourceable part of "how big are they".</div>' +
      '</div>';
    var co = coListing(sub, ctx);
    h += panelCoListed(sub, ctx, co);
    h += panelSameSpeciality(sub, ctx, co);
    h += panelFieldProfile(sub, ctx, co);
    if (d && d.marketPosition && d.marketPosition.length) {
      h += sec('Market position', '<div style="font-size:13.5px;line-height:1.7;color:#37485a;">' +
        d.marketPosition.map(function (p) { return '<p style="margin:0 0 8px;">' + esc(p) + '</p>'; }).join('') + '</div>');
    }

    /* -- 5 · News, alerts, people --------------------------------------- */
    var newsHtml = deepPress(sub);
    var pr = press(sub);
    h += newsHtml ? sec('In the press', newsHtml) + pr : pr;
    h += alerts(sub);
    var pplDeep = deepPeopleCards(sub);
    if (pplDeep) h += sec('Key people', pplDeep);
    h += panelPeople(sub, ctx);

    /* -- 6 · Working there (deep-dive extras) --------------------------- */
    h += workingThere(sub);

    /* -- 7 · The listings, deliberately last ---------------------------- */
    h += productListing(sub, ctx);

    return h;
  }

  function report(sub, ctx) {
    var h = '<div style="border:1px solid ' + LINE + ';border-radius:11px;background:#fdfcf9;overflow:hidden;">';
    h += heroBand(sub);
    h += '<div style="padding:6px 18px 16px;">';

    /* Stage 5 entry point. The pack is the same composer rendered for
       print — it adds no claims, so the button lives on the card. */
    h += '<div style="display:flex;justify-content:flex-end;margin:10px 0 0;">' +
      '<button id="mcrPack" style="cursor:pointer;background:linear-gradient(180deg,#D4AF7A,#B8935A);color:#0B1C33;border:0;border-radius:99px;padding:8px 16px;font-size:12.5px;font-weight:700;letter-spacing:.04em;">Download / print this report</button></div>';

    h += composeSections(sub, ctx);

    h += '<div style="margin-top:16px;padding-top:10px;border-top:1px solid ' + LINE + ';font-size:11px;color:' + DIM + ';line-height:1.7;">' +
      'Related Hub pages: ' +
      '<a href="/medical-sales-hub/frameworks/" style="color:' + G + ';">Frameworks</a> · ' +
      '<a href="/medical-sales-hub/awards/" style="color:' + G + ';">Award Tracker</a> · ' +
      '<a href="/medical-sales-hub/" style="color:' + G + ';">Live Desk (alerts)</a> · ' +
      '<a href="/medical-sales-hub/news/" style="color:' + G + ';">News</a></div>';
    h += '</div></div>';
    return h;
  }

  /* =====================================================================
     STAGE 5 — the interview pack. One printable document per supplier,
     sectioned by speciality. It composes the panels above VERBATIM — the
     same functions build the same HTML, so a refused panel arrives refused,
     with its reason, and nothing can appear in print that the page would
     not show. The speciality sections re-present the verified range where a
     full crawl exists; framework and field panels are company-level, and
     the pack says so rather than pretending a per-speciality split it
     cannot source (per-speciality framework attribution needs the award
     feed tagged by product — not built, stated in OUTSTANDING).
     ===================================================================== */
  function packSpecialitySections(sub, ctx) {
    var deep = deepRangeFor(sub, ctx.prodFile);
    if (!(deep && deep.divisions && deep.divisions.length)) {
      return '<div style="font-size:12px;color:' + DIM + ';line-height:1.6;">Per-speciality sections need the full site crawl for this company, which has not run yet — the range above is the curated and catalogue-verified view. The crawl is the same mechanism that built the GBUK tree and runs supplier by supplier.</div>';
    }
    var prods = deep.products || [];
    return deep.divisions.map(function (d) {
      var mine = prods.filter(function (p) { return p.division === d.name; });
      var byCat = {};
      mine.forEach(function (p) {
        var c = p.category || 'Uncategorised';
        (byCat[c] = byCat[c] || []).push(p.n);
      });
      var cats = Object.keys(byCat).sort();
      return '<div style="margin:0 0 14px;page-break-inside:avoid;">' +
        '<div style="font-size:14px;font-weight:700;color:' + INK + ';border-bottom:2px solid ' + G + ';padding-bottom:3px;margin-bottom:6px;">' + esc(d.name) +
        ' <span style="font-weight:400;color:' + DIM + ';font-size:12px;">· ' + mine.length + ' product(s)' +
        (d.specialities && d.specialities.length ? ' · ' + d.specialities.map(esc).join(', ') : '') + '</span></div>' +
        cats.map(function (c) {
          return '<div style="font-size:12.5px;line-height:1.65;margin:0 0 4px;"><b style="color:#4a5766;">' + esc(c) + ':</b> ' +
            byCat[c].map(esc).join(' · ') + '</div>';
        }).join('') +
        '</div>';
    }).join('');
  }

  function buildPack(sub, ctx) {
    var today = new Date();
    var stamp = ('0' + today.getDate()).slice(-2) + '/' + ('0' + (today.getMonth() + 1)).slice(-2) + '/' + today.getFullYear();
    var d = deepFor(sub);
    var inner =
      heroBand(sub) +
      '<div style="font-size:11px;color:' + DIM + ';margin:10px 0 2px;">MEDICAL SALES INTELLIGENCE HUB · COMPANY INTELLIGENCE REPORT · Prepared ' + stamp +
        ' · framework data as of ' + esc(ctx.asOf || 'not recorded') +
        (ctx.fin && ctx.fin.dataAsOf ? ' · Companies House read ' + esc(ctx.fin.dataAsOf) : '') +
        ' · every derived panel carries the rule it was computed under</div>' +
      composeSections(sub, ctx) +
      sec('The range by speciality', packSpecialitySections(sub, ctx)) +
      '<div style="margin-top:18px;padding-top:10px;border-top:1px solid ' + LINE + ';font-size:10.5px;color:' + DIM + ';line-height:1.7;">' +
        'Prepared by the Medical Sales Intelligence Hub (medsalesintelligencehub.co.uk) for the member who generated it. ' +
        'Sources are linked panel by panel; derived panels print their derivation. ' +
        (d && d.sources ? 'Deep-dive sources: ' + esc(d.sources) + ' ' : '') +
        'Company logos are served via Clearbit’s logo service and remain the property of their respective owners, shown for identification only. ' +
        '© Elevate and Thrive Ltd ' + today.getFullYear() + '. Not for redistribution.</div>';

    return '<!doctype html><html><head><meta charset="utf-8"><title>' + esc(sub.name) + ' — Company Intelligence Report</title>' +
      '<style>body{font-family:Inter,-apple-system,Segoe UI,sans-serif;color:' + INK + ';margin:24px auto;max-width:880px;padding:0 18px;background:#f7f4ee;}' +
      'a{color:' + G + ';}@media print{body{margin:0;max-width:none;background:#fff;}button{display:none;}}' +
      '*{-webkit-print-color-adjust:exact;print-color-adjust:exact;}</style></head><body>' +
      '<div style="text-align:right;margin:0 0 10px;"><button onclick="window.print()" style="cursor:pointer;background:linear-gradient(180deg,#D4AF7A,#B8935A);color:#0B1C33;border:0;border-radius:99px;padding:8px 16px;font-size:12.5px;font-weight:700;">Print / save as PDF</button></div>' +
      inner + '</body></html>';
  }

  function openPack(sub, ctx) {
    var w = window.open('', '_blank');
    if (!w) return; /* popup blocked — the on-page card is the same content */
    w.document.open();
    w.document.write(buildPack(sub, ctx));
    w.document.close();
  }

  function shell() {
    MOUNT.innerHTML = '' +
      '<div style="font-family:Inter,-apple-system,Segoe UI,sans-serif;margin:0;">' +
        '<div style="padding:2px 0 6px;">' +
          '<div style="font-size:11.5px;letter-spacing:2px;font-weight:700;color:' + G + ';">COMPANY REPORT</div>' +
          '<p style="margin:5px 0 12px;font-size:13.5px;color:' + DIM + ';line-height:1.6;">Type a company — get who they are, what they sell, the frameworks they hold, live alerts, corroborated press, and who else sits on those frameworks. <span id="mcrCount"></span></p>' +
          '<input id="mcrInput" list="mcrList" autocomplete="off" placeholder="e.g. GBUK Group, BD, Vygon, Coloplast…" ' +
            'style="width:100%;max-width:520px;padding:11px 16px;border-radius:99px;border:1px solid ' + LINE + ';font:inherit;font-size:15px;color:' + INK + ';background:#ffffff;-webkit-text-fill-color:' + INK + ';caret-color:' + INK + ';outline:none;">' +
          '<datalist id="mcrList"></datalist>' +
          '<div id="mcrChips" style="margin:10px 0 2px;display:flex;flex-wrap:wrap;gap:6px;"></div>' +
        '</div>' +
        '<div id="mcrResult" style="padding:2px 0 18px;"></div>' +
      '</div>';
  }

  function boot(index, seed, specMap, prodFile, fin, cache, fwDoc) {
    var all = mergeSuppliers(index, seed);
    var byName = {};
    all.forEach(function (s) { byName[s.name] = s; });

    /* framework key -> deduped list of supplier names holding it. Built once
       from the merged set so both the count and the rows come from the same
       place. */
    var fwMap = {};
    all.forEach(function (s) {
      fwList(s).forEach(function (f) {
        if (!fwMap[f.key]) fwMap[f.key] = [];
        if (fwMap[f.key].indexOf(s.name) === -1) fwMap[f.key].push(s.name);
      });
    });

    var ctx = {
      all: all,
      byName: byName,
      fwMap: fwMap,
      asOf: (index && index.dataAsOf) || '',
      spec: specCtx(specMap, prodFile),
      prodFile: prodFile,
      fin: fin || null,
      cache: cache || null,
      fwDoc: fwDoc || null,
      fwByKey: fwIndex(fwDoc),
      /* The briefs print legal names ("B. Braun Medical Limited"); this Hub
         holds trading names ("B. Braun Medical"). Matching those by exact
         string made every confirmed company on a framework look unresolved,
         so the filing profile refused even where the filings were held. */
      byKey: (function () {
        var m = {};
        all.forEach(function (s) {
          [s.name].concat(s.aliases || []).forEach(function (n) {
            var k = coKey(n);
            if (k && !m[k]) { m[k] = s; }
          });
        });
        return m;
      })()
    };

    shell();
    var input = document.getElementById('mcrInput'),
        list = document.getElementById('mcrList'),
        result = document.getElementById('mcrResult'),
        chips = document.getElementById('mcrChips'),
        count = document.getElementById('mcrCount');

    count.textContent = all.length + ' companies indexed · data as of ' + (ctx.asOf || 'date not recorded');
    list.innerHTML = all.map(function (s) { return '<option value="' + esc(s.name) + '">'; }).join('');

    var quick = ['GBUK Group', 'BD — Becton, Dickinson', 'Vygon (UK)', 'Coloplast', 'Convatec'];
    chips.innerHTML = quick.filter(function (q) { return !!byName[q]; }).map(function (q) {
      return '<button data-q="' + esc(q) + '" style="cursor:pointer;background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:99px;padding:5px 12px;font-size:12px;color:' + INK + ';">' + esc(q.split(' — ')[0]) + '</button>';
    }).join('');

    function find(q) {
      var n = norm(q);
      if (!n) return null;
      var hit = all.filter(function (s) {
        return norm(s.name) === n || (s.aliases || []).some(function (a) { return norm(a) === n; });
      })[0];
      if (hit) return hit;
      return all.filter(function (s) {
        if (norm(s.name).indexOf(n) > -1) return true;
        if ((s.aliases || []).some(function (a) { return norm(a).indexOf(n) > -1; })) return true;
        if ((s.products || []).some(function (p) { return norm(typeof p === 'string' ? p : (p && p.n)).indexOf(n) > -1; })) return true;
        return false;
      })[0] || null;
    }
    function show(q) {
      var s = find(q);
      result.innerHTML = s ? report(s, ctx) :
        '<div style="padding:14px 4px;font-size:13.5px;color:' + DIM + ';line-height:1.6;">No match for “' + esc(q) +
        '”. Coverage is the tracked-supplier set (' + all.length + ' indexed) — a company that is not here is <b>not yet indexed</b>, not “nothing found”.</div>';
      var pk = document.getElementById('mcrPack');
      if (pk && s) pk.addEventListener('click', function () { openPack(s, ctx); });
    }
    input.addEventListener('change', function () { show(input.value); });
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') show(input.value); });
    chips.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('button') : null;
      if (b) { input.value = b.getAttribute('data-q'); show(input.value); }
    });

    if (window.MSH_COMPANY_REPORT_OPEN) show(window.MSH_COMPANY_REPORT_OPEN);

    /* Harness hook, same family as MSH_COMPANY_REPORT_OPEN: lets a test page
       pull the Stage 5 pack HTML for a named company without opening a popup
       window. Carries no data of its own — it is the same buildPack the
       button calls. */
    window.MSH_COMPANY_REPORT_BUILD = function (q) {
      var s = find(q);
      return s ? buildPack(s, ctx) : null;
    };
  }

  /* Test / preload hook, same pattern as supplier-search.js's
     window.MSH_SUPPLIER_INDEX — lets a harness run this file against local
     copies of the data without touching the network. */
  if (window.MSH_COMPANY_REPORT_DATA) {
    var P = window.MSH_COMPANY_REPORT_DATA;
    boot(P.index, P.seed, P.specMap, P.products, P.financials, P.nhssc, P.frameworks);
    return;
  }

  MOUNT.innerHTML = '<div style="font-family:Inter,-apple-system,Segoe UI,sans-serif;color:' + DIM + ';font-size:13px;padding:12px;">Loading company report…</div>';
  Promise.all([
    fetch(IDX, { cache: 'no-store' }).then(function (r) { return r.json(); }),
    fetch(SEED, { cache: 'no-store' }).then(function (r) { return r.json(); }).catch(function () { return { suppliers: [] }; }),
    fetch(SPECMAP, { cache: 'no-store' }).then(function (r) { return r.json(); }).catch(function () { return null; }),
    fetch(PRODUCTS, { cache: 'no-store' }).then(function (r) { return r.json(); }).catch(function () { return null; }),
    fetch(FIN, { cache: 'no-store' }).then(function (r) { return r.json(); }).catch(function () { return null; }),
    fetch(NHSSC, { cache: 'no-store' }).then(function (r) { return r.json(); }).catch(function () { return null; }),
    fetch(FWDATA, { cache: 'no-store' }).then(function (r) { return r.json(); }).catch(function () { return null; })
  ]).then(function (res) { boot(res[0], res[1], res[2], res[3], res[4], res[5], res[6]); })
    .catch(function () {
      MOUNT.innerHTML = '<div style="font-family:Inter,-apple-system,Segoe UI,sans-serif;color:' + DIM + ';font-size:13px;padding:12px;">The company report is loading its data — if this persists, the index feed is temporarily unreachable. Nothing is missing from the report; the report has not loaded.</div>';
    });
})();
