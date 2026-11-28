/* DPS Board of Education Natural-Language Search & Decision Explorer */
(function () {
  let BOE = null;
  let ACTIVE_TAB = "search";
  let ACTIVE_STREAM = "all";
  let SEARCH_LIMIT = 35;
  let ARCHIVE_LIMIT = 40;
  let SELECTED_EVO = new Set();

  const PALETTE = ["#38bdf8", "#10b981", "#f59e0b", "#f472b6", "#a78bfa", "#fb7185", "#34d399", "#facc15"];
  const RECENT_BOARD = ["Joy Harrell-Goff", "Xavier Cason", "Millicent Rogers", "Wendell Tabb", "Bettina Umstead", "Natalie Beyer", "Emily Chávez", "Jessica Carda-Auten"];

  const STOPWORDS = new Set([
    "give","me","show","find","get","list","search","all","any","the","a","an","of","for","to","in","on","at","by","with",
    "about","from","where","when","who","what","which","that","this","these","those","is","are","was","were","and","or",
    "board","education","boe","dps","meeting","meetings","document","documents","docs","file","files","decision","decisions"
  ]);

  const DOMAIN_SYNONYMS = [
    { cat: "Staff Compensation & Labor", words: ["pay","salary","salaries","raise","raises","classified","dae","union","step","supplement","bonus","bus driver","drivers","cafeteria","custodial","teacher","teachers","compensation","overtime","payroll","hr","personnel","hiring","retention","staff"] },
    { cat: "Budget & Taxes", words: ["budget","amendment","funding","county","commissioners","fund balance","fiscal","audit","appropriation","tax","deficit","shortfall","finance","financial","cost","million","grant","title i","esser","lottery"] },
    { cat: "School Facilities & Closures", words: ["consolidation","rightsizing","closure","close","closing","mgt","facility","facilities","bond","construction","hvac","roof","campus","building","renovation","elementary","middle","high school","redistricting","enrollment","capacity","northern","lyons farm","murray-massenburg"] },
    { cat: "Community Safety & HEART", words: ["safety","sro","police","discipline","suspension","suspensions","4301","weapon","weapons","security","camera","cameras","bullying","mental health","crisis","lockdown","student code"] },
    { cat: "Governance & Transparency", words: ["policy","superintendent","mubenga","lewis","contract","bylaws","calendar","appointment","vacancy","minutes","agenda","closed session","attorney","governance","equity","audit","rfp","vendor"] },
    { cat: "Academics & Equity", words: ["magnet","ignite","lottery","advanced academics","aig","literacy","sipps","curriculum","school improvement","sip","reading","math","ec","special education","multilingual","esl","graduation","testing","achievement","pre-k"] },
    { cat: "Transit & Public Works", words: ["bus","buses","transportation","route","routes","bell schedule","walk zone","express","driver"] },
  ];

  const OPPOSE_RE = /\b(oppos\w*|object\w*|dissent\w*|against|nay|nays|vote\w*\s+no|reject\w*|split|concern\w*)\b/i;
  const SUPPORT_RE = /\b(support\w*|favor\w*|aye|ayes|vote\w*\s+yes|approv\w*)\b/i;

  const TOPIC_COLS = [
    { key: "all", label: "Overall" },
    { key: "Staff Compensation & Labor", label: "Staff Pay & Labor" },
    { key: "Budget & Taxes", label: "Budget & Finance" },
    { key: "School Facilities & Closures", label: "Facilities & Closures" },
    { key: "Community Safety & HEART", label: "Safety & Discipline" },
    { key: "Governance & Transparency", label: "Policy & Governance" },
  ];

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function pctStyle(pct, n) {
    if (pct == null || !n) return "background:#0a101d;color:#475569;";
    if (pct >= 90) return "background:rgba(16,185,129,0.28);color:#6ee7b7;";
    if (pct >= 75) return "background:rgba(56,189,248,0.22);color:#bae6fd;";
    if (pct >= 55) return "background:rgba(245,158,11,0.24);color:#fde68a;";
    return "background:rgba(239,68,68,0.30);color:#fca5a5;";
  }

  window.__onBetaAuthUnlocked = async function () {
    try {
      const resp = await fetch("./data/boe_intelligence.json", { cache: "no-store" });
      BOE = await resp.json();
      initFilters();
      renderKpis();
      selectBoeCurrent();
      runBoeNlSearch();
      renderBoeMembers();
      renderBoeDocsArchive();
    } catch (e) {
      document.getElementById("boeSearchResults").innerHTML =
        `<div class="res-card" style="color:#fca5a5;">Failed to load DPS BoE intelligence index: ${esc(e.message)}</div>`;
    }
  };

  function initFilters() {
    const yrs = new Set();
    (BOE.docs || []).forEach(d => { if (d.d) yrs.add(d.d.slice(0, 4)); });
    (BOE.votes || []).forEach(v => { if (v.d) yrs.add(v.d.slice(0, 4)); });
    const sortedYrs = Array.from(yrs).filter(y => /^20\d\d$/.test(y)).sort((a, b) => b.localeCompare(a));
    ["boeNlYear", "docYear"].forEach(id => {
      const sel = document.getElementById(id);
      sortedYrs.forEach(y => {
        const o = document.createElement("option");
        o.value = y; o.textContent = y;
        sel.appendChild(o);
      });
    });
  }

  function renderKpis() {
    const s = BOE.summary || {};
    document.getElementById("boeKpis").innerHTML = `
      <div class="kpi"><div class="kpi-lbl">BoE Meetings w/ Docs</div><div class="kpi-val" style="color:#93c5fd;">${s.diligent_meetings || 0}</div><div class="kpi-sub">${esc(s.diligent_range || "2013–2026")}</div></div>
      <div class="kpi"><div class="kpi-lbl">Official Docs Indexed</div><div class="kpi-val" style="color:#6ee7b7;">${(s.docs_total || 0).toLocaleString()}</div><div class="kpi-sub">${(s.docs_text_extracted || 0).toLocaleString()} full-text parsed</div></div>
      <div class="kpi"><div class="kpi-lbl">Precis &amp; Memos</div><div class="kpi-val" style="color:#fcd34d;">${(s.precis_count || 0).toLocaleString()}</div><div class="kpi-sub">${(s.fiscal_docs_count || 0).toLocaleString()} with fiscal impact $</div></div>
      <div class="kpi"><div class="kpi-lbl">Board Votes Tracked</div><div class="kpi-val" style="color:#c4b5fd;">${(s.votes_total || 0).toLocaleString()}</div><div class="kpi-sub">${s.split_votes_total || 0} split / contested votes</div></div>
      <div class="kpi"><div class="kpi-lbl">Recorded Debates</div><div class="kpi-val" style="color:#fca5a5;">${s.debates_total || 0}</div><div class="kpi-sub">Across ${s.db_meetings || 0} BoE meetings</div></div>
    `;
  }

  window.setBoeTab = function (tab) {
    ACTIVE_TAB = tab;
    document.querySelectorAll(".boe-tab").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
    document.querySelectorAll(".boe-panel").forEach(p => p.classList.toggle("active", p.id === "panel-" + tab));
    if (tab === "members") renderBoeMembers();
    if (tab === "docs") renderBoeDocsArchive();
  };

  window.setBoeStream = function (st) {
    ACTIVE_STREAM = st;
    SEARCH_LIMIT = 35;
    document.querySelectorAll("#boeStreamTabs .stream-btn").forEach(b => b.classList.toggle("active", b.dataset.stream === st));
    runBoeNlSearch();
  };

  window.tryBoeQuery = function (q) {
    document.getElementById("boeNlInput").value = q;
    SEARCH_LIMIT = 35;
    setBoeTab("search");
    runBoeNlSearch();
  };

  window.clearBoeSearch = function () {
    document.getElementById("boeNlInput").value = "";
    document.getElementById("boeNlYear").value = "";
    SEARCH_LIMIT = 35;
    runBoeNlSearch();
  };

  window.loadMoreBoeSearch = function () {
    SEARCH_LIMIT += 40;
    runBoeNlSearch();
  };

  function parseQuery(raw) {
    const q = (raw || "").trim().toLowerCase();
    const years = (q.match(/\b20[12]\d\b/g) || []);
    let stance = "";
    if (OPPOSE_RE.test(q)) stance = "oppose";
    else if (SUPPORT_RE.test(q)) stance = "support";

    const matchedMembers = [];
    const memTokens = new Set();
    (BOE.members || []).forEach(m => {
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

  window.runBoeNlSearch = function () {
    if (!BOE) return;
    const raw = document.getElementById("boeNlInput").value || "";
    const yrSel = document.getElementById("boeNlYear").value;
    const intent = parseQuery(raw);
    if (yrSel && !intent.years.includes(yrSel)) intent.years.push(yrSel);

    const hasQuery = Boolean(intent.q || yrSel);
    const badgeParts = [];
    if (intent.members.length) badgeParts.push(`Members: <strong>${esc(intent.members.join(", "))}</strong>`);
    if (intent.stance) badgeParts.push(`Stance: <strong>${esc(intent.stance)}</strong>`);
    if (intent.topics.length) badgeParts.push(`Topics: <strong>${esc(intent.topics.join(", "))}</strong>`);
    if (intent.years.length) badgeParts.push(`Year: <strong>${esc(intent.years.join(", "))}</strong>`);
    if (intent.terms.length) badgeParts.push(`Keywords: <strong>${esc(intent.terms.join(", "))}</strong>`);
    document.getElementById("boeIntentBadge").innerHTML = hasQuery
      ? (badgeParts.join(" &bull; ") || "Showing recent highlights")
      : "Showing recent DPS split votes, debates, and official Diligent Precis/documents — type any plain-English question above to search all 4,000+ docs & decisions.";

    const results = [];

    // 1. Score Official Docs & Precis
    if (!intent.members.length || !intent.stance) {
      for (const d of (BOE.docs || [])) {
        if (intent.years.length && (!d.d || !intent.years.includes(d.d.slice(0, 4)))) continue;
        let sc = 0;
        if (!hasQuery) {
          if (d.cat === "PRECIS" || d.fi) sc = 20;
          else continue;
        } else {
          const hay = d._q || (d._q = `${d.t} ${d.it || ""} ${d.sum || ""} ${d.fi || ""} ${d.cat || ""}`.toLowerCase());
          const tLow = (d.t || "").toLowerCase();
          let hits = 0;
          for (const term of intent.terms) {
            if (tLow.includes(term)) { sc += 18; hits++; }
            else if (hay.includes(term)) { sc += 9; hits++; }
          }
          for (const mn of intent.members) {
            const last = mn.toLowerCase().split(/\s+/).pop();
            if (hay.includes(last)) { sc += 15; hits++; }
          }
          if (intent.terms.length && hits === 0) continue;
          if (!intent.terms.length && intent.topics.length) {
            const sh = intent.synWords.filter(w => hay.includes(w)).length;
            if (!sh) continue;
            sc += sh * 10;
          }
          if (d.cat === "PRECIS") sc += 6;
          if (d.fi) sc += 4;
          if (sc <= 0 && !yrSel) continue;
          if (yrSel && !intent.q) sc = 10;
        }
        results.push({ kind: "docs", score: sc, date: d.d || "", item: d });
      }
    }

    // 2. Score Board Votes
    for (const v of (BOE.votes || [])) {
      if (intent.years.length && (!v.d || !intent.years.includes(v.d.slice(0, 4)))) continue;
      let sc = 0;
      if (!hasQuery) {
        if (!v.sp) continue;
        sc = 25;
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
    for (const db of (BOE.debates || [])) {
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

    // Update stream tab counts
    const counts = { all: results.length, docs: 0, votes: 0, debates: 0 };
    results.forEach(r => counts[r.kind]++);
    document.querySelectorAll("#boeStreamTabs .stream-btn").forEach(b => {
      const k = b.dataset.stream;
      const lbl = k === "all" ? "All Results" : k === "docs" ? "Official Docs & Precis" : k === "votes" ? "Board Votes & Splits" : "Recorded Debates";
      b.textContent = `${lbl} (${counts[k]})`;
    });

    const filtered = ACTIVE_STREAM === "all" ? results : results.filter(r => r.kind === ACTIVE_STREAM);
    filtered.sort((a, b) => (b.score - a.score) || b.date.localeCompare(a.date));

    const shown = filtered.slice(0, SEARCH_LIMIT);
    const outEl = document.getElementById("boeSearchResults");
    if (!shown.length) {
      outEl.innerHTML = `<div class="res-card" style="color:var(--muted);">No matching DPS documents, votes, or debates found. Try broader keywords.</div>`;
      document.getElementById("boeSearchMore").innerHTML = "";
      return;
    }

    outEl.innerHTML = shown.map(r => {
      const x = r.item;
      if (r.kind === "docs") {
        return `
          <article class="res-card">
            <div class="res-top">
              <div>
                <div class="res-title">${esc(x.it || x.t)}</div>
                <div class="res-meta">${esc(x.d || "Undated")} &bull; ${esc(x.t)}</div>
              </div>
              <div>
                <span class="b-pill green">${esc(x.cat || "DOC")}</span>
                ${x.fi ? `<span class="b-pill warn">Fiscal: ${esc(x.fi)}</span>` : ""}
              </div>
            </div>
            ${x.sum ? `<div class="res-body">${esc(x.sum)}</div>` : ""}
            <div class="doc-links-row">
              <a class="doc-btn" style="border-color:var(--dps);color:#93c5fd;" href="${esc(x.u)}" target="_blank" rel="noopener">&#128206; Open Official Document</a>
              ${x.mu ? `<a class="doc-btn" href="${esc(x.mu)}" target="_blank" rel="noopener">&#128197; Official Meeting Page</a>` : ""}
              ${x.pdf ? `<a class="doc-btn" style="border-color:#dc2626;color:#fca5a5;" href="${esc(x.pdf)}" target="_blank" rel="noopener">&#128196; Meeting Executive Summary PDF</a>` : ""}
            </div>
          </article>
        `;
      }
      if (r.kind === "votes") {
        return `
          <article class="res-card">
            <div class="res-top">
              <div>
                <div class="res-title">${esc(x.t)}</div>
                <div class="res-meta">${esc(x.d)} &bull; ${esc(x.mt || "DPS Board Meeting")}</div>
              </div>
              <div>
                <span class="b-pill ${x.sp ? "warn" : "green"}">${esc(x.o)} (${esc(x.tl)})</span>
                <span class="b-pill">${esc(x.c)}</span>
              </div>
            </div>
            ${x.sp && (x.ay || []).length ? `<div style="font-size:12px;color:#6ee7b7;margin-top:6px;"><strong>Ayes:</strong> ${esc(x.ay.join(", "))}</div>` : ""}
            ${(x.ny || []).length ? `<div style="font-size:12px;color:#fca5a5;margin-top:3px;"><strong>Nays:</strong> ${esc(x.ny.join(", "))}</div>` : ""}
            ${x.n ? `<div class="res-body">${esc(x.n)}</div>` : ""}
            <div class="doc-links-row">
              ${x.v ? `<a class="doc-btn" style="border-color:#2563eb;color:#93c5fd;" href="${esc(x.v)}" target="_blank" rel="noopener">&#9654; Watch Video${x.ts ? " @" + esc(x.ts) : ""}</a>` : ""}
              ${x.pdf ? `<a class="doc-btn" style="border-color:#dc2626;color:#fca5a5;" href="${esc(x.pdf)}" target="_blank" rel="noopener">&#128196; Executive Summary PDF</a>` : ""}
              ${x.au ? `<a class="doc-btn" href="${esc(x.au)}" target="_blank" rel="noopener">&#128206; Diligent Agenda</a>` : ""}
            </div>
          </article>
        `;
      }
      return `
        <article class="res-card">
          <div class="res-top">
            <div>
              <div class="res-title">${esc(x.t)}</div>
              <div class="res-meta">${esc(x.d)} &bull; ${esc(x.mt || "DPS Board Debate")}</div>
            </div>
            <div>
              <span class="b-pill purple">Debate</span>
              <span class="b-pill">${esc(x.c)}</span>
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
            ${x.au ? `<a class="doc-btn" href="${esc(x.au)}" target="_blank" rel="noopener">&#128206; Diligent Agenda</a>` : ""}
          </div>
        </article>
      `;
    }).join("");

    document.getElementById("boeSearchMore").innerHTML = filtered.length > SEARCH_LIMIT
      ? `<button class="nav-btn" onclick="loadMoreBoeSearch()">Load More (${filtered.length - SEARCH_LIMIT} remaining)</button>`
      : "";
  };

  window.selectBoeCurrent = function () {
    const avail = new Set((BOE.members || []).map(m => m.name));
    SELECTED_EVO = new Set(RECENT_BOARD.filter(n => avail.has(n)).slice(0, 7));
    renderBoeMembers();
  };

  window.selectBoeTop = function (k) {
    SELECTED_EVO = new Set((BOE.members || []).slice(0, k).map(m => m.name));
    renderBoeMembers();
  };

  window.toggleBoeEvo = function (nm) {
    if (SELECTED_EVO.has(nm)) SELECTED_EVO.delete(nm);
    else SELECTED_EVO.add(nm);
    renderBoeMembers();
  };

  window.drillMemberTopic = function (memberName, topicKey) {
    const q = topicKey === "all" ? `${memberName} opposing` : `${memberName} ${topicKey.split(" ")[0].toLowerCase()}`;
    tryBoeQuery(q);
  };

  window.renderBoeMembers = function () {
    if (!BOE) return;
    const contestedOnly = document.getElementById("boeMatContested").checked;
    const votes = (BOE.votes || []).filter(v => !contestedOnly || v.sp);
    const members = (BOE.members || []).filter(m => m.n >= 5);

    const hdr = TOPIC_COLS.map(c => `<th>${esc(c.label)}</th>`).join("");
    const rows = members.map(m => {
      const mVotes = votes.filter(v => (v.mv && v.mv[m.name]));
      const cells = TOPIC_COLS.map(col => {
        const sub = col.key === "all" ? mVotes : mVotes.filter(v => v.c === col.key);
        const n = sub.length;
        const ayes = sub.filter(v => v.mv[m.name] === "AYE").length;
        const pct = n > 0 ? Math.round((ayes * 1000) / n) / 10 : null;
        const txt = n > 0 ? `${pct.toFixed(0)}%<span class="m-sub">${ayes}/${n}</span>` : "·";
        return `<td class="m-cell" style="${pctStyle(pct, n)}" onclick="drillMemberTopic('${esc(m.name)}','${esc(col.key)}')">${txt}</td>`;
      }).join("");
      return `<tr><td>${esc(m.name)} <span style="color:var(--dim);font-weight:500;">(${mVotes.length})</span></td>${cells}</tr>`;
    }).join("");

    document.getElementById("boeMatrixWrap").innerHTML = `
      <table class="matrix-tbl">
        <thead><tr><th>Board Member</th>${hdr}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;

    // Evolution chips + SVG chart
    const colorMap = {};
    let ci = 0;
    members.forEach(m => {
      if (SELECTED_EVO.has(m.name)) { colorMap[m.name] = PALETTE[ci++ % PALETTE.length]; }
    });
    document.getElementById("boeEvoChips").innerHTML = members.map(m => {
      const act = SELECTED_EVO.has(m.name);
      const dot = act ? `<span style="width:9px;height:9px;border-radius:50%;background:${colorMap[m.name]};display:inline-block;"></span>` : "";
      return `<button class="mem-chip ${act ? "active" : ""}" onclick="toggleBoeEvo('${esc(m.name)}')">${dot}${esc(m.name)} (${m.n})</button>`;
    }).join("");

    const selList = members.filter(m => SELECTED_EVO.has(m.name));
    const selNames = selList.map(m => m.name);
    const activeYearsSet = new Set();
    votes.forEach(v => {
      const yr = (v.d || "").slice(0, 4);
      if (!/^20\d\d$/.test(yr) || !v.mv) return;
      if (selNames.some(nm => v.mv[nm])) activeYearsSet.add(yr);
    });
    const years = Array.from(activeYearsSet).sort();

    if (!selList.length || !years.length) {
      document.getElementById("boeEvoChart").innerHTML = `
        <div style="font-size:13px;color:var(--muted);padding:18px 8px;">
          Select one or more board members above to plot their Aye rate over their years on the board.
        </div>
      `;
      return;
    }

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

    const allPcts = [];
    series.forEach(s => s.pts.forEach(p => { if (p.pct != null) allPcts.push(p.pct); }));
    const minPct = allPcts.length ? Math.min(...allPcts) : 85;
    let yMin = contestedOnly ? 0 : 85;
    if (!contestedOnly && minPct < yMin) {
      yMin = Math.max(0, Math.floor((minPct - 1) / 5) * 5);
    }
    const yMax = 100;
    const span = yMax - yMin;
    let yTicks;
    if (yMin === 85) yTicks = [85, 88, 91, 94, 97, 100];
    else if (yMin === 0) yTicks = [0, 25, 50, 75, 100];
    else {
      const step = span <= 25 ? 5 : (span <= 50 ? 10 : 20);
      yTicks = [];
      for (let v = yMin; v <= 100; v += step) yTicks.push(v);
      if (yTicks[yTicks.length - 1] !== 100) yTicks.push(100);
    }

    const W = 880, H = 280, padL = 50, padR = 26, padT = 22, padB = 34;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const xPos = i => padL + (years.length <= 1 ? plotW / 2 : (i / (years.length - 1)) * plotW);
    const yPos = p => padT + plotH - ((Math.max(yMin, Math.min(yMax, p)) - yMin) / span) * plotH;

    let svg = "";
    yTicks.forEach(v => {
      const y = yPos(v);
      svg += `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" stroke="rgba(148,163,184,0.18)" stroke-dasharray="3,3" />`;
      svg += `<text x="${padL - 8}" y="${y + 4}" text-anchor="end" fill="#94a3b8" font-size="11">${v}%</text>`;
    });
    years.forEach((yr, i) => {
      svg += `<text x="${xPos(i)}" y="${H - 10}" text-anchor="middle" fill="#cbd5e1" font-size="11.5" font-weight="600">${yr}</text>`;
    });
    series.forEach(s => {
      let d = "";
      s.pts.forEach((p, i) => {
        if (p.pct == null) return;
        d += (d ? " L " : "M ") + `${xPos(i).toFixed(1)} ${yPos(p.pct).toFixed(1)}`;
      });
      if (d) svg += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2.5" />`;
      s.pts.forEach((p, i) => {
        if (p.pct == null) return;
        svg += `<circle cx="${xPos(i).toFixed(1)}" cy="${yPos(p.pct).toFixed(1)}" r="4.2" fill="${s.color}" stroke="#070b14" stroke-width="1.4"><title>${esc(s.name)} (${p.yr}): ${p.pct}% Aye (${p.ayes}/${p.n})</title></circle>`;
      });
    });

    const yrSpanLbl = years.length === 1 ? years[0] : `${years[0]}–${years[years.length - 1]}`;
    const leg = series.map(s => `<span style="display:inline-flex;align-items:center;gap:5px;margin-right:12px;font-size:12px;"><span style="width:12px;height:3px;background:${s.color};display:inline-block;"></span>${esc(s.name)}</span>`).join("");
    document.getElementById("boeEvoChart").innerHTML = `
      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
        <strong style="font-size:13.5px;">Board Member Aye Rate Over Time (${yrSpanLbl} &bull; ${contestedOnly ? "Split Votes Only" : "All Non-Consent Votes"} &bull; Scale ${yMin}%–100%)</strong>
        <div>${leg}</div>
      </div>
      <svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:960px;height:auto;display:block;">${svg}</svg>
    `;
  };

  window.resetDocArchiveFilters = function () {
    document.getElementById("docSearch").value = "";
    document.getElementById("docCat").value = "";
    document.getElementById("docYear").value = "";
    document.getElementById("docHasFiscal").checked = false;
    ARCHIVE_LIMIT = 40;
    renderBoeDocsArchive();
  };

  window.loadMoreDocsArchive = function () {
    ARCHIVE_LIMIT += 50;
    renderBoeDocsArchive();
  };

  window.renderBoeDocsArchive = function () {
    if (!BOE) return;
    const q = (document.getElementById("docSearch").value || "").trim().toLowerCase();
    const cat = document.getElementById("docCat").value;
    const yr = document.getElementById("docYear").value;
    const hasFi = document.getElementById("docHasFiscal").checked;

    const filtered = (BOE.docs || []).filter(d => {
      if (cat && d.cat !== cat) return false;
      if (yr && !(d.d || "").startsWith(yr)) return false;
      if (hasFi && !d.fi) return false;
      if (q) {
        const hay = d._q || (d._q = `${d.t} ${d.it || ""} ${d.sum || ""} ${d.fi || ""} ${d.cat || ""}`.toLowerCase());
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    document.getElementById("docArchiveCount").textContent =
      `Showing ${Math.min(filtered.length, ARCHIVE_LIMIT)} of ${filtered.length.toLocaleString()} official DPS Board documents (2013–2026)`;

    const shown = filtered.slice(0, ARCHIVE_LIMIT);
    document.getElementById("docArchiveList").innerHTML = shown.map(x => `
      <article class="res-card">
        <div class="res-top">
          <div>
            <div class="res-title">${esc(x.it || x.t)}</div>
            <div class="res-meta">${esc(x.d || "Undated")} &bull; ${esc(x.t)}</div>
          </div>
          <div>
            <span class="b-pill green">${esc(x.cat || "DOC")}</span>
            ${x.fi ? `<span class="b-pill warn">Fiscal: ${esc(x.fi)}</span>` : ""}
          </div>
        </div>
        ${x.sum ? `<div class="res-body">${esc(x.sum)}</div>` : ""}
        <div class="doc-links-row">
          <a class="doc-btn" style="border-color:var(--dps);color:#93c5fd;" href="${esc(x.u)}" target="_blank" rel="noopener">&#128206; Open Official Document</a>
          ${x.mu ? `<a class="doc-btn" href="${esc(x.mu)}" target="_blank" rel="noopener">&#128197; Official Meeting Page</a>` : ""}
          ${x.pdf ? `<a class="doc-btn" style="border-color:#dc2626;color:#fca5a5;" href="${esc(x.pdf)}" target="_blank" rel="noopener">&#128196; Executive Summary PDF</a>` : ""}
        </div>
      </article>
    `).join("") || `<div class="res-card" style="color:var(--muted);">No matching documents.</div>`;

    document.getElementById("docArchiveMore").innerHTML = filtered.length > ARCHIVE_LIMIT
      ? `<button class="nav-btn" onclick="loadMoreDocsArchive()">Load More (${filtered.length - ARCHIVE_LIMIT} remaining)</button>`
      : "";
  };
})();
