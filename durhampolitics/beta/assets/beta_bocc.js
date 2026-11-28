/* Durham BOCC Natural-Language Search & Decision Explorer */
(function () {
  let BOCC = null;
  let ACTIVE_TAB = "search";
  let ACTIVE_STREAM = "all";
  let SEARCH_LIMIT = 35;
  let ARCHIVE_LIMIT = 40;
  let SELECTED_EVO = new Set();

  const PALETTE = ["#f59e0b", "#38bdf8", "#10b981", "#f472b6", "#a78bfa", "#fb7185", "#34d399", "#facc15"];
  const CURRENT_BOCC = ["Nida Allam", "Michelle Burton", "Wendy Jacobs", "Stephen Valentine", "Mike Lee", "Brenda Howerton", "Heidi Carter", "Nimasheena Burns"];

  const STOPWORDS = new Set([
    "give","me","show","find","get","list","search","all","any","the","a","an","of","for","to","in","on","at","by","with",
    "about","from","where","when","who","what","which","that","this","these","those","is","are","was","were","and","or",
    "bocc","county","commissioner","commissioners","board","meeting","meetings","document","documents","docs","file","files","decision","decisions"
  ]);

  const DOMAIN_SYNONYMS = [
    { cat: "Budget & Taxes", words: ["tax","taxes","property tax","revaluation","budget","bond","bonds","sales tax","appropriation","fiscal","capital","cip","ordinance amendment","boa","cpa","fund balance","debt","deficit","audit"] },
    { cat: "School Facilities & Closures", words: ["school","schools","dps","durham public schools","durham tech","pre-k","prek","education","teacher","teachers","classified","school funding","school bond","campus"] },
    { cat: "Zoning & Development (SCAD)", words: ["zoning","rezoning","udo","planning","jccpc","annexation","site plan","watershed","development","developer","subdivision","comprehensive plan","land use","rural","suburban","open space","scad"] },
    { cat: "Affordable Housing", words: ["housing","affordable","homeless","homelessness","eviction","rent","rental","tenant","dha","shelter","housing bond"] },
    { cat: "Community Safety & HEART", words: ["sheriff","detention","jail","fire","ems","911","emergency","police","cops","heart","crime","violence","gun","criminal justice","reentry","public safety","birkhead","andrews"] },
    { cat: "Transit & Public Works", words: ["transit","bus","rail","light rail","gotriangle","commuter","sewer","water","stormwater","solid waste","landfill","recycling","sidewalk","road","park","trail","sustainability","climate"] },
    { cat: "Staff Compensation & Labor", words: ["salary","pay","raises","compensation","living wage","staff","employee","employees","benefits","union","personnel","hiring","retention","county manager","sowell","davis"] },
    { cat: "Governance & Transparency", words: ["dss","social services","public health","medicaid","mental health","alliance","library","libraries","interlocal","contract","grant","arpa","appointment","clerk","minutes","election","voting"] },
  ];

  const OPPOSE_RE = /\b(oppos\w*|object\w*|dissent\w*|against|nay|nays|vote\w*\s+no|reject\w*|split|concern\w*)\b/i;
  const SUPPORT_RE = /\b(support\w*|favor\w*|aye|ayes|vote\w*\s+yes|approv\w*)\b/i;

  const TOPIC_COLS = [
    { key: "all", label: "Overall" },
    { key: "Budget & Taxes", label: "Budget & Taxes" },
    { key: "Zoning & Development (SCAD)", label: "Zoning & Land Use" },
    { key: "School Facilities & Closures", label: "Schools & Education" },
    { key: "Community Safety & HEART", label: "Public Safety" },
    { key: "Affordable Housing", label: "Housing" },
    { key: "Transit & Public Works", label: "Transit & Infra" },
    { key: "Governance & Transparency", label: "Governance & HHS" },
  ];

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function pctStyle(pct, n) {
    if (pct == null || !n) return "background:#0a101d;color:#475569;";
    if (pct >= 92) return "background:rgba(16,185,129,0.28);color:#6ee7b7;";
    if (pct >= 78) return "background:rgba(56,189,248,0.22);color:#bae6fd;";
    if (pct >= 58) return "background:rgba(245,158,11,0.24);color:#fde68a;";
    return "background:rgba(239,68,68,0.30);color:#fca5a5;";
  }

  window.__onBetaAuthUnlocked = async function () {
    try {
      const resp = await fetch("./data/bocc_intelligence.json", { cache: "no-store" });
      BOCC = await resp.json();
      initFilters();
      renderKpis();
      selectBoccCurrent();
      runBoccNlSearch();
      renderBoccMembers();
      renderBoccArchive();
    } catch (e) {
      document.getElementById("boccSearchResults").innerHTML =
        `<div class="res-card" style="color:#fca5a5;">Failed to load BOCC intelligence index: ${esc(e.message)}</div>`;
    }
  };

  function initFilters() {
    const yrs = new Set();
    (BOCC.matters || []).forEach(m => { if (m.d) yrs.add(m.d.slice(0, 4)); });
    (BOCC.votes || []).forEach(v => { if (v.d) yrs.add(v.d.slice(0, 4)); });
    const sortedYrs = Array.from(yrs).filter(y => /^20\d\d$/.test(y)).sort((a, b) => b.localeCompare(a));
    ["boccNlYear", "matYear"].forEach(id => {
      const sel = document.getElementById(id);
      sortedYrs.forEach(y => {
        const o = document.createElement("option");
        o.value = y; o.textContent = y;
        sel.appendChild(o);
      });
    });
  }

  function renderKpis() {
    const s = BOCC.summary || {};
    document.getElementById("boccKpis").innerHTML = `
      <div class="kpi"><div class="kpi-lbl">Official Agendas Linked</div><div class="kpi-val" style="color:#fcd34d;">${(s.legistar_events || 0) + (s.granicus_events || 0)}</div><div class="kpi-sub">${s.legistar_events || 0} Legistar + ${s.granicus_events || 0} Granicus (2006&ndash;26)</div></div>
      <div class="kpi"><div class="kpi-lbl">Legistar Action Memos</div><div class="kpi-val" style="color:#6ee7b7;">${(s.matters_total || 0).toLocaleString()}</div><div class="kpi-sub">${(s.matters_with_text || 0).toLocaleString()} full-text parsed</div></div>
      <div class="kpi"><div class="kpi-lbl">Supporting Attachments</div><div class="kpi-val" style="color:#93c5fd;">${(s.attachments_total || 0).toLocaleString()}</div><div class="kpi-sub">${(s.fiscal_matters_count || 0).toLocaleString()} matters with fiscal $</div></div>
      <div class="kpi"><div class="kpi-lbl">BOCC Votes Tracked</div><div class="kpi-val" style="color:#c4b5fd;">${(s.votes_total || 0).toLocaleString()}</div><div class="kpi-sub">${s.split_votes_total || 0} split / contested votes</div></div>
      <div class="kpi"><div class="kpi-lbl">Recorded Debates</div><div class="kpi-val" style="color:#fca5a5;">${s.debates_total || 0}</div><div class="kpi-sub">Across ${s.db_meetings || 0} BOCC meetings</div></div>
    `;
  }

  window.setBoccTab = function (tab) {
    ACTIVE_TAB = tab;
    document.querySelectorAll(".bocc-tab").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
    document.querySelectorAll(".bocc-panel").forEach(p => p.classList.toggle("active", p.id === "panel-" + tab));
    if (tab === "members") renderBoccMembers();
    if (tab === "matters") renderBoccArchive();
  };

  window.setBoccStream = function (st) {
    ACTIVE_STREAM = st;
    SEARCH_LIMIT = 35;
    document.querySelectorAll("#boccStreamTabs .stream-btn").forEach(b => b.classList.toggle("active", b.dataset.stream === st));
    runBoccNlSearch();
  };

  window.tryBoccQuery = function (q) {
    document.getElementById("boccNlInput").value = q;
    SEARCH_LIMIT = 35;
    setBoccTab("search");
    runBoccNlSearch();
  };

  window.clearBoccSearch = function () {
    document.getElementById("boccNlInput").value = "";
    document.getElementById("boccNlYear").value = "";
    SEARCH_LIMIT = 35;
    runBoccNlSearch();
  };

  window.loadMoreBoccSearch = function () {
    SEARCH_LIMIT += 40;
    runBoccNlSearch();
  };

  function parseQuery(raw) {
    const q = (raw || "").trim().toLowerCase();
    const years = (q.match(/\b20[012]\d\b/g) || []);
    let stance = "";
    if (OPPOSE_RE.test(q)) stance = "oppose";
    else if (SUPPORT_RE.test(q)) stance = "support";

    const matchedMembers = [];
    const memTokens = new Set();
    (BOCC.members || []).forEach(m => {
      const full = m.name.toLowerCase();
      const parts = full.replace(/[^a-z\s-]/g, "").split(/\s+/);
      const last = parts[parts.length - 1];
      if (q.includes(full) || (last.length >= 4 && new RegExp("\\b" + last + "\\b", "i").test(q))) {
        matchedMembers.push(m.name);
        parts.forEach(p => memTokens.add(p));
      }
    });

    const topics = [];
    const synWords = [];
    DOMAIN_SYNONYMS.forEach(ds => {
      const hits = ds.words.filter(w => q.includes(w));
      if (hits.length) {
        topics.push(ds.cat);
        hits.forEach(h => synWords.push(h));
      }
    });

    const terms = q.replace(/[^a-z0-9\s-]/g, " ").split(/\s+/).filter(w =>
      w.length >= 2 && !STOPWORDS.has(w) && !memTokens.has(w) && !/^20\d\d$/.test(w) &&
      !OPPOSE_RE.test(w) && !SUPPORT_RE.test(w)
    );
    return { raw, q, years, stance, members: matchedMembers, topics, synWords, terms: Array.from(new Set(terms)) };
  }

  window.runBoccNlSearch = function () {
    if (!BOCC) return;
    const raw = document.getElementById("boccNlInput").value || "";
    const yrSel = document.getElementById("boccNlYear").value;
    const intent = parseQuery(raw);
    if (yrSel && !intent.years.includes(yrSel)) intent.years.push(yrSel);

    const hasQuery = Boolean(intent.q || yrSel);
    const badgeParts = [];
    if (intent.members.length) badgeParts.push(`Commissioners: <strong>${esc(intent.members.join(", "))}</strong>`);
    if (intent.stance) badgeParts.push(`Stance: <strong>${esc(intent.stance)}</strong>`);
    if (intent.topics.length) badgeParts.push(`Topics: <strong>${esc(intent.topics.join(", "))}</strong>`);
    if (intent.years.length) badgeParts.push(`Year: <strong>${esc(intent.years.join(", "))}</strong>`);
    if (intent.terms.length) badgeParts.push(`Keywords: <strong>${esc(intent.terms.join(", "))}</strong>`);
    document.getElementById("boccIntentBadge").innerHTML = hasQuery
      ? (badgeParts.join(" &bull; ") || "Showing recent highlights")
      : "Showing recent BOCC split votes, policy debates, and high-impact Legistar Action Memos — ask any plain-English question above to search across 2006–2026.";

    const results = [];

    // 1. Score Official Legistar Matters & Attachments
    if (!intent.members.length || !intent.stance) {
      for (const m of (BOCC.matters || [])) {
        if (intent.years.length && (!m.d || !intent.years.includes(m.d.slice(0, 4)))) continue;
        let sc = 0;
        if (!hasQuery) {
          if (m.fi && (m.docs || []).length > 0) sc = 20;
          else continue;
        } else {
          const hay = m._q || (m._q = `${m.f || ""} ${m.t} ${m.cat || ""} ${m.sum || ""} ${m.rec || ""} ${m.fi || ""} ${m.cn || ""} ${(m.docs || []).map(x => x.t).join(" ")}`.toLowerCase());
          const tLow = (m.t || "").toLowerCase();
          let hits = 0;
          for (const term of intent.terms) {
            if (tLow.includes(term)) { sc += 18; hits++; }
            else if (hay.includes(term)) { sc += 9; hits++; }
          }
          for (const mn of intent.members) {
            const last = mn.toLowerCase().split(/\s+/).pop();
            if (hay.includes(last)) { sc += 14; hits++; }
          }
          if (intent.terms.length && hits === 0) continue;
          if (!intent.terms.length && intent.topics.length) {
            const sh = intent.synWords.filter(w => hay.includes(w)).length;
            if (!sh) continue;
            sc += sh * 10;
          }
          if (m.fi) sc += 5;
          if ((m.docs || []).length) sc += 4;
          if (sc <= 0 && !yrSel) continue;
          if (yrSel && !intent.q) sc = 10;
        }
        results.push({ kind: "matters", score: sc, date: m.d || "", item: m });
      }
    }

    // 2. Score BOCC Votes
    for (const v of (BOCC.votes || [])) {
      if (intent.years.length && (!v.d || !intent.years.includes(v.d.slice(0, 4)))) continue;
      let sc = 0;
      if (!hasQuery) {
        if (!v.sp) continue;
        sc = 26;
      } else {
        const hay = v._q || (v._q = `${v.t} ${v.c} ${v.n || ""} ${(v.ay || []).join(" ")} ${(v.ny || []).join(" ")}`.toLowerCase());
        const ayesL = (v.ay || []).join(" ").toLowerCase();
        const naysL = (v.ny || []).join(" ").toLowerCase();
        let memHit = false;
        if (intent.members.length) {
          for (const mn of intent.members) {
            const last = mn.toLowerCase().split(/\s+/).pop();
            const inNay = naysL.includes(last);
            const inAye = ayesL.includes(last);
            if (intent.stance === "oppose" && inNay) { sc += 55; memHit = true; }
            else if (intent.stance === "support" && inAye) { sc += 40; memHit = true; }
            else if (!intent.stance && (inNay || inAye)) { sc += inNay ? 35 : 22; memHit = true; }
          }
          if (!memHit) continue;
        } else if (intent.stance === "oppose") {
          if (!v.sp) continue;
          sc += 25;
        }
        let tHits = 0;
        for (const term of intent.terms) {
          if ((v.t || "").toLowerCase().includes(term)) { sc += 18; tHits++; }
          else if (hay.includes(term)) { sc += 9; tHits++; }
        }
        if (intent.topics.includes(v.c)) sc += 18;
        if (intent.terms.length && tHits === 0 && !memHit) continue;
        if (v.sp) sc += 8;
        if (sc <= 0 && !yrSel) continue;
        if (yrSel && !intent.q) sc = v.sp ? 18 : 8;
      }
      results.push({ kind: "votes", score: sc, date: v.d || "", item: v });
    }

    // 3. Score Recorded Debates
    for (const db of (BOCC.debates || [])) {
      if (intent.years.length && (!db.d || !intent.years.includes(db.d.slice(0, 4)))) continue;
      let sc = 0;
      if (!hasQuery) {
        sc = 28;
      } else {
        const hay = db._q || (db._q = `${db.t} ${db.c} ${db.s} ${db.sa} ${db.sb} ${(db.sam || []).join(" ")} ${(db.sbm || []).join(" ")}`.toLowerCase());
        let memHit = false;
        if (intent.members.length) {
          for (const mn of intent.members) {
            const last = mn.toLowerCase().split(/\s+/).pop();
            if (hay.includes(last)) { sc += 30; memHit = true; }
          }
          if (!memHit) continue;
        }
        let tHits = 0;
        for (const term of intent.terms) {
          if ((db.t || "").toLowerCase().includes(term)) { sc += 20; tHits++; }
          else if (hay.includes(term)) { sc += 10; tHits++; }
        }
        if (intent.topics.includes(db.c)) sc += 20;
        if (intent.terms.length && tHits === 0 && !memHit) continue;
        if (sc <= 0 && !yrSel) continue;
        if (yrSel && !intent.q) sc = 15;
      }
      results.push({ kind: "debates", score: sc, date: db.d || "", item: db });
    }

    const counts = { all: results.length, matters: 0, votes: 0, debates: 0 };
    results.forEach(r => counts[r.kind]++);
    document.querySelectorAll("#boccStreamTabs .stream-btn").forEach(b => {
      const k = b.dataset.stream;
      const lbl = k === "all" ? "All Results" : k === "matters" ? "Official Legistar Matters & Docs" : k === "votes" ? "BOCC Votes & Splits" : "Recorded Debates";
      b.textContent = `${lbl} (${counts[k]})`;
    });

    const filtered = ACTIVE_STREAM === "all" ? results : results.filter(r => r.kind === ACTIVE_STREAM);
    filtered.sort((a, b) => (b.score - a.score) || b.date.localeCompare(a.date));

    const shown = filtered.slice(0, SEARCH_LIMIT);
    const outEl = document.getElementById("boccSearchResults");
    if (!shown.length) {
      outEl.innerHTML = `<div class="res-card" style="color:var(--muted);">No matching BOCC matters, votes, or debates found. Try broader keywords.</div>`;
      document.getElementById("boccSearchMore").innerHTML = "";
      return;
    }

    outEl.innerHTML = shown.map(r => {
      const x = r.item;
      if (r.kind === "matters") {
        return renderMatterCard(x);
      }
      if (r.kind === "votes") {
        return `
          <article class="res-card">
            <div class="res-top">
              <div>
                <div class="res-title">${esc(x.t)}</div>
                <div class="res-meta">${esc(x.d)} &bull; ${esc(x.mt || "BOCC Meeting")}</div>
              </div>
              <div>
                <span class="b-pill ${x.sp ? "" : "green"}">${esc(x.o)} (${esc(x.tl)})</span>
                <span class="b-pill blue">${esc(x.c)}</span>
              </div>
            </div>
            ${x.sp && (x.ay || []).length ? `<div style="font-size:12px;color:#6ee7b7;margin-top:6px;"><strong>Ayes:</strong> ${esc(x.ay.join(", "))}</div>` : ""}
            ${(x.ny || []).length ? `<div style="font-size:12px;color:#fca5a5;margin-top:3px;"><strong>Nays:</strong> ${esc(x.ny.join(", "))}</div>` : ""}
            ${x.n ? `<div class="res-body">${esc(x.n)}</div>` : ""}
            <div class="doc-links-row">
              ${x.v ? `<a class="doc-btn" style="border-color:#2563eb;color:#93c5fd;" href="${esc(x.v)}" target="_blank" rel="noopener">&#9654; Watch Video${x.ts ? " @" + esc(x.ts) : ""}</a>` : ""}
              ${x.pdf ? `<a class="doc-btn" style="border-color:#dc2626;color:#fca5a5;" href="${esc(x.pdf)}" target="_blank" rel="noopener">&#128196; Executive Summary PDF</a>` : ""}
              ${x.au ? `<a class="doc-btn" style="border-color:var(--bocc);color:#fcd34d;" href="${esc(x.au)}" target="_blank" rel="noopener">&#128206; Official Agenda / Legistar</a>` : ""}
            </div>
          </article>
        `;
      }
      return `
        <article class="res-card">
          <div class="res-top">
            <div>
              <div class="res-title">${esc(x.t)}</div>
              <div class="res-meta">${esc(x.d)} &bull; ${esc(x.mt || "BOCC Debate")}</div>
            </div>
            <div>
              <span class="b-pill purple">Debate</span>
              <span class="b-pill blue">${esc(x.c)}</span>
            </div>
          </div>
          <div class="res-body">${esc(x.s)}</div>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px;margin-top:8px;font-size:12px;">
            <div style="background:var(--surface);padding:8px 10px;border-radius:8px;border-left:3px solid #38bdf8;">
              <strong style="color:#93c5fd;">Side A:</strong> ${esc(x.sa)}
              ${(x.sam || []).length ? `<div style="color:var(--dim);margin-top:3px;">${esc(x.sam.join(", "))}</div>` : ""}
            </div>
            <div style="background:var(--surface);padding:8px 10px;border-radius:8px;border-left:3px solid #f59e0b;">
              <strong style="color:#fcd34d;">Side B:</strong> ${esc(x.sb)}
              ${(x.sbm || []).length ? `<div style="color:var(--dim);margin-top:3px;">${esc(x.sbm.join(", "))}</div>` : ""}
            </div>
          </div>
          <div class="doc-links-row">
            ${x.v ? `<a class="doc-btn" style="border-color:#2563eb;color:#93c5fd;" href="${esc(x.v)}" target="_blank" rel="noopener">&#9654; Watch Video${x.ts ? " @" + esc(x.ts) : ""}</a>` : ""}
            ${x.pdf ? `<a class="doc-btn" style="border-color:#dc2626;color:#fca5a5;" href="${esc(x.pdf)}" target="_blank" rel="noopener">&#128196; Executive Summary PDF</a>` : ""}
            ${x.au ? `<a class="doc-btn" style="border-color:var(--bocc);color:#fcd34d;" href="${esc(x.au)}" target="_blank" rel="noopener">&#128206; Official Agenda / Legistar</a>` : ""}
          </div>
        </article>
      `;
    }).join("");

    document.getElementById("boccSearchMore").innerHTML = filtered.length > SEARCH_LIMIT
      ? `<button class="nav-btn" onclick="loadMoreBoccSearch()">Load More (${filtered.length - SEARCH_LIMIT} remaining)</button>`
      : "";
  };

  function renderMatterCard(x) {
    const docBtns = (x.docs || []).slice(0, 6).map(d =>
      `<a class="doc-btn" style="border-color:var(--bocc);color:#fde68a;" href="${esc(d.u)}" target="_blank" rel="noopener">&#128206; ${esc(d.t)}</a>`
    ).join("");
    const extraDocs = (x.docs || []).length > 6 ? `<span style="font-size:11px;color:var(--dim);align-self:center;">+${x.docs.length - 6} more on Legistar</span>` : "";
    return `
      <article class="res-card">
        <div class="res-top">
          <div>
            <div class="res-title">${x.f ? `<span style="color:#fcd34d;font-family:monospace;">[${esc(x.f)}]</span> ` : ""}${esc(x.t)}</div>
            <div class="res-meta">${esc(x.d || "Undated")}${x.mt ? ` &bull; ${esc(x.mt)}` : ""}${x.cn ? ` &bull; Case: ${esc(x.cn)}` : ""}</div>
          </div>
          <div>
            <span class="b-pill green">${esc(x.cat || "GENERAL")}</span>
            ${x.fi ? `<span class="b-pill">Fiscal: ${esc(x.fi)}</span>` : ""}
          </div>
        </div>
        ${x.sum ? `<div class="res-body">${esc(x.sum)}</div>` : ""}
        ${x.rec ? `<div class="res-rec"><strong>County Manager Recommendation:</strong> ${esc(x.rec)}</div>` : ""}
        <div class="doc-links-row">
          ${docBtns}${extraDocs}
          ${x.mu ? `<a class="doc-btn" href="${esc(x.mu)}" target="_blank" rel="noopener">&#128197; Legistar Meeting</a>` : ""}
          ${x.pdf ? `<a class="doc-btn" style="border-color:#dc2626;color:#fca5a5;" href="${esc(x.pdf)}" target="_blank" rel="noopener">&#128196; Executive Summary PDF</a>` : ""}
        </div>
      </article>
    `;
  }

  window.selectBoccCurrent = function () {
    const avail = new Set((BOCC.members || []).map(m => m.name));
    SELECTED_EVO = new Set(CURRENT_BOCC.filter(n => avail.has(n)).slice(0, 6));
    renderBoccMembers();
  };

  window.selectBoccTop = function (k) {
    SELECTED_EVO = new Set((BOCC.members || []).slice(0, k).map(m => m.name));
    renderBoccMembers();
  };

  window.toggleBoccEvo = function (nm) {
    if (SELECTED_EVO.has(nm)) SELECTED_EVO.delete(nm);
    else SELECTED_EVO.add(nm);
    renderBoccMembers();
  };

  window.drillBoccMemberTopic = function (memberName, topicKey) {
    const q = topicKey === "all" ? `${memberName} opposing` : `${memberName} ${topicKey.split(" ")[0].toLowerCase()}`;
    tryBoccQuery(q);
  };

  window.renderBoccMembers = function () {
    if (!BOCC) return;
    const contestedOnly = document.getElementById("boccMatContested").checked;
    const votes = (BOCC.votes || []).filter(v => !contestedOnly || v.sp);
    const members = (BOCC.members || []).filter(m => m.n >= 5);

    const hdr = TOPIC_COLS.map(c => `<th>${esc(c.label)}</th>`).join("");
    const rows = members.map(m => {
      const mVotes = votes.filter(v => (v.mv && v.mv[m.name]));
      const cells = TOPIC_COLS.map(col => {
        const sub = col.key === "all" ? mVotes : mVotes.filter(v => v.c === col.key);
        const n = sub.length;
        const ayes = sub.filter(v => v.mv[m.name] === "AYE").length;
        const pct = n > 0 ? Math.round((ayes * 1000) / n) / 10 : null;
        const txt = n > 0 ? `${pct.toFixed(0)}%<span class="m-sub">${ayes}/${n}</span>` : "·";
        return `<td class="m-cell" style="${pctStyle(pct, n)}" onclick="drillBoccMemberTopic('${esc(m.name)}','${esc(col.key)}')">${txt}</td>`;
      }).join("");
      return `<tr><td>${esc(m.name)} <span style="color:var(--dim);font-weight:500;">(${mVotes.length})</span></td>${cells}</tr>`;
    }).join("");

    document.getElementById("boccMatrixWrap").innerHTML = `
      <table class="matrix-tbl">
        <thead><tr><th>County Commissioner</th>${hdr}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;

    const colorMap = {};
    let ci = 0;
    members.forEach(m => {
      if (SELECTED_EVO.has(m.name)) { colorMap[m.name] = PALETTE[ci++ % PALETTE.length]; }
    });
    document.getElementById("boccEvoChips").innerHTML = members.map(m => {
      const act = SELECTED_EVO.has(m.name);
      const dot = act ? `<span style="width:9px;height:9px;border-radius:50%;background:${colorMap[m.name]};display:inline-block;"></span>` : "";
      return `<button class="mem-chip ${act ? "active" : ""}" onclick="toggleBoccEvo('${esc(m.name)}')">${dot}${esc(m.name)} (${m.n})</button>`;
    }).join("");

    const years = Array.from(new Set(votes.map(v => (v.d || "").slice(0, 4)).filter(y => /^20\d\d$/.test(y)))).sort();
    const selList = members.filter(m => SELECTED_EVO.has(m.name));
    const series = selList.map(m => ({
      name: m.name,
      color: colorMap[m.name],
      pts: years.map(yr => {
        const sub = votes.filter(v => (v.d || "").startsWith(yr) && v.mv && v.mv[m.name]);
        const n = sub.length;
        const ayes = sub.filter(v => v.mv[m.name] === "AYE").length;
        return { yr, n, ayes, pct: n > 0 ? Math.round((ayes * 1000) / n) / 10 : null };
      }),
    }));

    const W = 920, H = 290, padL = 48, padR = 24, padT = 22, padB = 34;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const xPos = i => padL + (years.length <= 1 ? plotW / 2 : (i / (years.length - 1)) * plotW);
    const yPos = p => padT + plotH - (p / 100) * plotH;

    let svg = "";
    [0, 25, 50, 75, 100].forEach(v => {
      const y = yPos(v);
      svg += `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" stroke="rgba(148,163,184,0.18)" stroke-dasharray="3,3" />`;
      svg += `<text x="${padL - 8}" y="${y + 4}" text-anchor="end" fill="#94a3b8" font-size="11">${v}%</text>`;
    });
    years.forEach((yr, i) => {
      if (years.length <= 14 || i % 2 === 0 || i === years.length - 1) {
        svg += `<text x="${xPos(i)}" y="${H - 10}" text-anchor="middle" fill="#cbd5e1" font-size="11" font-weight="600">${yr}</text>`;
      }
    });
    series.forEach(s => {
      let d = "";
      s.pts.forEach((p, i) => {
        if (p.pct == null) return;
        d += (d ? " L " : "M ") + `${xPos(i).toFixed(1)} ${yPos(p.pct).toFixed(1)}`;
      });
      if (d) svg += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2.4" />`;
      s.pts.forEach((p, i) => {
        if (p.pct == null) return;
        svg += `<circle cx="${xPos(i).toFixed(1)}" cy="${yPos(p.pct).toFixed(1)}" r="4" fill="${s.color}" stroke="#070b14" stroke-width="1.4"><title>${esc(s.name)} (${p.yr}): ${p.pct}% Aye (${p.ayes}/${p.n})</title></circle>`;
      });
    });

    const leg = series.map(s => `<span style="display:inline-flex;align-items:center;gap:5px;margin-right:12px;font-size:12px;"><span style="width:12px;height:3px;background:${s.color};display:inline-block;"></span>${esc(s.name)}</span>`).join("");
    document.getElementById("boccEvoChart").innerHTML = `
      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
        <strong style="font-size:13.5px;">Commissioner Aye Rate Over Time (${contestedOnly ? "Split Votes Only" : "All Non-Consent Votes"})</strong>
        <div>${leg}</div>
      </div>
      <svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:980px;height:auto;display:block;">${svg}</svg>
    `;
  };

  window.resetBoccArchiveFilters = function () {
    document.getElementById("matSearch").value = "";
    document.getElementById("matCat").value = "";
    document.getElementById("matYear").value = "";
    document.getElementById("matHasFiscal").checked = false;
    document.getElementById("matHasDocs").checked = false;
    ARCHIVE_LIMIT = 40;
    renderBoccArchive();
  };

  window.loadMoreBoccArchive = function () {
    ARCHIVE_LIMIT += 50;
    renderBoccArchive();
  };

  window.renderBoccArchive = function () {
    if (!BOCC) return;
    const q = (document.getElementById("matSearch").value || "").trim().toLowerCase();
    const cat = document.getElementById("matCat").value;
    const yr = document.getElementById("matYear").value;
    const hasFi = document.getElementById("matHasFiscal").checked;
    const hasDocs = document.getElementById("matHasDocs").checked;

    const filtered = (BOCC.matters || []).filter(m => {
      if (cat && m.cat !== cat) return false;
      if (yr && !(m.d || "").startsWith(yr)) return false;
      if (hasFi && !m.fi) return false;
      if (hasDocs && !(m.docs && m.docs.length)) return false;
      if (q) {
        const hay = m._q || (m._q = `${m.f || ""} ${m.t} ${m.cat || ""} ${m.sum || ""} ${m.rec || ""} ${m.fi || ""} ${m.cn || ""} ${(m.docs || []).map(x => x.t).join(" ")}`.toLowerCase());
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    document.getElementById("matArchiveCount").textContent =
      `Showing ${Math.min(filtered.length, ARCHIVE_LIMIT)} of ${filtered.length.toLocaleString()} official Legistar matters`;

    const shown = filtered.slice(0, ARCHIVE_LIMIT);
    document.getElementById("matArchiveList").innerHTML = shown.map(renderMatterCard).join("") ||
      `<div class="res-card" style="color:var(--muted);">No matching BOCC matters.</div>`;

    document.getElementById("matArchiveMore").innerHTML = filtered.length > ARCHIVE_LIMIT
      ? `<button class="nav-btn" onclick="loadMoreBoccArchive()">Load More (${filtered.length - ARCHIVE_LIMIT} remaining)</button>`
      : "";
  };
})();
