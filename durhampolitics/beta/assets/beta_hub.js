/* Hub page controller + $0 client-side Natural-Language Video Clip Search */
let HUB_DATA = null;
let CLIP_DATA = null;
let ACTIVE_TOPIC = "";
let ACTIVE_BOARD = "all";
let SEARCH_Q = "";
let RESULT_TAB = "clips";
let SHOW_MORE_CLIPS = false;

const NL_STOPWORDS = new Set([
  "give", "me", "show", "find", "get", "list", "search", "all", "any", "the", "a", "an",
  "of", "for", "to", "in", "on", "at", "by", "with", "about", "from", "where", "when",
  "who", "what", "which", "that", "this", "these", "those", "is", "are", "was", "were",
  "video", "videos", "clip", "clips", "moment", "moments", "times", "time", "cases", "case",
  "meeting", "meetings", "please", "can", "you", "want", "see", "watch", "and", "or", "his", "her", "their"
]);

const TOPIC_SYNONYMS = [
  {
    cat: "Zoning & Development (SCAD)",
    words: ["development", "developer", "developers", "rezoning", "rezonings", "zoning", "scad", "annexation", "annexations", "land use", "density", "subdivision", "apartments", "townhouse", "townhomes", "udo", "builder", "builders", "sprawl", "comprehensive plan", "site plan", "planning", "growth"]
  },
  {
    cat: "Affordable Housing",
    words: ["affordable housing", "housing", "rent", "renters", "tenant", "tenants", "eviction", "evictions", "homeless", "homelessness", "gentrification", "displacement", "housing bond", "public housing", "dha"]
  },
  {
    cat: "Budget & Taxes",
    words: ["budget", "budgets", "tax", "taxes", "tax rate", "property tax", "bond", "bonds", "funding", "fiscal", "revenue", "appropriations", "revaluation", "capital"]
  },
  {
    cat: "Staff Compensation & Labor",
    words: ["teacher", "teachers", "pay", "salary", "salaries", "raise", "raises", "classified", "staff", "labor", "union", "dae", "step plan", "living wage", "workers", "employee", "employees", "superintendent", "bus driver", "bus drivers"]
  },
  {
    cat: "Community Safety & HEART",
    words: ["police", "dpd", "heart", "safety", "crime", "shotspotter", "surveillance", "flock", "cameras", "sheriff", "jail", "detention", "violence", "gun", "guns", "911", "emergency", "fire"]
  },
  {
    cat: "School Facilities & Closures",
    words: ["school", "schools", "closure", "closures", "facility", "facilities", "campus", "enrollment", "magnet", "charter", "curriculum", "redistricting", "hvac", "construction", "elementary", "middle school", "high school"]
  },
  {
    cat: "Transit & Public Works",
    words: ["transit", "bus", "buses", "light rail", "rail", "sidewalk", "sidewalks", "bike", "bicycle", "road", "roads", "water", "sewer", "stormwater", "parks", "trails", "public works", "street", "streets"]
  },
  {
    cat: "Governance & Transparency",
    words: ["transparency", "ethics", "appointment", "appointments", "vacancy", "board", "charter", "rules", "procedure", "audit", "contract", "contracts", "election", "voting"]
  }
];

const OPPOSE_PATTERNS = [
  /\bobject(?:ing|ed|s|ion|ions)?\b/i,
  /\boppos(?:ing|ed|es|ition|e)?\b/i,
  /\bagainst\b/i,
  /\bdissent(?:ing|ed|s)?\b/i,
  /\bvot(?:e|ed|ing)\s+no\b/i,
  /\bnay(?:s)?\b/i,
  /\bpush(?:ing|ed)?\s+back\b/i,
  /\bcriticiz(?:e|ed|ing)\b/i,
  /\breject(?:ed|ing|s)?\b/i,
  /\bconcern(?:ed|s)?\b/i,
  /\bskeptic(?:al|ism)?\b/i,
  /\bquestion(?:ed|ing)\b/i,
  /\bsplit\s+vote(?:s)?\b/i
];

const SUPPORT_PATTERNS = [
  /\bsupport(?:ing|ed|s)?\b/i,
  /\bfavor(?:ing|ed|s)?\b/i,
  /\bvot(?:e|ed|ing)\s+yes\b/i,
  /\baye(?:s)?\b/i,
  /\bchampion(?:ing|ed|s)?\b/i,
  /\badvocat(?:e|ed|ing)\b/i,
  /\bback(?:ed|ing)\b/i,
  /\bdefend(?:ed|ing|s)?\b/i
];

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function cohesionPill(c) {
  const cls = c.mode === "cohesive" ? "pill-cohesive"
    : c.mode === "consensus" ? "pill-consensus" : "pill-fluid";
  return `<span class="pill ${cls}">${esc(c.label)}</span>`;
}

