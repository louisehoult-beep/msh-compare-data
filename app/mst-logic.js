
(function(){
  var D=window.MST_DATA,SPECS=D.SPECS,P=D.P,FW=D.FW,PRIORITY=D.PRIORITY,EVID=D.EVID;
  var $=function(id){return document.getElementById(id);};
  var ICON={
    coins:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><ellipse cx="9" cy="7" rx="6" ry="3"/><path d="M3 7v5c0 1.7 2.7 3 6 3"/><ellipse cx="15" cy="14" rx="6" ry="3"/><path d="M9 14v3c0 1.7 2.7 3 6 3s6-1.3 6-3v-6"/></svg>',
    clipboard:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3h6v1"/><path d="M9 13l2 2 4-4"/></svg>',
    users:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 3-5 6-5s6 2 6 5"/><path d="M16 6a3 3 0 0 1 0 6"/><path d="M18 20c0-2-1-3.5-2.5-4.3"/></svg>',
    heart:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 20s-7-4.5-7-9a4 4 0 0 1 7-2.5A4 4 0 0 1 19 11c0 4.5-7 9-7 9z"/></svg>',
    shield:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3l7 3v5c0 5-3.5 8-7 10-3.5-2-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/></svg>',
    flask:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M9 3h6"/><path d="M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/><path d="M7.5 15h9"/></svg>',
    pill:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="8" width="18" height="8" rx="4" transform="rotate(-45 12 12)"/><path d="M8.5 8.5l7 7"/></svg>',
    alert:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 4l9 16H3z"/><path d="M12 10v4"/><path d="M12 17h.01"/></svg>',
    cart:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 5h2l2 11h10l2-7H7"/><circle cx="9" cy="20" r="1.3"/><circle cx="18" cy="20" r="1.3"/></svg>',
    bandage:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="2" y="8" width="20" height="8" rx="4" transform="rotate(-45 12 12)"/><path d="M10 10l4 4"/></svg>',
    wrench:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M15 7a4 4 0 0 1-5 5l-5 5 2 2 5-5a4 4 0 0 0 5-5l-2 2-2-2 2-2z"/></svg>',
    droplet:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z"/></svg>',
    leaf:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M5 19c0-8 6-13 14-13 0 8-5 14-13 14"/><path d="M5 19c3-4 7-6 10-7"/></svg>',
    scan:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"/><circle cx="12" cy="12" r="3"/></svg>'
  };
  var L={
    payer:{icon:'coins',role:'Payer',whoSec:'Divisional / finance manager (budget-holder)',whoPri:'ICB finance and commissioning (community / prescribing budget)',cares:'Cash-releasing savings, capacity, length of stay, CQC position',evidence:'A banked, attributable business case plus local baseline audit',hook:'Reduce the problem with a saving you can point to and bank',risk:"Won't release budget without an attributable, cash-releasing saving",spin:function(p,s){return['What is your annual volume and current cost linked to '+p.problem+'?','When it happens, who absorbs the downstream cost (repeat activity, longer stays, extra prescribing)?','Across a year, what does that do to your budget, capacity and CQC position?','If we cut it with a saving you could attribute, how would that help your '+(s==='primary'?'ICB budget':'division')+'?'];}},
    decision_maker:{icon:'clipboard',role:'Decision-maker',whoSec:'Clinical lead plus procurement / product evaluation group',whoPri:'ICB formulary and service lead; PCN clinical directors',cares:'Evidence quality, framework / formulary compliance, total cost of ownership',evidence:'Peer-reviewed data, framework/formulary availability, NICE/GIRFT alignment',hook:'Evidence-backed, compliant-route, low-risk swap that moves a measured KPI',risk:'Will require a local pilot and a compliant route before sign-off',spin:function(p,s){return['What do you use now for '+p.area+', and what is the route to market?','How strong is the evidence, and is there a compliant '+(s==='primary'?'formulary':'framework')+' route?','If you adopt without robust evidence, what is the risk to sign-off and clinical buy-in?','If I bring evidence, a compliant route and a local pilot, does this become straightforward?'];}},
    user:{icon:'users',role:'User',whoSec:'Front-line clinical team',whoPri:'GPs, practice and community / district nurses',cares:'Ease of use, time, safety, fewer failures, patient experience',evidence:'Acceptability / ease-of-use data and a simple training plan',hook:'Easier, safer, right-first-time without extra steps',risk:'Will abandon anything that adds steps, training burden or fails in use',spin:function(p,s){return['How do you manage '+p.area+' day to day right now?','Where does the current approach create hassle, delay or risk for you?','What does that cost in time, rework or patient experience?','If this made the job easier and safer, how would that change things on the floor?'];}},
    ipc:{icon:'shield',role:'Infection Prevention and Control',whoSec:'IPC lead nurse / team',whoPri:'Community IPC / ICB IPC lead',cares:'Infection rates, diagnostic and antimicrobial stewardship, CQC IPC assurance',evidence:'Infection-outcome and inappropriate-prescribing data',hook:'Fewer infections / false positives, a stewardship and assurance win',risk:'Influential blocker or champion; ignore them and adoption stalls',spin:function(p,s){return['How does '+p.problem+' show up in your infection / AMR data?','How often does it drive avoidable infection or inappropriate antibiotics?','What does that mean for your IPC assurance and CQC position?','If we reduced it, how would that support your stewardship and IPC goals?'];}},
    microbiology:{icon:'flask',role:'Microbiology / pathology',whoSec:'Microbiology / pathology service lead',whoPri:'Community pathology link',cares:'Avoidable repeat tests, lab capacity, turnaround, cost per test',evidence:'Local repeat-rate audit plus lab cost modelling',hook:'Fewer avoidable repeats equals released lab capacity and faster turnaround',risk:'Holds the data that proves or sinks your case; engage early',spin:function(p,s){return['What proportion of your workload is avoidable repeat or contamination linked to '+p.area+'?','What does each avoidable test cost the lab in time and capacity?','Across the year, how much capacity goes on that?','If it halved, what would you do with the released capacity?'];}},
    stewardship:{icon:'pill',role:'Antimicrobial stewardship',whoSec:'Antimicrobial stewardship lead (micro consultant / pharmacist)',whoPri:'ICB / PCN prescribing and AMR lead',cares:'Inappropriate prescribing, AMR, over-treatment',evidence:'Link between the problem and unnecessary prescribing; stewardship outcomes',hook:'Fewer false positives directly supports your AMR targets',risk:'A credibility multiplier; their endorsement de-risks the case',spin:function(p,s){return['How much prescribing traces back to '+p.problem+'?','Where does it drive over-treatment or resistance risk?','What is the AMR and safety cost across the year?','If we cut it, how would that move your stewardship numbers?'];}},
    sharps:{icon:'alert',role:'Sharps safety / H&S',whoSec:'Sharps safety / health and safety committee',whoPri:'Community H&S / sharps lead',cares:'Needlestick injuries, staff safety, sharps regulations compliance',evidence:'Incident-rate data and safety-engineered device evidence',hook:'Fewer needlestick incidents, safer staff and regulatory compliance',risk:'Safety mandate can accelerate adoption, or block a non-compliant device',spin:function(p,s){return['What is your current rate of sharps / needlestick incidents in '+p.area+'?','Where are staff most exposed with the current devices?','What do those incidents cost in time, testing and staff wellbeing?','If a safer device cut incidents, how would that support your safety obligations?'];}},
    procurement:{icon:'cart',role:'Procurement',whoSec:'Procurement category manager',whoPri:'ICB procurement / supply lead',cares:'Price, framework compliance, total cost, maverick-spend control',evidence:'Framework position, price benchmarking, total cost of ownership',hook:'A compliant, better-value route that fits your category plan',risk:'Off-framework or poor-value routes get rejected regardless of clinical merit',spin:function(p,s){return['What framework and pricing are you on for '+p.area+' today?','Where are the off-contract or maverick-spend risks?','What does fragmented buying cost you in price and compliance?','If I offered a compliant, better-value route, would that help your category plan?'];}},
    tissue_viability:{icon:'bandage',role:'Tissue viability',whoSec:'Tissue viability nurse (TVN) / service',whoPri:'Community TVN service',cares:'Healing rates, avoidable pressure / wound harm, nurse-visit burden',evidence:'Healing-time and avoidable-harm data',hook:'Faster healing equals fewer visits, shorter stays, less avoidable harm',risk:'Owns the harm metrics; a key clinical gatekeeper for wound/skin products',spin:function(p,s){return['What is your current rate of the skin / wound problem behind '+p.problem+'?','Where does the current approach delay healing or add harm?','What does that cost in nurse visits, length of stay and harm reporting?','If healing improved, how would that help your service and harm metrics?'];}},
    ebme:{icon:'wrench',role:'EBME / clinical engineering',whoSec:'EBME / medical physics / clinical engineering',whoPri:'Community equipment service',cares:'Maintenance, training, uptime, servicing (incl. LOLER), capital fit',evidence:'Servicing/maintenance profile, training need, uptime data',hook:'Lower servicing burden and reliable uptime for your team',risk:'Can veto on maintenance, safety or interoperability grounds',spin:function(p,s){return['How does the current equipment fit your maintenance, training and servicing load?','Where does downtime or servicing create risk or cost?','What does that mean for safety, uptime and your team workload?','If a device reduced servicing burden, how would that help your department?'];}},
    decontamination:{icon:'droplet',role:'Decontamination / SSD',whoSec:'Decontamination / sterile services lead',whoPri:'Community decontamination link',cares:'Reprocessing load, compliance (JAG / HTM), capacity, traceability',evidence:'Reprocessing volumes, compliance position, capacity modelling',hook:'Less reprocessing equals more throughput and easier compliance',risk:'Compliance failures here stop a whole service; engage early',spin:function(p,s){return['What is your current reprocessing load and compliance position (JAG / HTM) for '+p.area+'?','Where do bottlenecks or failures create risk or delay?','What does that cost in capacity, repeat work and compliance risk?','If we reduced reprocessing, how would that help throughput and compliance?'];}},
    sustainability:{icon:'leaf',role:'Sustainability / Green Plan',whoSec:'Sustainability / Green Plan lead',whoPri:'ICB Green Plan lead',cares:'Carbon footprint, waste, net-zero targets, single-use vs reusable',evidence:'Carbon / waste data and net-zero alignment',hook:'A lower-carbon option that performs and supports your Green Plan',risk:'Sustainability is now a scored procurement criterion; ignore at your cost',spin:function(p,s){return['How does '+p.area+' feature in your Green Plan / net-zero targets?','Where does the current product drive waste or carbon?','What is the cost and reputational exposure of that?','If a lower-carbon option performed as well, how would that support your Green Plan?'];}},
    medicines:{icon:'pill',role:'Medicines optimisation',whoSec:'Medicines optimisation / formulary pharmacist',whoPri:'ICB medicines optimisation / formulary pharmacist',cares:'Formulary choice, prescribing spend, variation, adherence',evidence:'Cost-effectiveness, formulary criteria, prescribing data',hook:'A better-value, formulary-ready option that cuts downstream cost',risk:'Formulary gatekeeping; no formulary place, no volume',spin:function(p,s){return['What is your current formulary choice and prescribing spend for '+p.area+'?','Where does it create variation, waste or poor adherence?','What does that cost across the ICB in spend and outcomes?','If a better-value option fit the formulary, would that help your medicines plan?'];}},
    dietitian:{icon:'leaf',role:'Dietetics / nutrition',whoSec:'Dietetics / nutrition support team',whoPri:'Community dietetics / ICB nutrition lead',cares:'Malnutrition risk, feed safety, ONS prescribing spend, MUST scores',evidence:'Nutritional-outcome and prescribing data',hook:'Better nutrition outcomes with controlled feed / ONS spend',risk:'Owns the nutrition pathway; a key clinical gatekeeper',spin:function(p,s){return['How do you assess and manage nutrition in '+p.area+' now?','Where does the current approach create malnutrition risk or feed-related harm?','What does that cost in admissions, length of stay and ONS spend?','If outcomes improved with controlled spend, how would that help your service?'];}},
    radiation_protection:{icon:'scan',role:'Radiation protection',whoSec:'Radiation protection adviser / medical physics expert',whoPri:'Radiation protection adviser',cares:'Patient and staff dose, IR(ME)R compliance, QA, safety',evidence:'Dose audit and compliance data',hook:'Lower dose and easier IR(ME)R compliance',risk:'Can block on radiation-safety or compliance grounds',spin:function(p,s){return['How does '+p.area+' sit within your dose and IR(ME)R compliance position?','Where do dose or QA issues create risk?','What is the safety and compliance exposure across the year?','If a solution lowered dose and eased compliance, how would that help?'];}},
    pharmacy:{icon:'pill',role:'Pharmacy / aseptic',whoSec:'Chief pharmacist / aseptic services lead',whoPri:'ICB chief pharmacist',cares:'Medicines safety, aseptic capacity, drug budget, governance',evidence:'Safety, capacity and cost data',hook:'A safer, more efficient medicines / aseptic pathway',risk:'Governs medicines and aseptic prep; gatekeeper for SACT / PN',spin:function(p,s){return['How does '+p.area+' fit your aseptic capacity and medicines governance?','Where do preparation, safety or capacity bottlenecks arise?','What does that cost in risk, delay and drug budget?','If a solution improved safety and capacity, how would that help pharmacy?'];}},
    patient:{icon:'heart',role:'Patient',whoSec:'The patient / carer',whoPri:'The patient / carer at home',cares:'Dignity, safety, right-first-time care, fewer repeat visits, avoided harm',evidence:'Patient-experience / acceptability feedback',hook:'A dignified, accurate, less burdensome experience',risk:'Experience and harm drive complaints, PALS and CQC scrutiny'}
  };
  var TPL={dev:['payer','decision_maker','user','ebme'],con:['payer','decision_maker','user'],ipc:['payer','decision_maker','user','ipc'],micro:['payer','decision_maker','user','ipc','microbiology'],tv:['payer','decision_maker','user','tissue_viability'],proc:['payer','decision_maker','user','procurement'],rx:['payer','medicines','user'],cap:['payer','decision_maker','user','ebme','procurement']};
  /* 36 ICBs, effective 01/04/2026. The ICB (Establishment and Abolition) Order 2026 established 6,
     abolished 12 and widened 1, cutting 42 to 36; changes affected London, East of England and the
     South East only. Cross-checked against the Order, the NHSE April 2026 map and live ODS.
     Source of truth: Cowork-OS .../Medical Sales Hub/Website/mapper-data/icb-list-2026-04.js
     NOTE: a naive ODS query returns 48 - all 12 abolished ICBs still show Status:Active for ~6
     months after their 31/03/2026 legal end. Filter on legal end date, never on status. */
  var GEOS=[{r:'East of England',n:['Central East','Essex','Norfolk and Suffolk']},{r:'London',n:['North East London','South East London','South West London','West and North London']},{r:'Midlands',n:['Birmingham and Solihull','Black Country','Coventry and Warwickshire','Derby and Derbyshire','Herefordshire and Worcestershire','Leicester, Leicestershire and Rutland','Lincolnshire','Northamptonshire','Nottingham and Nottinghamshire','Shropshire, Telford and Wrekin','Staffordshire and Stoke-on-Trent']},{r:'North East and Yorkshire',n:['Humber and North Yorkshire','North East and North Cumbria','South Yorkshire','West Yorkshire']},{r:'North West',n:['Cheshire and Merseyside','Greater Manchester','Lancashire and South Cumbria']},{r:'South East',n:['Hampshire and Isle of Wight','Kent and Medway','Surrey and Sussex','Thames Valley']},{r:'South West',n:['Bath and North East Somerset, Swindon and Wiltshire','Bristol, North Somerset and South Gloucestershire','Cornwall and the Isles of Scilly','Devon','Dorset','Gloucestershire','Somerset']}];
  /* Three legal entities, one buying centre - Board in Common since 20/11/2025, one shared exec team. */
  var BUYING_CENTRE={'NHS Derby and Derbyshire ICB':'DLN','NHS Lincolnshire ICB':'DLN','NHS Nottingham and Nottinghamshire ICB':'DLN'};
  var BUYING_CENTRE_NOTE='Meets as a Board in Common with Derby and Derbyshire, Lincolnshire and Nottingham and Nottinghamshire ICBs — three legal entities, one shared executive team. Work them as one account, not three.';

  function fwFor(p){return FW[p.s]||{fam:'NHS Supply Chain framework',cat:'https://www.supplychain.nhs.uk/'};}
  function renderIntel(p,s){var fw=fwFor(p);var ev=EVID[p.t]||EVID.con;var pri=PRIORITY[p.s]||'NHS productivity & GIRFT';var h='';h+='<div class="mst__chip"><h4>Route to market &middot; framework</h4><p>'+fw.fam+'.</p><p class="mst__chiplink"><a href="'+fw.cat+'" target="_blank" rel="noopener">NHS Supply Chain category</a> &middot; <a href="/medical-sales-hub/frameworks/">Frameworks hub (live)</a> &middot; new tech: <a href="https://innovation.nhs.uk/" target="_blank" rel="noopener">NHS Innovation Service</a> &rarr; Supply Chain URN &rarr; Innovation DPS</p></div>';h+='<div class="mst__chip"><h4>Evidence to lead with</h4><p>'+ev+'.</p><p class="mst__chiplink"><a href="https://www.nice.org.uk/guidance" target="_blank" rel="noopener">NICE guidance</a> &middot; <a href="https://gettingitrightfirsttime.co.uk/" target="_blank" rel="noopener">GIRFT</a></p></div>';h+='<div class="mst__chip"><h4>National priority hook</h4><p>'+pri+'.</p></div>';$('m-intel').innerHTML=h;}
  function renderPath(p,s){var cap=(p.t==='cap'||p.t==='dev'||p.t==='proc');var rx=(p.t==='rx'||p.s==='ostomy'||p.s==='nutrition');var steps=[];steps.push(['1','Find the clinical champion',(s==='primary'?'GP, community / practice nurse or PCN lead who owns the problem':'Front-line clinician / consultant who specifies and wants it')]);steps.push(['2','Local evaluation / trial','Small pilot with the evidence pack; bring IPC, the product evaluation group and (for kit) EBME in early']);if(cap){steps.push(['3','Business case & capital sign-off',(s==='primary'?'ICB capital / transformation funding':'Trust Medical Devices Management Group + capital committee')]);}else{steps.push(['3','Product evaluation sign-off',(s==='primary'?'ICB formulary / commissioning approval':'Trust Medical Devices Management Group / Product Evaluation Group')]);}steps.push(['4','Procurement & compliant route','Procurement confirms framework / DPS position'+(rx?' or Drug Tariff / formulary place':'')+' and total cost of ownership']);steps.push(['5','Award & onboard',(rx?'Supplied via Drug Tariff / community order or framework call-off':'Order via the framework call-off')+'; deliver training and go-live']);steps.push(['6','Review & spread','Measure the agreed outcome, feed back, and roll out to neighbouring teams / trusts']);var h='<div class="mst__pathhead">Typical buying-cycle pathway &mdash; who signs off</div><div class="mst__steps2">';steps.forEach(function(st){h+='<div class="mst__step2"><b>'+st[0]+'</b><div><strong>'+st[1]+'</strong><span>'+st[2]+'</span></div></div>';});h+='</div>';$('m-path').innerHTML=h;}
  var lastCalc=null;
  function copyText(t,el){var done=function(){if(el){el.hidden=false;setTimeout(function(){el.hidden=true;},2000);}};if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(done);}else{var ta=document.createElement('textarea');ta.value=t;document.body.appendChild(ta);ta.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(ta);done();}}
  function renderCalcExtras(o){var save=o.save,pc=o.pc,net=o.net,vol=o.vol;var ex=$('c-extra');if(!ex)return;if(!(save>0)){ex.innerHTML='';return;}var cash=save*o.cashShare,cap=save*(1-o.cashShare);var dpct=Math.round(o.dir*100);var perInstance=vol>0?save/vol:0;var h='';h+='<div class="mst__xpanel"><div class="mst__xh">Cash vs capacity — what kind of saving is this?</div>';h+='<div class="mst__xrow"><span>Released cash<em>Budget directly freed — can be reallocated or saved</em></span><b>'+gbp(cash)+'/yr</b></div>';h+='<div class="mst__xrow"><span>Released capacity<em>Time / resource freed — enables more activity, does not reduce spend</em></span><b>'+gbp(cap)+'/yr</b></div></div>';h+='<div class="mst__xpanel"><div class="mst__xh">Value by stakeholder — three pitch foundations</div><div class="mst__cols3">';h+='<div class="mst__col"><h5>Payer · ICB / commissioner</h5><p>Annual cost across the commissioned population; strategic and directive alignment.</p><b>'+gbp(save)+'/yr</b></div>';h+='<div class="mst__col"><h5>Decision-maker · unit / practice manager</h5><p>Cost impact within their specific budget envelope; service-delivery effect.</p><b>'+gbp(net>0?net:save)+'/yr net</b></div>';h+='<div class="mst__col"><h5>User · clinician</h5><p>Per-procedure / per-shift impact; workload and supply-continuity risk.</p><b>'+(perInstance?gbp(perInstance)+' per case':'—')+'</b></div>';h+='</div></div>';if(pc>0){var pb=o.pb;h+='<div class="mst__xpanel"><div class="mst__xh">Break-even &amp; saving curve</div>';h+='<div class="mst__xrow"><span>Months to break-even<em>When cumulative saving overtakes cumulative product cost</em></span><b>'+(pb!==null?(pb<1?'<1':pb.toFixed(1))+' months':'n/a')+'</b></div>';h+='<div class="mst__curve"><div class="mst__yr">Year 1<b>'+gbp(net)+'</b>net</div><div class="mst__yr">Year 2<b>'+gbp(net*2)+'</b>cumulative</div><div class="mst__yr">Year 3<b>'+gbp(net*3)+'</b>cumulative</div></div></div>';}var p=currentProduct();h+='<div class="mst__xpanel"><div class="mst__xh">Cost of inaction</div><div class="mst__inact">Every year <b>'+p.n+'</b> is not adopted, this problem costs the organisation an estimated <b>'+gbp(save)+'</b>.<div class="mst__curve"><div class="mst__yr">Year 1<b>'+gbp(save)+'</b></div><div class="mst__yr">Year 2<b>'+gbp(save*2)+'</b></div><div class="mst__yr">Year 3<b>'+gbp(save*3)+'</b></div></div></div></div>';var bands=[['Highly direct, single-use device in a controlled single-clinician setting','60–80%',60,100],['Device requiring clinical interpretation or pathway integration','40–59%',40,59],['Behaviour-change or training-based intervention','10–25%',0,39]];var bench=bands.map(function(b){var on=dpct>=b[2]&&dpct<=b[3];return '<div class="mst__band'+(on?' mst__band--on':'')+'"><span>'+b[1]+'</span>'+b[0]+'</div>';}).join('');h+='<div class="mst__xpanel"><div class="mst__xh">Directness factor — defend your '+dpct+'%</div>'+bench+'<p class="mst__disc" style="margin-top:4px;">Pick the band you can justify in a procurement conversation; when unsure, choose the lower one.</p></div>';h+='<div class="mst__xpanel"><div class="mst__xh">Conversation brief — rep preparation &amp; coaching use</div><p class="mst__disc" style="margin:0 0 10px;">Builds the need statement, each stakeholder’s risk / benefit, the value figure and a recommended pitch angle into one copyable brief.</p><button class="mst__btn mst__btn--primary" id="c-briefbtn" type="button">Copy conversation brief</button> <span class="mst__copied" id="c-briefdone" hidden>Copied</span></div>';ex.innerHTML=h;var bb=$('c-briefbtn');if(bb)bb.addEventListener('click',function(){copyText(buildBrief(lastCalc),$('c-briefdone'));});}
  function buildBrief(o){if(!o)return '';var p=currentProduct();var s=state.setting;var keys=stakeKeys(p,s);var save=o.save,pc=o.pc,net=o.net,vol=o.vol;var perInstance=vol>0?save/vol:0;var L1=[];L1.push('CONVERSATION BRIEF — rep preparation and coaching use');L1.push('');L1.push('NEED STATEMENT');L1.push(p.p.charAt(0).toUpperCase()+p.p.slice(1)+'. Product: '+p.n+'. Speciality: '+p.area+'. Setting: '+(s==='primary'?'Primary care / community / ICB':'Acute trust / hospital')+'. '+$('m-geo').value+'.');L1.push('');L1.push('VALUE (from the calculator)');L1.push('Gross annual cost of the problem: '+gbp(o.gross)+'. Conservative annual saving: '+gbp(save)+' (efficacy '+Math.round(o.eff*100)+'%, directness '+Math.round(o.dir*100)+'%).');L1.push('Released cash '+gbp(save*o.cashShare)+'/yr; released capacity '+gbp(save*(1-o.cashShare))+'/yr.');if(pc>0)L1.push('Product cost '+gbp(pc)+'/yr; net benefit '+gbp(net)+'/yr'+(o.pb!==null?'; payback '+(o.pb<1?'under a month':o.pb.toFixed(1)+' months'):'')+'.');L1.push('Cost of inaction: ~'+gbp(save)+'/yr forgone ('+gbp(save*3)+' over three years).');L1.push('');L1.push('VALUE BY STAKEHOLDER');L1.push('• Payer (ICB / commissioner): '+gbp(save)+'/yr across the commissioned population — lead on strategic / directive alignment.');L1.push('• Decision-maker (unit / practice manager): '+gbp(net>0?net:save)+'/yr within their budget — lead on service-delivery effect.');L1.push('• User (clinician): '+(perInstance?gbp(perInstance)+' per case':'per-shift impact')+' — lead on workload and supply continuity.');L1.push('');L1.push('STAKEHOLDERS — risk, benefit and pitch angle');keys.forEach(function(k){var lib=L[k];if(!lib)return;var who=s==='primary'?(lib.whoPri||lib.whoSec):lib.whoSec;L1.push('• '+lib.role+' ('+who+'):');if(lib.cares)L1.push('   Cares about: '+lib.cares+'.');if(lib.risk)L1.push('   Risk / uncertainty: '+lib.risk+'.');if(lib.hook)L1.push('   Pitch angle: '+lib.hook+'.');});L1.push('');L1.push('Framing: problem-first, evidence-based, stakeholder-aware (NHS value-based procurement; Stanford Biodesign). Figures are estimates — validate against trust-level data before quoting.');return L1.join('\n');}
  var state={spec:'',prodIdx:0,setting:'secondary'};
  function settingsOf(p){return p.set==='sp'?['secondary','primary']:(p.set==='s'?['secondary']:['primary']);}
  function stakeKeys(p,s){var base=(s==='primary'&&p.tp)?TPL[p.tp]:TPL[p.t];var extra=(s==='primary'&&p.xp)?p.xp:(p.x||[]);var all=base.concat(extra);var seen={},out=[];all.forEach(function(k){if(k!=='patient'&&!seen[k]){seen[k]=1;out.push(k);}});out.push('patient');return out;}
  /* Sub-specialities (e.g. bloodcoll under vascular): picking the PARENT rolls up
     its children's products too, so a rep working Vascular access sees blood
     collection products as well. Picking the child alone still shows only its
     own products. Generic over any SPECS.parent, not hardcoded to one pair -
     this was previously wired into meeting-prep.js's speciality-map.json logic
     but never into the Stakeholder Mapper itself, which is why blood collection
     did not appear under Vascular access here despite the products existing. */
  function productsFor(spec){
    var kids=SPECS.filter(function(s){return s.parent===spec;}).map(function(s){return s.id;});
    var wanted=[spec].concat(kids);
    return P.filter(function(p){return wanted.indexOf(p.s)!==-1;});
  }
  function currentProduct(){var l=productsFor(state.spec);return l[state.prodIdx]||l[0]||{n:'your product',p:'the problem you solve',s:state.spec||'',t:'dev',area:''};}
  function fillGeo(){var h='';GEOS.forEach(function(g){h+='<optgroup label="'+g.r+'">';g.n.forEach(function(nm){h+='<option>NHS '+nm+' ICB</option>';});h+='</optgroup>';});$('m-geo').innerHTML=h;fixNote();}
  /* The on-page note lives in WP page 1109's content, not here, and still read
     "42 ICBs ... consolidating into roughly 26 clusters across 2026-27" - both
     wrong since 01/04/2026. The note sits inside a 26,000-character block, so
     editing it in wp-admin means rewriting all of it by hand. Correcting it from
     here keeps the number in the same version-controlled place as the list it
     describes, so the two can never drift apart again.
     If the block is ever rewritten cleanly in wp-admin, this becomes a no-op. */
  function fixNote(){
    var n=document.querySelector('.mst__note');
    if(!n)return;
    var h=n.innerHTML;
    /* Anchor on the surrounding stable text rather than matching the sentence's
       punctuation - WordPress renders the en-dash inconsistently as a character
       or an entity, and an exact regex would silently fail to match. */
    var start=h.indexOf('42 ICBs are shown');
    var end=h.indexOf('Roles and levers');
    if(start===-1||end===-1||end<start)return;
    n.innerHTML=h.slice(0,start)
      +'36 ICBs are shown, grouped by NHS region — the first merger round took effect on 1 April 2026 '
      +'(42 → 36), affecting London, the East of England and the South East only. A second round is '
      +'proposed for 1 April 2027, but the number and boundaries are not yet decided: clusters were asked '
      +'to submit merged footprints by 14 July 2026, with approvals expected in autumn 2026 and the '
      +'outcome tied to Local Government Reorganisation. '
      +h.slice(end);
  }
  function fillSpec(){$('m-spec').innerHTML='<option value="">Select\u2026</option>'+SPECS.map(function(s){return '<option value="'+s.id+'">'+s.label+'</option>';}).join('');$('m-spec').value=state.spec;}
  function fillProd(){if(!state.spec){$('m-prod').innerHTML='<option value="">\u2014</option>';return;}var list=productsFor(state.spec);$('m-prod').innerHTML=list.map(function(p,i){return '<option value="'+i+'">'+p.n+'</option>';}).join('');if(state.prodIdx>=list.length)state.prodIdx=0;$('m-prod').value=state.prodIdx;}
  function ensureSetting(){var p=currentProduct();var ss=settingsOf(p);if(ss.indexOf(state.setting)<0)state.setting=ss[0];var only=ss.length===1;$('m-sec').style.display=ss.indexOf('secondary')>=0?'':'none';$('m-pri').style.display=ss.indexOf('primary')>=0?'':'none';$('m-sec').classList.toggle('mst__segbtn--on',state.setting==='secondary');$('m-pri').classList.toggle('mst__segbtn--on',state.setting==='primary');$('m-setwrap').style.opacity=only?'.7':'1';}
  function render(){if(!state.spec){$('m-problem').innerHTML='<b>Select your speciality above</b> to build the stakeholder map.';$('m-geoline').innerHTML='';$('m-intel').innerHTML='';$('m-path').innerHTML='';$('m-cards').innerHTML='';if($('m-contacts'))$('m-contacts').innerHTML='';if($('m-sheet'))$('m-sheet').innerHTML='';return;}var p=currentProduct();p.area=(SPECS.filter(function(x){return x.id===state.spec;})[0]||{}).label||state.spec;ensureSetting();var s=state.setting;var settingLabel=s==='secondary'?'Acute trust / hospital':'Primary care, community and ICB';$('m-problem').innerHTML='<b>Problem to anchor on:</b> '+p.p+'  · <b>Setting:</b> '+settingLabel;$('m-geoline').innerHTML='<b style="color:var(--ink)">'+$('m-geo').value+'</b> — identify the named '+(s==='primary'?'ICB / community':'trust')+' Payer, Decision-maker and IPC leads locally; org structures are real, individuals confirmed per target.';renderIntel(p,s);renderPath(p,s);var keys=stakeKeys(p,s);var html='';keys.forEach(function(k){var lib=L[k];if(!lib)return;var who=s==='primary'?(lib.whoPri||lib.whoSec):lib.whoSec;var spin='';if(lib.spin){var lab=['Situation','Problem','Implication','Need-payoff'];var pa={problem:p.p,area:p.area};var qs=lib.spin(pa,s);spin='<div class="mst__spin"><div class="mst__spinh">SPIN questions</div>'+qs.map(function(q,i){return '<div><span>'+lab[i]+':</span> '+q+'</div>';}).join('')+'</div>';}html+='<div class="mst__c"><div class="mst__chead"><div class="mst__ico">'+(ICON[lib.icon]||'')+'</div><div><div class="mst__role">'+lib.role+'</div><div class="mst__who">'+who+'</div></div></div>'+(lib.cares?'<div class="mst__f"><b>Cares about:</b> '+lib.cares+'</div>':'')+(lib.evidence?'<div class="mst__f"><b>Evidence they demand:</b> '+lib.evidence+'</div>':'')+(lib.hook?'<div class="mst__f"><b>Your hook:</b> '+lib.hook+'</div>':'')+spin+(lib.risk?'<div class="mst__risk"><b style="color:var(--ink)">Risk / uncertainty:</b> '+lib.risk+'</div>':'')+nameBlock(k,lib)+'</div>';});html+='<div class="mst__c" style="grid-column:1/-1;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px"><div class="mst__f" style="margin:0"><b style="color:var(--ink)">Build the financial case for this product</b><br>Sends the problem above into the Value Case Calculator.</div><button class="mst__btn mst__btn--primary" id="m-tocalc" type="button">Open value calculator</button></div>';$('m-cards').innerHTML=html;$('m-tocalc').addEventListener('click',function(){$('c-prob').value=p.p.charAt(0).toUpperCase()+p.p.slice(1);showTab('calc');calc();$('c-cost').focus();});renderTrustLine(s);ensureMounts();renderContacts();renderToolbar(p,s);}
  var gbp=function(n){if(!isFinite(n))return '£0';return new Intl.NumberFormat('en-GB',{style:'currency',currency:'GBP',maximumFractionDigits:(Math.abs(n)>=1000?0:2)}).format(n);};
  var num=function(id){var v=parseFloat($(id).value);return isNaN(v)?0:v;};
  function mrow(l,v,hero){return '<div class="mst__metric"><span class="mst__ml">'+l+'</span><span class="mst__mv'+(hero?' mst__mv--hero':'')+'">'+v+'</span></div>';}
  function calc(){var prob=$('c-prob').value.trim()||'this problem';var cost=num('c-cost'),vol=num('c-vol'),eff=Math.min(num('c-eff'),100)/100,dir=Math.min(num('c-dir'),100)/100,price=num('c-price'),units=num('c-units');var gross=cost*vol,save=gross*eff*dir,pc=price*units,net=save-pc;var roi=pc>0?net/pc*100:null,pb=(save>0?(pc>0):false)?pc/save*12:null;var h=mrow('Gross annual cost of the problem',gbp(gross));h+=mrow('Conservative annual saving',gbp(save),true);if(pc>0){h+=mrow('Annual product cost',gbp(pc));h+=mrow('Net annual benefit',gbp(net));if(roi!==null)h+=mrow('Return on investment',Math.round(roi)+'%');if(pb!==null)h+=mrow('Payback period',(pb<1?'<1':pb.toFixed(1))+' months');}$('c-results').innerHTML=h;var vd=$('c-verdict');if(pc<=0){vd.textContent='Add a unit price and units to test ROI.';vd.style.color='var(--muted)';}else if(net>0){vd.textContent='Stacks up — a net saving for the trust.';vd.style.color='var(--good)';}else{vd.textContent='Non-starter — costs the trust more than it saves.';vd.style.color='var(--bad)';}var st=prob.charAt(0).toUpperCase()+prob.slice(1)+' costs an estimated '+gbp(gross)+'/yr ('+gbp(cost)+' x '+vol.toLocaleString('en-GB')+'). At '+Math.round(eff*100)+'% efficacy and a conservative '+Math.round(dir*100)+'% directness factor, the solution releases '+gbp(save)+'/yr'+(pc>0?(' against '+gbp(pc)+' product cost — net '+gbp(net)+(roi!==null?', '+Math.round(roi)+'% ROI':'')+(pb!==null?', payback '+(pb<1?'under a month':pb.toFixed(1)+' months'):'')+'.'):'.')+' Figures are estimates based on stated assumptions; validate against trust-level data.';$('c-stmt').textContent=st;$('c-copied').hidden=true;var cashShare=Math.min(num('c-cash')||60,100)/100;var o={gross:gross,save:save,pc:pc,net:net,eff:eff,dir:dir,cost:cost,vol:vol,roi:roi,pb:pb,cashShare:cashShare};lastCalc=o;renderCalcExtras(o);}
  function copy(){var t=$('c-stmt').textContent;var done=function(){$('c-copied').hidden=false;setTimeout(function(){$('c-copied').hidden=true;},2000);};if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(done);}else{var ta=document.createElement('textarea');ta.value=t;document.body.appendChild(ta);ta.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(ta);done();}}
  function showTab(which){var map=which==='map';$('sec-map').hidden=!map;$('sec-calc').hidden=map;$('tab-map').classList.toggle('mst__tab--on',map);$('tab-calc').classList.toggle('mst__tab--on',!map);}

  /* ==========================================================================
     TRUST-LEVEL DRILL-DOWN, NAME ROUTES, ACCOUNT SHEET
     Added 24/07/2026. Everything below is injected from here — no wp-admin,
     no page-content edit. Data is fetched from this same repo.

     Four things this adds to the ICB-level map:
       1. A trust picker under the ICB picker (202 legally-live trusts, ODS).
       2. Per role: where a real name can lawfully be found, and a LinkedIn
          people-search link the member clicks themselves.
       3. Named contacts already held for that trust, from Find a Tender.
       4. A printable / downloadable account map sheet with blank fields.

     ⚠️ LINKEDIN — read before "improving" this.
     The links below open a normal LinkedIn search in the member's own browser,
     on their click. That is a person using LinkedIn. It is NOT what the who's-who
     page rules out: automated collection returns HTTP 999, breaches LinkedIn's
     terms, and — the practical reason — automated profile views appear in the
     target's "who viewed your profile" feed attributed to the member. Never
     fetch, scrape or pre-load anything from linkedin.com here.
     ========================================================================== */
  var RAW = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/';
  var TRUSTS = [], TRUST_ASOF = '', CONTACTS = null, MOVES = null, TRUST_LOAD_ERR = '';

  /* Where a real name for each role can lawfully be obtained.
     Every verdict here is lifted from the 20/07/2026 real-names research
     (data/whos-who.html in this repo) — not re-judged, not estimated.
     tier: named | partial | earn | unchecked                                  */
  var ROUTE = {
    payer: {tier:'partial', li:'director of finance',
      how:'The board Chief Finance Officer is named in the ODS SIRO register (~280–293 rows at trusts and ICBs, 31% carry an email). The divisional or service finance manager who actually holds the budget you are pitching to is in no register.',
      links:[['ODS registers (Caldicott / SIRO / IAO)','https://digital.nhs.uk/services/organisation-data-service/export-data-files/csv-downloads/miscellaneous']]},
    decision_maker: {tier:'earn', li:'clinical lead',
      how:'Product evaluation committee membership is not published anywhere, and the two best clinical registers (RCP Fellows, RCoA Regional Advisers) are both permission-blocked. You can still get the committee’s cycle and submission criteria without a name — often the more valuable half.',
      links:[]},
    user: {tier:'earn', li:'clinical nurse specialist',
      how:'Never published as a named list. This one is met, not looked up.', links:[]},
    ipc: {tier:'earn', li:'infection prevention and control',
      how:'Filtered across 20,000+ named individuals in the ODS registers, IPC returned exactly 1. No register lists trust IPC leads.',
      links:[]},
    microbiology: {tier:'earn', li:'consultant microbiologist',
      how:'Would be reachable via the RCP Register of Fellows — which is permission-blocked, its terms prohibit copying.',
      links:[]},
    stewardship: {tier:'earn', li:'antimicrobial pharmacist',
      how:'No register lists antimicrobial stewardship post-holders by trust.', links:[]},
    sharps: {tier:'earn', li:'health and safety manager',
      how:'A committee role. Membership is not published.', links:[]},
    procurement: {tier:'partial', li:'procurement category manager',
      how:'Two different people, two different answers. The NHS Supply Chain <b>national</b> category lead is published for supplier contact — the strongest lawful basis of any source, because your purpose matches the publication purpose, and NHS Supply Chain states the engagement window itself: 9 to 15 months before the current arrangement expires. The <b>trust</b> category manager who buys your line is the single most valuable name in this map and the least obtainable: ODS returns 0, board papers 0 across ~170 author lines, and the ICO backed a trust withholding exactly this in IC-340495-F0W1. Where a trust is currently tendering, Find a Tender names a contact — see below.',
      links:[['NHS Supply Chain — categories','https://www.supplychain.nhs.uk/categories/'],
             ['NHS Supply Chain — contact','https://www.supplychain.nhs.uk/contact-us/'],
             ['HCSA (Health Care Supply Association)','https://www.nhsprocurement.org.uk/']]},
    tissue_viability: {tier:'earn', li:'tissue viability nurse',
      how:'No register. Occasionally named on a trust service page.', links:[]},
    ebme: {tier:'partial', li:'clinical engineering',
      how:'The Register of Clinical Technologists lists 688 named Medical Engineering registrants (1,055 across all scopes), free and public — but <b>name and town only</b>, no employer and no job title. It establishes who exists, not who works where. Roughly 10–15% of acute trusts publish named clinical engineering staff on department pages, skewed to large teaching centres.',
      links:[['Register of Clinical Technologists','https://www.therct.org.uk/']]},
    decontamination: {tier:'earn', li:'sterile services manager',
      how:'A committee and service role. Membership is not published.', links:[]},
    sustainability: {tier:'unchecked', li:'sustainability lead',
      how:'Trust Green Plans are published and <i>may</i> name a lead. This was not checked in the 20/07/2026 research — flagged as open rather than claimed either way.',
      links:[]},
    medicines: {tier:'partial', li:'formulary pharmacist',
      how:'Some pharmacists appear in the ODS registers. Area Prescribing Committee membership <i>categories</i> are published; the named individuals in the seats generally are not. Do not use ABPI Disclosure UK — its identity data is licensed from IQVIA OneKey, whose terms expressly prohibit compiling an internal database or commercial extraction, which is precisely what a CRM import is.',
      links:[['ODS registers','https://digital.nhs.uk/services/organisation-data-service/export-data-files/csv-downloads/miscellaneous']]},
    dietitian: {tier:'earn', li:'dietitian', how:'No register.', links:[]},
    radiation_protection: {tier:'unchecked', li:'radiation protection adviser',
      how:'Radiation Protection Advisers are a statutory appointment, so a route may well exist. Not checked in the 20/07/2026 research — flagged rather than claimed.',
      links:[]},
    pharmacy: {tier:'partial', li:'chief pharmacist',
      how:'Some Chief Pharmacists appear in the ODS registers. Same ABPI / IQVIA restriction as medicines optimisation — do not import from Disclosure UK.',
      links:[['ODS registers','https://digital.nhs.uk/services/organisation-data-service/export-data-files/csv-downloads/miscellaneous']]},
    patient: {tier:'na', li:'',
      how:'Never a prospecting target. Patient and carer experience reaches you through PALS, complaints and CQC — not through a name you look up.',
      links:[]}
  };
  var TIER = {named:['Named now','#2E6B3E'], partial:['Findable — partly','#9A7A2E'],
              earn:['Earn it','#6B2A34'], unchecked:['Not yet checked','#8C8880'],
              na:['Not a target','#8C8880']};

  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function stripTags(s){return String(s==null?'':s).replace(/<[^>]*>/g,'');}
  function liURL(trust,terms){
    return 'https://www.linkedin.com/search/results/people/?keywords='
      + encodeURIComponent('"'+trust+'" '+terms);}
  function ftsURL(trust){
    return 'https://www.find-tender.service.gov.uk/Search/Results?keywords='
      + encodeURIComponent(trust);}

  /* Injected styles — kept here so the whole feature is one git-served file. */
  function injectCSS(){
    if(document.getElementById('mst-trust-css'))return;
    var st=document.createElement('style');st.id='mst-trust-css';
    st.textContent=
     '.mst__tline{font-size:13px;line-height:1.55;margin:6px 0 2px}'
    +'.mst__tline b{color:var(--ink)}'
    +'.mst__tpill{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.5px;'
    +'text-transform:uppercase;padding:2px 8px;border-radius:99px;color:#fff;margin-right:6px;vertical-align:1px}'
    +'.mst__name{border-top:1px dashed rgba(0,0,0,.14);margin-top:10px;padding-top:9px;font-size:12.5px;line-height:1.55}'
    +'.mst__name a{color:inherit}'
    +'.mst__namehow{color:var(--muted);margin:4px 0 6px}'
    +'.mst__lnk{display:inline-block;font-size:11.5px;font-weight:600;border:1px solid rgba(0,0,0,.18);'
    +'border-radius:7px;padding:3px 9px;margin:3px 5px 0 0;text-decoration:none}'
    +'.mst__lnk:hover{background:rgba(0,0,0,.04)}'
    +'.mst__toolbar{display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin:14px 0 0}'
    +'.mst__ctbl{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}'
    +'.mst__ctbl th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.7px;'
    +'color:var(--muted);border-bottom:2px solid rgba(0,0,0,.12);padding:6px 8px}'
    +'.mst__ctbl td{border-bottom:1px solid rgba(0,0,0,.08);padding:7px 8px;vertical-align:top}'
    +'.mst__empty{font-size:12.5px;color:var(--muted);line-height:1.6}'
    +'@media(max-width:640px){.mst__ctbl{font-size:11.5px}}';
    document.head.appendChild(st);
  }

  /* ---- data ------------------------------------------------------------- */
  function getJSON(file){
    return fetch(RAW+file+'?cb='+Date.now()).then(function(r){
      if(!r.ok)throw new Error(r.status);return r.json();});
  }
  function loadTrustData(){
    getJSON('trust-map.json').then(function(d){
      TRUSTS=d.trusts||[];TRUST_ASOF=d.asOf||'';fillTrust();render();
    }).catch(function(e){
      TRUST_LOAD_ERR='The trust list could not be loaded ('+e.message+'). '
        +'The ICB-level map below still works.';
      fillTrust();render();
    });
    /* Contacts and observed moves are optional — a failure here must never
       take the map down, so they render as "nothing on file" instead. */
    getJSON('trust-contacts.json').then(function(d){CONTACTS=d;})
      .catch(function(){CONTACTS={trusts:{},unavailable:true};}).then(render);
    getJSON('people-moves.json').then(function(d){MOVES=d;})
      .catch(function(){MOVES={moves:[],unavailable:true};}).then(render);
  }

  /* ---- trust picker ----------------------------------------------------- */
  function icbNameFromGeo(){
    /* #m-geo options read "NHS Lincolnshire ICB"; trust-map holds "Lincolnshire". */
    return ($('m-geo').value||'').replace(/^NHS\s+/,'').replace(/\s+ICB$/,'').trim();
  }
  function trustsInICB(){
    var want=icbNameFromGeo();
    return TRUSTS.filter(function(t){return t.icbName===want;});
  }
  function selectedTrust(){
    var el=$('m-trust');
    if(!el||!el.value)return null;
    for(var i=0;i<TRUSTS.length;i++){if(TRUSTS[i].code===el.value)return TRUSTS[i];}
    return null;
  }
  function ensureTrustSelect(){
    if($('m-trust'))return;
    var geo=$('m-geo'); if(!geo)return;
    var lab=document.createElement('label');
    lab.className=geo.parentNode.className||'mst__lab';
    lab.innerHTML='Trust (optional — drills the map down to one account)'
      +'<select class="mst__sel" id="m-trust"></select>';
    geo.parentNode.parentNode.insertBefore(lab,geo.parentNode.nextSibling);
    $('m-trust').addEventListener('change',render);
  }
  function fillTrust(){
    ensureTrustSelect();
    var el=$('m-trust'); if(!el)return;
    var keep=el.value, list=trustsInICB();
    /* kind===null means ODS gave no sector and the name did not prove one — the
       group is honestly "and other", not silently "acute". See kind() in
       scripts/refresh_trusts.py for why "Healthcare"/"Partnership" can't be rules. */
    var groups={}, order=['Acute and other trusts','Mental health','Community','Ambulance service'];
    list.forEach(function(t){var k=t.kind||'Acute and other trusts';(groups[k]=groups[k]||[]).push(t);});
    var h='<option value="">— Whole ICB (no single trust) —</option>';
    order.forEach(function(k){
      if(!groups[k])return;
      h+='<optgroup label="'+esc(k)+'">';
      groups[k].forEach(function(t){
        h+='<option value="'+esc(t.code)+'">'+esc(t.n)+(t.town?' — '+esc(t.town):'')+'</option>';});
      h+='</optgroup>';
    });
    if(!list.length){
      h='<option value="">'+(TRUST_LOAD_ERR?'Trust list unavailable':'No trusts listed for this ICB')+'</option>';
    }
    el.innerHTML=h;
    if(keep){el.value=keep;}
  }

  /* ---- trust context line ----------------------------------------------- */
  function renderTrustLine(s){
    var t=selectedTrust(), el=$('m-geoline'); if(!el)return;
    if(TRUST_LOAD_ERR){
      el.innerHTML+='<div class="mst__tline" style="color:var(--muted)">'+esc(TRUST_LOAD_ERR)+'</div>';
      return;
    }
    if(!t){
      var n=trustsInICB().length;
      if(n)el.innerHTML+='<div class="mst__tline" style="color:var(--muted)">'+n
        +' NHS trust'+(n===1?'':'s')+' sit'+(n===1?'s':'')+' in this ICB — pick one above to drill the map '
        +'down to a single account, with name routes, LinkedIn searches and a printable account sheet.</div>';
      return;
    }
    var h='<div class="mst__tline"><b>'+esc(t.n)+'</b> · ODS '+esc(t.code)
      +(t.town?' · '+esc(t.town):'')+(t.postcode?' '+esc(t.postcode):'')
      +(t.kind?' · '+esc(t.kind):'')+' · commissioned by <b>NHS '+esc(t.icbName)+' ICB</b>'
      +(t.region?' ('+esc(t.region)+')':'')+'</div>';
    if(t.bc==='DLN'){
      h+='<div class="mst__tline" style="color:var(--muted)"><b>Buying centre:</b> '+BUYING_CENTRE_NOTE+'</div>';
    }
    if(s==='primary'){
      h+='<div class="mst__tline" style="color:var(--muted)">You have the map set to '
        +'<b>primary care / community / ICB</b>. The trust above still frames the geography, but the roles '
        +'shown are the ICB-side ones — switch to acute if you are selling into the hospital.</div>';
    }
    el.innerHTML+=h;
  }

  /* ---- per-role name route + LinkedIn ----------------------------------- */
  function nameBlock(key,lib){
    var t=selectedTrust(); if(!t)return '';
    var r=ROUTE[key]; if(!r)return '';
    var tier=TIER[r.tier]||TIER.earn;
    var h='<div class="mst__name"><span class="mst__tpill" style="background:'+tier[1]+'">'
      +esc(tier[0])+'</span><b>Getting a real name</b>'
      +'<div class="mst__namehow">'+r.how+'</div>';
    if(r.li){
      h+='<a class="mst__lnk" target="_blank" rel="noopener nofollow" href="'
        +esc(liURL(t.n,r.li))+'">Search LinkedIn ↗</a>';
    }
    (r.links||[]).forEach(function(l){
      h+='<a class="mst__lnk" target="_blank" rel="noopener" href="'+esc(l[1])+'">'+esc(l[0])+' ↗</a>';});
    if(key==='procurement'){
      h+='<a class="mst__lnk" target="_blank" rel="noopener" href="'+esc(ftsURL(t.n))
        +'">This trust on Find a Tender ↗</a>';
    }
    return h+'</div>';
  }

  /* ---- named contacts already held (Find a Tender) ---------------------- */
  function contactsFor(t){
    if(!t||!CONTACTS)return null;
    return (CONTACTS.trusts||{})[t.code]||[];
  }
  function movesFor(t){
    if(!t||!MOVES)return null;
    return (MOVES.moves||[]).filter(function(m){return m.trust===t.code;});
  }
  function renderContacts(){
    var host=$('m-contacts'); if(!host)return;
    var t=selectedTrust();
    if(!t){host.innerHTML='';return;}
    var list=contactsFor(t), moves=movesFor(t);
    var h='<div class="mst__c" style="grid-column:1/-1">'
      +'<div class="mst__role" style="margin-bottom:2px">Names already on file for '+esc(t.n)+'</div>';

    if(list===null){
      h+='<div class="mst__empty">Loading the contact index…</div>';
    }else if(!list.length){
      h+='<div class="mst__empty">'+(CONTACTS.unavailable
        ?'The contact index could not be loaded just now — this is a loading problem, not an empty trust. '
        :'Nothing on file for this trust yet. ')+'The index is built from named '
        +'contacts on this trust’s own Find a Tender notices, and only covers the period harvested so '
        +'far — a trust that has not published a notice in that window will be empty, which is coverage, '
        +'not an answer. Use the source links on each role card above, and '
        +'<a href="'+esc(ftsURL(t.n))+'" target="_blank" rel="noopener">check Find a Tender directly</a>.</div>';
    }else{
      h+='<div class="mst__empty" style="margin-bottom:4px">From this trust’s own public procurement '
        +'notices (Find a Tender, Open Government Licence). Each name was published as the enquiry contact '
        +'for the notice shown — that notice is your reason to make contact, and there is no job-title '
        +'field in the data, so do not assume seniority. People move: verify before you use a name.</div>'
        +'<div style="overflow-x:auto"><table class="mst__ctbl"><tr><th>Name</th><th>Contact</th>'
        +'<th>Last seen</th><th>Notice it came from</th></tr>';
      list.slice(0,12).forEach(function(c){
        h+='<tr><td><b>'+esc(c.name)+'</b>'+(c.n>1?'<br><span style="color:var(--muted)">'+c.n
          +' notices</span>':'')+'</td><td>'
          +(c.email?'<a href="mailto:'+esc(c.email)+'">'+esc(c.email)+'</a>':'—')
          +(c.tel?'<br>'+esc(c.tel):'')+'</td><td>'+esc(c.last)+'</td><td>'
          +esc(c.notice||'—')+'</td></tr>';
      });
      h+='</table></div>';
      if(list.length>12)h+='<div class="mst__empty">Showing the 12 most recent of '+list.length+'.</div>';
    }

    /* Observed changes — a change of named contact, never an inferred appointment. */
    h+='<div class="mst__role" style="margin:16px 0 2px">Recent changes in who is named</div>';
    if(moves===null){
      h+='<div class="mst__empty">Loading…</div>';
    }else if(!moves.length){
      h+='<div class="mst__empty">'+(MOVES.unavailable
        ?'The change index could not be loaded just now. '
        :'No change of named contact observed for this trust. ')+'This tracks one '
        +'specific, evidenced thing: when the person named on this trust’s procurement notices changes. '
        +'It is not a feed of announced appointments — no public register of NHS procurement job moves '
        +'exists, which is exactly why the relationship is worth something.</div>';
    }else{
      h+='<div class="mst__empty" style="margin-bottom:4px">A new name appearing where a different one used '
        +'to sign the notices. Evidence that a remit changed — not an announced appointment. Worth a call: '
        +'someone new in post has no incumbent supplier loyalty yet.</div>'
        +'<div style="overflow-x:auto"><table class="mst__ctbl"><tr><th>New name</th><th>First seen</th>'
        +'<th>Where they appear to have taken over from</th></tr>';
      moves.slice(0,8).forEach(function(m){
        h+='<tr><td><b>'+esc(m.name)+'</b>'+(m.email?'<br><a href="mailto:'+esc(m.email)+'">'
          +esc(m.email)+'</a>':'')+'</td><td>'+esc(m.firstSeen)+'</td><td>'
          +(m.replaces?esc(m.replaces)+(m.replacesLastSeen?' (last seen '+esc(m.replacesLastSeen)+')':''):'—')
          +'</td></tr>';
      });
      h+='</table></div>';
    }
    /* Article 14 UK GDPR: these people did not give us their details, so they are
       owed an explanation of where they came from — within one month, or at first
       contact, whichever is sooner. The member making the approach is the one who
       discharges that, so the wording they need is spelled out here rather than
       buried in a privacy notice they will never read. */
    h+='<div class="mst__empty" style="margin-top:10px;border-top:1px dashed rgba(0,0,0,.14);padding-top:8px">'
      +'<b>Where these came from, and what you owe them.</b> Source: Find a Tender OCDS API, Open '
      +'Government Licence v3'+(CONTACTS&&CONTACTS.asOf?' · index as at '+esc(CONTACTS.asOf):'')
      +'. Each person was named as the enquiry contact on the public procurement notice shown — these '
      +'are work contact details published for that purpose, not a mailing list, and nobody here gave '
      +'you their details directly. <b>UK GDPR Article 14 means you must tell them where you got them, '
      +'at first contact.</b> One line does it: <i>“I found your details on [trust]’s notice for '
      +'[subject] on Find a Tender.”</i> That is also a better opener than anything cold. Approach under '
      +'the Hub’s outreach standard — short, problem-first, about the notice. If someone asks you not to '
      +'contact them again, stop, and tell us so we can drop them from the index.</div></div>';
    host.innerHTML=h;
  }

  /* ---- account map sheet (print + CSV) ---------------------------------- */
  function sheetRows(p,s){
    var keys=stakeKeys(p,s), t=selectedTrust();
    return keys.map(function(k){
      var lib=L[k]; if(!lib)return null;
      var r=ROUTE[k]||{}, tier=TIER[r.tier||'earn'];
      return {role:lib.role,
              who:s==='primary'?(lib.whoPri||lib.whoSec):lib.whoSec,
              cares:lib.cares||'',
              hook:lib.hook||'',
              tier:tier[0], tierColour:tier[1],
              how:stripTags(r.how||''),
              li:(t&&r.li)?liURL(t.n,r.li):''};
    }).filter(Boolean);
  }
  function sheetHead(p,s){
    var t=selectedTrust();
    return {trust:t?t.n:('Whole ICB — '+$('m-geo').value),
            code:t?t.code:'', town:t?[t.town,t.postcode].filter(Boolean).join(' '):'',
            kind:t?(t.kind||''):'', icb:t?('NHS '+t.icbName+' ICB'):$('m-geo').value,
            region:t?(t.region||''):'',
            bc:(t&&t.bc==='DLN')?BUYING_CENTRE_NOTE:'',
            product:p.n, spec:p.area, problem:p.p,
            setting:s==='secondary'?'Acute trust / hospital':'Primary care, community and ICB',
            trustObj:t};
  }
  function today(){
    var d=new Date(), z=function(n){return (n<10?'0':'')+n;};
    return z(d.getDate())+'/'+z(d.getMonth()+1)+'/'+d.getFullYear();
  }
  function buildSheetHTML(p,s){
    var H=sheetHead(p,s), rows=sheetRows(p,s), t=H.trustObj;
    var steps=[];
    var pathEl=$('m-path');
    if(pathEl){
      Array.prototype.forEach.call(pathEl.querySelectorAll('.mst__step2'),function(el){
        var b=el.querySelector('b'), st=el.querySelector('strong');
        if(b&&st)steps.push([b.textContent,st.textContent]);});
    }
    var css='body{font-family:Inter,-apple-system,"Segoe UI",Arial,sans-serif;color:#1d2733;'
      +'font-size:10.5px;line-height:1.45;margin:0;padding:16px}'
      +'h1{font-size:17px;margin:0 0 3px}h2{font-size:11.5px;text-transform:uppercase;letter-spacing:1px;'
      +'margin:16px 0 6px;color:#6B2A34;border-bottom:1px solid #e6e0d4;padding-bottom:3px}'
      +'.meta{font-size:10px;color:#4a5766;margin:0 0 4px}'
      +'table{width:100%;border-collapse:collapse;margin-bottom:6px}'
      +'th{background:#f7f4ee;text-align:left;font-size:8.5px;text-transform:uppercase;letter-spacing:.6px;'
      +'color:#5a6675;border:1px solid #d9d2c4;padding:4px 5px}'
      +'td{border:1px solid #d9d2c4;padding:4px 5px;vertical-align:top}'
      +'.fill{background:#fcfbf8}.pill{display:inline-block;font-size:7.5px;font-weight:700;color:#fff;'
      +'padding:1px 5px;border-radius:99px;text-transform:uppercase;letter-spacing:.4px}'
      +'.note{font-size:9px;color:#5a6675;background:#f7f4ee;border-left:3px solid #9A7A2E;'
      +'padding:6px 8px;margin:6px 0}'
      +'.foot{font-size:8.5px;color:#7a838f;margin-top:14px;border-top:1px solid #e6e0d4;padding-top:6px}'
      +'@page{size:A4;margin:11mm}'
      +'@media print{.noprint{display:none}}';
    var h='<h1>Account map — '+esc(H.trust)+'</h1>'
      +'<p class="meta">'+[H.code?'ODS '+esc(H.code):'',esc(H.town),esc(H.kind),esc(H.icb),esc(H.region)]
        .filter(Boolean).join(' &middot; ')+'</p>'
      +'<p class="meta"><b>Product:</b> '+esc(H.product)+' &middot; <b>Speciality:</b> '+esc(H.spec)
      +' &middot; <b>Setting:</b> '+esc(H.setting)+'</p>'
      +'<p class="meta"><b>Problem to anchor on:</b> '+esc(H.problem)+'</p>'
      +'<p class="meta"><b>Rep:</b> ______________________  <b>Prepared:</b> '+today()
      +'  <b>Review by:</b> ______________</p>';
    if(H.bc)h+='<div class="note"><b>Buying centre.</b> '+esc(H.bc)+'</div>';
    h+='<div class="note">Three people have to line up on almost every NHS purchase: a <b>clinical champion</b> '
      +'who wants it, a <b>procurement gatekeeper</b> who can buy it compliantly, and a <b>budget holder</b> who '
      +'will fund it. If any one of the three is blank, the deal is not yet real.</div>';
    h+='<h2>Stakeholders — fill in the names</h2><table><tr>'
      +'<th style="width:14%">Role</th><th style="width:17%">Who this is</th>'
      +'<th style="width:11%">Name findable?</th><th style="width:16%">Name</th>'
      +'<th style="width:13%">Job title</th><th style="width:17%">Email / phone</th>'
      +'<th style="width:6%">Met?</th><th style="width:6%">Date</th></tr>';
    rows.forEach(function(r){
      h+='<tr><td><b>'+esc(r.role)+'</b></td><td>'+esc(r.who)+'</td>'
        +'<td><span class="pill" style="background:'+r.tierColour+'">'+esc(r.tier)+'</span></td>'
        +'<td class="fill">&nbsp;</td><td class="fill">&nbsp;</td><td class="fill">&nbsp;</td>'
        +'<td class="fill">&nbsp;</td><td class="fill">&nbsp;</td></tr>';
    });
    h+='</table>';
    h+='<h2>What each one cares about, and your hook</h2><table><tr>'
      +'<th style="width:14%">Role</th><th style="width:30%">Cares about</th>'
      +'<th style="width:28%">Your hook</th><th style="width:28%">What you learned / next action</th></tr>';
    rows.forEach(function(r){
      h+='<tr><td><b>'+esc(r.role)+'</b></td><td>'+esc(r.cares)+'</td><td>'+esc(r.hook)
        +'</td><td class="fill">&nbsp;</td></tr>';
    });
    h+='</table>';
    var held=contactsFor(t);
    if(held&&held.length){
      h+='<h2>Names already published for this trust</h2>'
        +'<p class="meta">From this trust’s own Find a Tender notices (Open Government Licence). '
        +'No job-title field exists in the source — do not assume seniority. Verify before use.</p>'
        +'<table><tr><th style="width:22%">Name</th><th style="width:26%">Contact</th>'
        +'<th style="width:12%">Last seen</th><th style="width:40%">Notice</th></tr>';
      held.slice(0,10).forEach(function(c){
        h+='<tr><td>'+esc(c.name)+'</td><td>'+esc(c.email||'—')+(c.tel?'<br>'+esc(c.tel):'')
          +'</td><td>'+esc(c.last)+'</td><td>'+esc(c.notice||'—')+'</td></tr>';});
      h+='</table>';
    }
    if(steps.length){
      h+='<h2>Buying pathway — where this account actually is</h2><table><tr>'
        +'<th style="width:5%">#</th><th style="width:33%">Step</th><th style="width:14%">Status</th>'
        +'<th style="width:14%">Date / meeting</th><th style="width:34%">Notes</th></tr>';
      steps.forEach(function(st){
        h+='<tr><td>'+esc(st[0])+'</td><td>'+esc(st[1])+'</td><td class="fill">&nbsp;</td>'
          +'<td class="fill">&nbsp;</td><td class="fill">&nbsp;</td></tr>';});
      h+='</table>';
    }
    h+='<h2>Where to look for the names you are missing</h2><table><tr>'
      +'<th style="width:16%">Role</th><th style="width:84%">Route to a real name</th></tr>';
    rows.forEach(function(r){
      if(!r.how)return;
      h+='<tr><td><b>'+esc(r.role)+'</b></td><td>'+esc(r.how)+'</td></tr>';});
    h+='</table>';
    h+='<div class="foot">Medical Sales Hub — Stakeholder Mapper. Roles, levers and the buying pathway '
      +'reflect standard NHS structures. Organisation data: NHS Organisation Data Service (Open Government '
      +'Licence)'+(TRUST_ASOF?', as at '+esc(TRUST_ASOF):'')+'. Named contacts, where shown: Find a Tender '
      +'(Open Government Licence). Individuals move — confirm every name against the trust before you use '
      +'it. Structures are changing through 2026–27. General guidance, not procurement or legal advice.</div>';
    return {title:'Account map — '+H.trust, css:css, body:h};
  }
  function printSheet(p,s){
    var d=buildSheetHTML(p,s);
    /* An iframe rather than window.open — popup blockers kill the latter and the
       member just sees nothing happen. */
    var old=document.getElementById('mst-printframe');
    if(old)old.parentNode.removeChild(old);
    var f=document.createElement('iframe');
    f.id='mst-printframe';
    f.setAttribute('aria-hidden','true');
    f.style.cssText='position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden';
    document.body.appendChild(f);
    var doc=f.contentWindow.document;
    doc.open();
    doc.write('<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><title>'
      +esc(d.title)+'</title><style>'+d.css+'</style></head><body>'+d.body+'</body></html>');
    doc.close();
    setTimeout(function(){try{f.contentWindow.focus();f.contentWindow.print();}catch(e){}},350);
  }
  function csvCell(v){return '"'+String(v==null?'':v).replace(/"/g,'""')+'"';}
  function downloadCSV(p,s){
    var H=sheetHead(p,s), rows=sheetRows(p,s), t=H.trustObj;
    var out=[];
    out.push(['Account map',H.trust,'ODS code',H.code,'Prepared',today()].map(csvCell).join(','));
    out.push(['ICB',H.icb,'Region',H.region,'Type',H.kind,'Location',H.town].map(csvCell).join(','));
    out.push(['Product',H.product,'Speciality',H.spec,'Setting',H.setting].map(csvCell).join(','));
    out.push(['Problem to anchor on',H.problem].map(csvCell).join(','));
    if(H.bc)out.push(['Buying centre',H.bc].map(csvCell).join(','));
    out.push('');
    out.push(['Role','Who this is','Name findable?','Name','Job title','Email','Phone','Met? (Y/N)',
              'Date met','What they care about','Your hook','Next action',
              'Route to a real name','LinkedIn search'].map(csvCell).join(','));
    rows.forEach(function(r){
      out.push([r.role,r.who,r.tier,'','','','','','',r.cares,r.hook,'',r.how,r.li]
        .map(csvCell).join(','));
    });
    var held=contactsFor(t);
    if(held&&held.length){
      out.push('');
      out.push(['Names already published for this trust (Find a Tender, OGL) — no job-title field exists '
                +'in the source; verify before use'].map(csvCell).join(','));
      out.push(['Name','Email','Phone','First seen','Last seen','Notices','Notice it came from']
        .map(csvCell).join(','));
      held.forEach(function(c){
        out.push([c.name,c.email,c.tel,c.first,c.last,c.n,c.notice].map(csvCell).join(','));});
    }
    var moves=movesFor(t);
    if(moves&&moves.length){
      out.push('');
      out.push(['Observed changes of named contact — evidence of a changed remit, not an announced '
                +'appointment'].map(csvCell).join(','));
      out.push(['New name','Email','First seen','Appears to have taken over from','Predecessor last seen']
        .map(csvCell).join(','));
      moves.forEach(function(m){
        out.push([m.name,m.email,m.firstSeen,m.replaces||'',m.replacesLastSeen||''].map(csvCell).join(','));});
    }
    out.push('');
    out.push(['Sources: NHS Organisation Data Service (Open Government Licence)'
      +(TRUST_ASOF?', as at '+TRUST_ASOF:'')+'; Find a Tender (Open Government Licence). '
      +'Individuals move — confirm every name against the trust before use.'].map(csvCell).join(','));
    /* BOM so Excel opens UTF-8 correctly — without it "Guy's" arrives mangled. */
    var blob=new Blob(['\ufeff'+out.join('\r\n')],{type:'text/csv;charset=utf-8;'});
    var a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download='account-map-'+(t?t.code+'-'+t.n:'icb').toLowerCase()
      .replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')+'.csv';
    document.body.appendChild(a);a.click();
    setTimeout(function(){URL.revokeObjectURL(a.href);a.parentNode.removeChild(a);},1500);
  }
  function renderToolbar(p,s){
    var host=$('m-sheet'); if(!host)return;
    var t=selectedTrust();
    host.innerHTML='<div class="mst__c" style="grid-column:1/-1">'
      +'<div class="mst__f" style="margin:0 0 4px"><b style="color:var(--ink)">Take this account map with you</b>'
      +'<br>'+(t?('A one-page sheet for <b>'+esc(t.n)+'</b> with every stakeholder listed and blank fields for '
        +'the real names, titles and contact details — fill it in as you meet people. The CSV opens in '
        +'Excel and carries the LinkedIn search links and the name routes.')
       :('Pick a trust above and this becomes a per-account sheet. Without one you still get the ICB-level '
        +'map — useful, but there is nobody to name.'))+'</div>'
      +'<div class="mst__toolbar">'
      +'<button class="mst__btn mst__btn--primary" id="m-print" type="button">Print account map (A4)</button>'
      +'<button class="mst__btn" id="m-csv" type="button">Download as CSV</button></div></div>';
    $('m-print').addEventListener('click',function(){printSheet(p,s);});
    $('m-csv').addEventListener('click',function(){downloadCSV(p,s);});
  }

  /* Mount points, appended once after the existing cards grid. */
  function ensureMounts(){
    var cards=$('m-cards'); if(!cards)return;
    ['m-contacts','m-sheet'].forEach(function(id){
      if($(id))return;
      var d=document.createElement('div');
      d.id=id; d.className='mst__cards';
      cards.parentNode.insertBefore(d,cards.nextSibling);
    });
  }

  $('m-spec').addEventListener('change',function(){state.spec=this.value;state.prodIdx=0;fillProd();render();});
  $('m-prod').addEventListener('change',function(){state.prodIdx=parseInt(this.value,10);render();});
  $('m-geo').addEventListener('change',function(){fillTrust();render();});
  $('m-sec').addEventListener('click',function(){state.setting='secondary';render();});
  $('m-pri').addEventListener('click',function(){state.setting='primary';render();});
  $('tab-map').addEventListener('click',function(){showTab('map');});
  $('tab-calc').addEventListener('click',function(){showTab('calc');calc();});
  ['c-prob','c-cost','c-vol','c-eff','c-dir','c-price','c-units','c-cash'].forEach(function(id){$(id).addEventListener('input',calc);});
  $('c-copy').addEventListener('click',copy);
  injectCSS();fillGeo();fillSpec();fillProd();ensureMounts();render();calc();loadTrustData();
})();