function extractYouTubeEmbed(url) {
  if (!url) return null;
  const m = url.match(/(?:youtube\.com\/(?:watch\?v=|live\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/);
  if (!m) return null;
  const tm = url.match(/[?&]t=(\d+)/);
  const start = tm ? parseInt(tm[1], 10) : 0;
  return { vid: m[1], start };
}

window.__onBetaAuthUnlocked = async function () {
  const res = await fetch("./data/hub_index.json?t=" + Date.now(), { cache: "no-store" });
  HUB_DATA = await res.json();
  document.getElementById("hubUpdated").textContent = HUB_DATA.generated_at || "";

  renderHubKpis();
  renderTopicChips();
  renderBoards();

  // Load clip_index.json in background right after hub paints
  fetch("./data/clip_index.json?t=" + Date.now(), { cache: "no-store" })
    .then(r => r.json())
    .then(data => {
      CLIP_DATA = data;
      // Precompute lowercase searchable text per clip once
      (CLIP_DATA.clips || []).forEach(cl => {
        cl._hay = `${cl.t} ${cl.s} ${cl.o} ${cl.c} ${cl.mt} ${cl.d} ${(cl.ay || []).join(" ")} ${(cl.ny || []).join(" ")}`.toLowerCase();
        cl._ay = (cl.ay || []).map(x => x.toLowerCase());
        cl._ny = (cl.ny || []).map(x => x.toLowerCase());
        cl._ab = (cl.ab || []).map(x => x.toLowerCase());
      });
      const st = document.getElementById("clipIndexStatus");
      if (st) st.textContent = `${(data.clips_count || 0).toLocaleString()} timestamped video clips indexed`;
      if (SEARCH_Q || ACTIVE_TOPIC) renderSearchResults();
    })
    .catch(() => {
      const st = document.getElementById("clipIndexStatus");
      if (st) st.textContent = "Clip index unavailable";
    });

  const inp = document.getElementById("hubSearchInput");
  inp.addEventListener("input", () => {
    SEARCH_Q = inp.value.trim().toLowerCase();
    SHOW_MORE_CLIPS = false;
    renderSearchAndBoards();
  });
  const sel = document.getElementById("hubBoardFilter");
  sel.addEventListener("change", () => {
    selectHubBoard(sel.value);
  });
};

window.runExampleQuery = function (q) {
  const inp = document.getElementById("hubSearchInput");
  if (inp) inp.value = q;
  SEARCH_Q = q.trim().toLowerCase();
  RESULT_TAB = "clips";
  SHOW_MORE_CLIPS = false;
  renderSearchAndBoards();
  const box = document.getElementById("hubSearchResults");
  if (box) box.scrollIntoView({ behavior: "smooth", block: "nearest" });
};

window.setResultTab = function (tab) {
  RESULT_TAB = tab;
  renderSearchResults();
};

window.showAllMatchedClips = function () {
  SHOW_MORE_CLIPS = !SHOW_MORE_CLIPS;
  renderSearchResults();
};

window.toggleInlineClip = function (btn, vid, startSec) {
  const card = btn.closest(".clip-card");
  if (!card) return;
  const existing = card.querySelector(".clip-embed-wrap");
  if (existing) {
    existing.remove();
    btn.innerHTML = "&#9654; Play Clip Here";
    return;
  }
  const wrap = document.createElement("div");
  wrap.className = "clip-embed-wrap";
  wrap.innerHTML = `<iframe src="https://www.youtube.com/embed/${encodeURIComponent(vid)}?start=${Number(startSec || 0)}&autoplay=1&rel=0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
  card.appendChild(wrap);
  btn.innerHTML = "&#10005; Close Player";
};

function parseNaturalLanguageQuery(rawQ) {
  const q = (rawQ || "").trim().toLowerCase();
  const intent = {
    raw: q,
    members: [],
    stance: "",        // "oppose" | "support" | ""
    topics: [],
    topicKeywords: [],
    years: [],
    boardHint: "",
    freeTerms: []
  };
  if (!q) return intent;

  // 1. Detect stance
  if (OPPOSE_PATTERNS.some(rx => rx.test(q))) {
    intent.stance = "oppose";
  } else if (SUPPORT_PATTERNS.some(rx => rx.test(q))) {
    intent.stance = "support";
  }

  // 2. Detect years (e.g. 2024 or 2022-2025)
  const yrRange = q.match(/\b(20\d{2})\s*[-–to]+\s*(20\d{2})\b/);
  if (yrRange) {
    const a = parseInt(yrRange[1], 10), b = parseInt(yrRange[2], 10);
    for (let y = Math.min(a, b); y <= Math.max(a, b); y++) intent.years.push(String(y));
  } else {
    const yrs = q.match(/\b(20(?:0[6-9]|1\d|2[0-6]))\b/g);
    if (yrs) intent.years = [...new Set(yrs)];
  }

  // 3. Detect board hints
  if (/\b(city council|municipal)\b/i.test(q)) intent.boardHint = "city";
  else if (/\b(bocc|county commissioner|county commissioners)\b/i.test(q)) intent.boardHint = "bocc";
  else if (/\b(dps|school board|board of education)\b/i.test(q)) intent.boardHint = "dps";
  else if (/\bjccpc\b/i.test(q)) intent.boardHint = "jccpc";
  else if (/\bjoint\s+city[- ]county\b/i.test(q)) intent.boardHint = "joint_cc";
  else if (/\bjoint\s+bocc[-– ]boe\b/i.test(q)) intent.boardHint = "joint_bocc_boe";

  // 4. Detect official names (full name first, then unambiguous last name)
  const matchedTokens = new Set();
  const membersList = (CLIP_DATA && CLIP_DATA.members) ? CLIP_DATA.members : [];
  const lastCounts = {};
  membersList.forEach(m => {
    const sh = (m.short || "").toLowerCase();
    if (sh) lastCounts[sh] = (lastCounts[sh] || 0) + 1;
  });
  membersList.forEach(m => {
    const full = (m.name || "").toLowerCase().replace(/^dr\.?\s+/, "").replace(/\([^)]*\)/g, "").trim();
    const sh = (m.short || "").toLowerCase();
    let hit = false;
    if (full && q.includes(full)) {
      hit = true;
      full.split(/\s+/).forEach(w => matchedTokens.add(w));
    } else if (sh && sh.length >= 4 && lastCounts[sh] === 1 && new RegExp("\\b" + sh.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "i").test(q)) {
      hit = true;
      matchedTokens.add(sh);
    } else if ((m.aliases || []).some(al => al.length >= 6 && q.includes(al))) {
      hit = true;
    }
    if (hit && !intent.members.some(x => x.name === m.name)) {
      intent.members.push(m);
    }
  });

  // 5. Detect topics & expand synonyms
  TOPIC_SYNONYMS.forEach(ts => {
    const hits = ts.words.filter(w => new RegExp("\\b" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "i").test(q));
    if (hits.length) {
      intent.topics.push(ts.cat);
      ts.words.slice(0, 10).forEach(w => intent.topicKeywords.push(w));
    }
  });

  // 6. Remaining free keywords (excluding stopwords, member names, stance words, years)
  const stanceStop = new Set(["object", "objecting", "objected", "objection", "objections", "oppose", "opposing", "opposed", "opposition", "against", "dissent", "dissenting", "nay", "nays", "no", "yes", "aye", "ayes", "support", "supporting", "supported", "favor", "favoring", "split", "vote", "votes", "voted", "voting", "question", "questioning", "push", "pushing", "back", "debates", "debate", "city", "council", "bocc", "county", "dps", "board"]);
  q.replace(/[^a-z0-9\s-]/g, " ").split(/\s+/).forEach(w => {
    if (w.length < 3) return;
    if (NL_STOPWORDS.has(w) || matchedTokens.has(w) || stanceStop.has(w) || /^20\d{2}$/.test(w)) return;
    intent.freeTerms.push(w);
  });
  intent.freeTerms = [...new Set(intent.freeTerms)];
  return intent;
}

function memberMatchesList(mem, listLower) {
  const full = (mem.name || "").toLowerCase().replace(/^dr\.?\s+/, "").replace(/\([^)]*\)/g, "").trim();
  const sh = (mem.short || "").toLowerCase();
  return listLower.some(x => x.includes(full) || (sh.length >= 4 && new RegExp("\\b" + sh.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b").test(x)));
}

function searchClipsNL(intent) {
  if (!CLIP_DATA || !CLIP_DATA.clips) return [];
  const effectiveBoard = ACTIVE_BOARD !== "all" ? ACTIVE_BOARD : intent.boardHint;
  const activeTopics = ACTIVE_TOPIC ? [ACTIVE_TOPIC] : intent.topics;
  const scored = [];

  for (const cl of CLIP_DATA.clips) {
    if (effectiveBoard && cl.b !== effectiveBoard) continue;
    if (intent.years.length && !intent.years.includes((cl.d || "").slice(0, 4))) continue;

    let score = 0;
    let stanceMatch = "";

    // Topic filter / boost
    const catMatched = activeTopics.length > 0 && activeTopics.includes(cl.c);
    const synHits = intent.topicKeywords.filter(kw => cl._hay.includes(kw)).length;
    if (ACTIVE_TOPIC && cl.c !== ACTIVE_TOPIC) continue;
    if (activeTopics.length > 0) {
      if (catMatched) score += 28;
      if (synHits > 0) score += Math.min(20, synHits * 6);
      if (!catMatched && synHits === 0) continue;
    }

    // Member + Stance matching
    if (intent.members.length > 0) {
      let anyMemMatched = false;
      for (const mem of intent.members) {
        const inNay = memberMatchesList(mem, cl._ny);
        const inAye = memberMatchesList(mem, cl._ay);
        const inAb = memberMatchesList(mem, cl._ab);
        const inText = cl._hay.includes((mem.short || "").toLowerCase()) || cl._hay.includes((mem.name || "").toLowerCase());

        if (intent.stance === "oppose") {
          if (inNay) {
            score += 60;
            stanceMatch = "oppose";
            anyMemMatched = true;
          } else if (inAb) {
            score += 25;
            stanceMatch = "oppose";
            anyMemMatched = true;
          } else if (cl.k === "debate" && inText) {
            score += 18;
            anyMemMatched = true;
          }
        } else if (intent.stance === "support") {
          if (inAye) {
            score += 45;
            stanceMatch = "support";
            anyMemMatched = true;
          } else if (inText) {
            score += 15;
            anyMemMatched = true;
          }
        } else {
          if (inNay) { score += 38; stanceMatch = "oppose"; anyMemMatched = true; }
          else if (inAye) { score += 30; stanceMatch = "support"; anyMemMatched = true; }
          else if (inText) { score += 22; anyMemMatched = true; }
        }
      }
      if (!anyMemMatched) continue;
    } else if (intent.stance === "oppose") {
      // No specific member, user asked for split votes / objections in general
      if (cl.k === "split_vote" || cl.k === "debate" || cl._ny.length > 0) {
        score += 30;
        stanceMatch = "oppose";
      } else {
        continue;
      }
    }

    // Free keyword matching (BM25-style title boost + body match)
    if (intent.freeTerms.length > 0) {
      const titleLow = (cl.t || "").toLowerCase();
      let termHits = 0;
      for (const ft of intent.freeTerms) {
        if (titleLow.includes(ft)) { score += 16; termHits++; }
        else if (cl._hay.includes(ft)) { score += 9; termHits++; }
      }
      // Require at least one free term hit unless topic + member already gave a strong structural match
      if (termHits === 0 && score < 55) continue;
    }

    if (score <= 0) continue;
    // Prefer timestamped clips and debates/split votes
    if (cl.ts) score += 8;
    if (cl.k === "debate") score += 7;
    else if (cl.k === "split_vote") score += 6;

    scored.push({ cl, score, stanceMatch });
  }

  scored.sort((a, b) => (b.score - a.score) || (b.cl.d > a.cl.d ? 1 : -1));
  return scored;
}

window.selectHubBoard = function (boardId) {
  ACTIVE_BOARD = boardId;
  const sel = document.getElementById("hubBoardFilter");
  if (sel) sel.value = boardId;
  document.querySelectorAll("#hubBoardTabs .tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-board") === boardId);
  });
  renderSearchAndBoards();
};

function renderHubKpis() {
  const t = HUB_DATA.totals || {};
  document.getElementById("hubKpis").innerHTML = `
    <div class="kpi"><div class="kpi-lbl">Board-Terms Ready</div><div class="kpi-val" style="color:#38bdf8;">${t.terms_ready}</div><div class="kpi-sub">Dedicated deep-dive pages</div></div>
    <div class="kpi"><div class="kpi-lbl">Meetings Analyzed</div><div class="kpi-val" style="color:#6ee7b7;">${(t.meetings || 0).toLocaleString()}</div><div class="kpi-sub">${esc(HUB_DATA.coverage)}</div></div>
    <div class="kpi"><div class="kpi-lbl">Executive Summary PDFs</div><div class="kpi-val" style="color:#fca5a5;">${(t.pdfs || 0).toLocaleString()}</div><div class="kpi-sub">Direct hyperlinked reports</div></div>
    <div class="kpi"><div class="kpi-lbl">Searchable Video Clips</div><div class="kpi-val" style="color:#fcd34d;">${(t.clips || 0).toLocaleString()}</div><div class="kpi-sub">${(t.split_votes || 0).toLocaleString()} split votes tracked</div></div>
    <div class="kpi"><div class="kpi-lbl">Major Conflicts</div><div class="kpi-val" style="color:#c4b5fd;">${(t.conflicts || 0).toLocaleString()}</div><div class="kpi-sub">Debates &amp; contested votes</div></div>
  `;
}

function renderTopicChips() {
  const wrap = document.getElementById("hubTopicChips");
  wrap.innerHTML = (HUB_DATA.topics || []).map(t => `
    <button class="topic-chip ${ACTIVE_TOPIC === t.label ? "active" : ""}" onclick="toggleHubTopic('${esc(t.label)}')">
      <span class="topic-dot" style="background:${esc(t.color)};"></span>
      <span>${esc(t.label)}</span>
      <span style="color:var(--dim);font-size:11px;">(${t.meetings_count})</span>
    </button>
  `).join("");
}

window.toggleHubTopic = function (label) {
  ACTIVE_TOPIC = (ACTIVE_TOPIC === label) ? "" : label;
  SHOW_MORE_CLIPS = false;
  renderTopicChips();
  renderSearchAndBoards();
};

window.clearHubSearch = function () {
  ACTIVE_TOPIC = "";
  ACTIVE_BOARD = "all";
  SEARCH_Q = "";
  SHOW_MORE_CLIPS = false;
  document.getElementById("hubSearchInput").value = "";
  document.getElementById("hubBoardFilter").value = "all";
  document.querySelectorAll("#hubBoardTabs .tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-board") === "all");
  });
  renderTopicChips();
  renderSearchAndBoards();
};

function renderSearchAndBoards() {
  const hasFilter = Boolean(ACTIVE_TOPIC || SEARCH_Q || ACTIVE_BOARD !== "all");
  document.getElementById("hubClearBtn").style.display = hasFilter ? "inline-block" : "none";
  renderSearchResults();
  renderBoards();
}

function renderSearchResults() {
  const box = document.getElementById("hubSearchResults");
  if (!ACTIVE_TOPIC && !SEARCH_Q) {
    box.style.display = "none";
    box.innerHTML = "";
    return;
  }
  box.style.display = "block";

  const intent = parseNaturalLanguageQuery(SEARCH_Q);
  const clipHits = searchClipsNL(intent);
  const effBoard = ACTIVE_BOARD !== "all" ? ACTIVE_BOARD : intent.boardHint;
  const kwTokens = intent.freeTerms.length ? intent.freeTerms : (SEARCH_Q ? [SEARCH_Q] : []);

  const matchConflict = c => {
    if (effBoard && c.body_id !== effBoard) return false;
    if (ACTIVE_TOPIC && c.category !== ACTIVE_TOPIC) return false;
    if (intent.topics.length && !ACTIVE_TOPIC && !intent.topics.includes(c.category)) return false;
    if (intent.members.length && !intent.members.some(m => c.q.includes((m.short || "").toLowerCase()))) return false;
    if (kwTokens.length && !kwTokens.some(t => c.q.includes(t)) && !intent.members.length && !intent.topics.length) return false;
    return true;
  };
  const matchMtg = m => {
    if (effBoard && m.body_id !== effBoard) return false;
    if (ACTIVE_TOPIC && !(m.topics || []).includes(ACTIVE_TOPIC)) return false;
    if (intent.topics.length && !ACTIVE_TOPIC && !intent.topics.some(tp => (m.topics || []).includes(tp))) return false;
    if (intent.members.length && !intent.members.some(mem => m.q.includes((mem.short || "").toLowerCase()))) return false;
    if (kwTokens.length && !kwTokens.some(t => m.q.includes(t)) && !intent.members.length && !intent.topics.length) return false;
    return true;
  };

  const cHits = (HUB_DATA.search_conflicts || []).filter(matchConflict);
  const mHits = (HUB_DATA.search_meetings || []).filter(matchMtg);

  const qs = new URLSearchParams();
  if (ACTIVE_TOPIC) qs.set("topic", ACTIVE_TOPIC);
  if (SEARCH_Q) qs.set("q", SEARCH_Q);
  const qSuffix = qs.toString() ? "?" + qs.toString() : "";

  // Build Understood Query pill bar
  const pills = [];
  intent.members.forEach(m => pills.push(`<span class="nl-pill mem">Official: ${esc(m.name)}</span>`));
  if (intent.stance === "oppose") pills.push(`<span class="nl-pill opp">Stance: Objecting / Nay / Dissent</span>`);
  else if (intent.stance === "support") pills.push(`<span class="nl-pill sup">Stance: Supporting / Aye</span>`);
  (ACTIVE_TOPIC ? [ACTIVE_TOPIC] : intent.topics).forEach(tp => pills.push(`<span class="nl-pill top">Topic: ${esc(tp)}</span>`));
  if (intent.years.length) pills.push(`<span class="nl-pill yr">Year: ${esc(intent.years.join(", "))}</span>`);
  if (intent.freeTerms.length) pills.push(`<span class="nl-pill" style="background:var(--surface);border:1px solid var(--border);color:#cbd5e1;">Keywords: ${esc(intent.freeTerms.join(", "))}</span>`);

  const understoodHtml = pills.length
    ? `<div class="nl-understood"><strong style="color:#fff;">Understood:</strong> ${pills.join("")}</div>`
    : "";

  const tabsHtml = `
    <div class="tab-bar" style="margin-bottom:14px;">
      <button class="tab-btn ${RESULT_TAB === "clips" ? "active" : ""}" onclick="setResultTab('clips')">&#9654; Video Clips (${clipHits.length})</button>
      <button class="tab-btn ${RESULT_TAB === "conflicts" ? "active" : ""}" onclick="setResultTab('conflicts')">Major Conflicts (${cHits.length})</button>
      <button class="tab-btn ${RESULT_TAB === "meetings" ? "active" : ""}" onclick="setResultTab('meetings')">Meetings (${mHits.length})</button>
    </div>
  `;

  let bodyHtml = "";
  if (RESULT_TAB === "clips") {
    const shown = SHOW_MORE_CLIPS ? clipHits.slice(0, 60) : clipHits.slice(0, 12);
    const kindLbl = k => k === "debate" ? "Policy Debate" : k === "split_vote" ? "Split Vote" : k === "vote" ? "Vote" : "Agenda Clip";
    const boardShortMap = {};
    const cohortLblMap = {};
    (HUB_DATA.boards || []).forEach(bd => {
      boardShortMap[bd.id] = bd.short_name || bd.name;
      (bd.terms || []).forEach(tm => { cohortLblMap[tm.id] = tm.short_label || tm.label; });
    });
    const cardsHtml = shown.map(({ cl, stanceMatch }) => {
      const yt = extractYouTubeEmbed(cl.u);
      const isGranicus = (cl.u || "").toLowerCase().includes("granicus.com");
      const isPdfSrc = (cl.u || "").toLowerCase().includes(".pdf") || (cl.u || "").toLowerCase().includes("thrillshare.com");
      const bs = cl.bs || boardShortMap[cl.b] || cl.b;
      const clbl = cl.cl || cohortLblMap[cl.cid] || cl.cid;
      const termHref = cl.th || `./terms/${encodeURIComponent(cl.cid)}.html`;
      const pdfUrl = cl.p || (cl.hp && cl.mid ? `../summaries/${encodeURIComponent(cl.mid)}.pdf` : "");
      const openLabel = isPdfSrc ? "&#128196; Official Minutes PDF"
        : (cl.ts ? `&#9654; Open ${isGranicus ? "Granicus" : "Video"} @ ${esc(cl.ts)}` : `&#9654; Open ${isGranicus ? "Granicus" : "Video"}`);
      const sidesHtml = ((cl.ay && cl.ay.length) || (cl.ny && cl.ny.length)) ? `
        <div class="clip-sides">
          ${cl.ny && cl.ny.length ? `<span class="nl-pill opp">Nays / Side B: ${esc(cl.ny.join(", "))}</span>` : ""}
          ${cl.ay && cl.ay.length ? `<span class="nl-pill sup">Ayes / Side A: ${esc(cl.ay.slice(0, 6).join(", "))}${cl.ay.length > 6 ? " +" + (cl.ay.length - 6) : ""}</span>` : ""}
        </div>
      ` : "";
      return `
        <div class="clip-card ${stanceMatch === "oppose" ? "hit-opp" : stanceMatch === "support" ? "hit-sup" : ""}">
          <div>
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
              <div class="sr-title">${esc(cl.t)}</div>
              <span class="pill pill-cat" style="flex-shrink:0;">${esc(kindLbl(cl.k))}</span>
            </div>
            <div class="sr-meta">${esc(cl.d)} &bull; ${esc(bs)} (${esc(clbl)}) &bull; ${esc(cl.c)}${cl.o ? " &bull; <strong>" + esc(cl.o) + "</strong>" : ""}</div>
            ${cl.s ? `<div style="font-size:12px;color:#cbd5e1;margin-top:6px;">${esc(cl.s)}</div>` : ""}
            ${sidesHtml}
          </div>
          <div class="sr-actions">
            ${yt ? `<button class="play-inline-btn" onclick="toggleInlineClip(this, '${esc(yt.vid)}', ${yt.start})">&#9654; Play Clip Here${cl.ts ? " @" + esc(cl.ts) : ""}</button>` : ""}
            ${cl.u ? `<a class="vid-btn sm" href="${esc(cl.u)}" target="_blank" rel="noopener">${openLabel}</a>` : ""}
            ${pdfUrl ? `<a class="pdf-btn sm" href="${esc(pdfUrl)}" target="_blank" rel="noopener">&#128196; Summary PDF</a>` : ""}
            <a class="nav-link" style="font-size:11.5px;padding:4px 8px;" href="${esc(termHref + qSuffix)}">Term Page &rarr;</a>
          </div>
        </div>
      `;
    }).join("") || `<div class="empty-msg">${CLIP_DATA ? "No matching video clips found. Try broadening the name or topic." : "Loading video clip index..."}</div>`;

    const moreBtn = clipHits.length > 12
      ? `<div style="text-align:center;margin-top:12px;"><button class="nav-btn" onclick="showAllMatchedClips()">${SHOW_MORE_CLIPS ? "Show Fewer Clips" : `Show More Clips (${Math.min(60, clipHits.length)} of ${clipHits.length})`}</button></div>`
      : "";
    bodyHtml = `<div class="clips-grid">${cardsHtml}</div>${moreBtn}`;
  } else if (RESULT_TAB === "conflicts") {
    bodyHtml = cHits.slice(0, 16).map(c => `
      <div class="sr-item">
        <div class="sr-title">${esc(c.issue)}</div>
        <div class="sr-meta">${esc(c.body_short)} &bull; ${esc(c.cohort_label)} &bull; ${esc(c.date)} &bull; <strong>${esc(c.resolution || c.category)}</strong></div>
        <div style="font-size:12px;color:#cbd5e1;margin-top:5px;">${esc(c.summary)}</div>
        <div class="sr-actions">
          <a class="vid-btn sm" href="${esc(c.term_href + qSuffix)}#conflicts">Open Term Page &rarr;</a>
          ${c.pdf_url ? `<a class="pdf-btn sm" href="${esc(c.pdf_url)}" target="_blank" rel="noopener">&#128196; Executive Summary PDF</a>` : ""}
        </div>
      </div>
    `).join("") || `<div class="empty-msg">No matching conflicts.</div>`;
  } else {
    bodyHtml = mHits.slice(0, 16).map(m => `
      <div class="sr-item">
        <div class="sr-title">${esc(m.date)} &mdash; ${esc(m.title)}</div>
        <div class="sr-meta">${esc(m.body_short)} &bull; ${esc(m.cohort_label)} &bull; ${m.votes_count} votes (${m.split_votes_count} split)</div>
        <div style="font-size:12px;color:#cbd5e1;margin-top:5px;">${esc(m.summary)}</div>
        <div class="sr-actions">
          <a class="vid-btn sm" href="${esc(m.term_href + qSuffix)}#meetings">View in Term Table &rarr;</a>
          ${m.pdf_url ? `<a class="pdf-btn sm" href="${esc(m.pdf_url)}" target="_blank" rel="noopener">&#128196; Executive Summary PDF</a>` : ""}
        </div>
      </div>
    `).join("") || `<div class="empty-msg">No matching meetings.</div>`;
  }

  box.innerHTML = `${understoodHtml}${tabsHtml}${bodyHtml}`;
}

function renderBoards() {
  const container = document.getElementById("boardsContainer");
  const qs = new URLSearchParams();
  if (ACTIVE_TOPIC) qs.set("topic", ACTIVE_TOPIC);
  if (SEARCH_Q) qs.set("q", SEARCH_Q);
  const qSuffix = qs.toString() ? "?" + qs.toString() : "";

  const boards = (HUB_DATA.boards || []).filter(b => ACTIVE_BOARD === "all" || b.id === ACTIVE_BOARD);
  container.innerHTML = boards.map(b => {
    const terms = (b.terms || []).filter(t => {
      if (ACTIVE_TOPIC && !(t.topics || []).includes(ACTIVE_TOPIC)) return false;
      return true;
    });
    const cardsHtml = terms.map(t => {
      const k = t.kpis || {};
      const themesHtml = (t.top_themes || []).map(th => {
        const meta = th.split_votes_count
          ? `${th.split_votes_count} split${th.split_votes_count === 1 ? "" : "s"}`
          : `${th.conflicts_count} debate${th.conflicts_count === 1 ? "" : "s"}`;
        return `<span class="pill pill-cat"><span class="topic-dot" style="background:${esc(th.color)};"></span>${esc(th.topic)} <span style="color:var(--muted);">(${meta})</span></span>`;
      }).join("");
      const isJoint = b.id === "jccpc" || b.id === "joint_cc" || b.id === "joint_bocc_boe";
      const covHtml = t.coverage_note
        ? `<div style="margin-top:8px;font-size:11.5px;color:#fcd34d;background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:7px;padding:5px 8px;">Archive note: ${esc(t.coverage_note)}</div>`
        : "";
      return `
        <a class="term-card" href="${esc(t.href + qSuffix)}">
          <div>
            <div class="term-card-top">
              <div>
                <div class="term-title">${esc(t.label)}</div>
                <div class="term-dates">${esc(t.date_range_label)}${!isJoint && t.transition_reason ? " &bull; " + esc(t.transition_reason) : ""}</div>
              </div>
              <div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px;">
                ${t.is_current && !isJoint ? `<span class="pill pill-current">Current Term</span>` : ""}
                ${cohesionPill(t.cohesion)}
              </div>
            </div>
            ${!isJoint ? `<div class="term-roster"><strong>Seated:</strong> ${esc((t.roster_names || []).join(", ") || "See term page")}</div>` : ""}
            ${covHtml}
            <div class="term-stats-row">
              <div class="tstat"><b>${k.meetings_count || 0}</b><span>Meetings</span></div>
              <div class="tstat"><b style="color:#fca5a5;">${k.pdfs_count || 0}</b><span>PDFs</span></div>
              <div class="tstat"><b style="color:#fcd34d;">${k.split_votes_count || 0}</b><span>Splits</span></div>
              <div class="tstat"><b style="color:#c4b5fd;">${k.conflicts_count || 0}</b><span>Conflicts</span></div>
            </div>
            ${themesHtml ? `<div style="font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--dim);margin-top:12px;">Primary Areas of Disagreement</div><div class="term-themes" style="margin-top:6px;">${themesHtml}</div>` : ""}
          </div>
          <div class="term-card-cta">
            <span>${isJoint ? "Open " + esc(t.short_label) + " Meetings, Conflicts &amp; Summaries" : "Open Term Conflicts, Voting Blocs &amp; Meetings"}</span>
            <span>&rarr;</span>
          </div>
        </a>
      `;
    }).join("") || `<div class="empty-msg">No terms match the active topic filter for this board.</div>`;

    const isJointBoard = b.id === "jccpc" || b.id === "joint_cc" || b.id === "joint_bocc_boe";
    const yearTabsStrip = isJointBoard
      ? `<div class="term-switcher" style="margin-bottom:14px;">${terms.map(t => `<a class="tsw-pill" href="${esc(t.href + qSuffix)}"><strong>${esc(t.short_label)}</strong> <span style="color:var(--dim);">(${(t.kpis || {}).meetings_count || 0}m)</span></a>`).join("")}</div>`
      : "";
    const pendingNote = (!isJointBoard && b.pending_terms_count > 0)
      ? ` &bull; ${b.pending_terms_count} pre-YouTube term(s) have no recordings`
      : "";

    return `
      <section class="board-section">
        <div class="board-sec-hdr">
          <div class="board-sec-title">
            <span class="board-stripe" style="background:${esc(b.badge_color)};"></span>
            <span>${esc(b.name)}</span>
          </div>
          <div class="board-sec-meta">${b.terms.length} ${isJointBoard ? "year(s)" : "term(s)"} &bull; ${esc(b.regular_schedule)}${pendingNote}</div>
        </div>
        ${yearTabsStrip}
        <div class="terms-grid">${cardsHtml}</div>
      </section>
    `;
  }).join("");
}
