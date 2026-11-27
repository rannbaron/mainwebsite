/* Dedicated board-term page controller for /durhampolitics/beta/terms/<cohort_id>.html */
let TERM_DATA = null;
let ACTIVE_TOPIC = "";
let SEARCH_Q = "";
let MTG_FILTER = "all";
let SORT_BY = "date_desc";
let BLOC_TAB = "topics";
let MATRIX_MODE = "split";
let SHOW_ALL_CONFLICTS = false;
const OPEN_DRAWERS = new Set();

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

window.__onBetaAuthUnlocked = async function () {
  const cid = document.body.getAttribute("data-cohort-id");
  const res = await fetch(`../data/term_${encodeURIComponent(cid)}.json?t=` + Date.now(), { cache: "no-store" });
  TERM_DATA = await res.json();

  // Read optional ?topic=...&q=... from Hub navigation
  const params = new URLSearchParams(window.location.search);
  ACTIVE_TOPIC = params.get("topic") || "";
  SEARCH_Q = (params.get("q") || "").trim().toLowerCase();
  if (SEARCH_Q) document.getElementById("termSearchInput").value = params.get("q") || "";

  // Default Voting Blocs tab: Per-Topic when coalitions shift by topic (or when a topic filter is set),
  // Overall when board-term has strongly cohesive blocs.
  BLOC_TAB = (ACTIVE_TOPIC || TERM_DATA.cohesion.mode === "fluid_by_topic") ? "topics" : "overall";

  renderTermSwitcher();
  renderHero();
  renderTopicChips();
  renderAllFilteredSections();

  document.getElementById("termSearchInput").addEventListener("input", e => {
    SEARCH_Q = e.target.value.trim().toLowerCase();
    renderAllFilteredSections();
  });
  document.getElementById("termMtgFilter").addEventListener("change", e => {
    MTG_FILTER = e.target.value;
    renderMeetingsTable();
  });
  document.getElementById("termSortSelect").addEventListener("change", e => {
    SORT_BY = e.target.value;
    renderMeetingsTable();
  });
};

function renderTermSwitcher() {
  const sibs = TERM_DATA.sibling_terms || [];
  const curId = TERM_DATA.cohort.id;
  document.getElementById("termSwitcher").innerHTML = sibs.map(s => `
    <a class="tsw-pill ${s.id === curId ? "active" : ""}" href="${esc(s.href)}">
      ${esc(s.short_label || s.label)} <span style="color:var(--dim);">(${s.meetings_count})</span>
    </a>
  `).join("");
}

function renderHero() {
  const c = TERM_DATA.cohort;
  const k = TERM_DATA.kpis;
  const coh = TERM_DATA.cohesion;
  document.getElementById("heroKicker").innerHTML =
    `${esc(c.body_name)} &bull; ${esc(c.date_range_label)}${c.is_current ? " &bull; Current Term" : ""}`;
  document.getElementById("heroTitle").textContent = c.label;
  const subParts = [];
  if (c.transition_reason) subParts.push(c.transition_reason);
  if (c.coverage_note) subParts.push("Archive coverage: " + c.coverage_note);
  document.getElementById("heroSub").textContent =
    subParts.join(" — ") || `Complete meeting record, conflict highlights, and roll-call coalition analysis for ${c.label}.`;

  document.getElementById("termKpis").innerHTML = `
    <div class="kpi"><div class="kpi-lbl">Meetings</div><div class="kpi-val" style="color:#6ee7b7;">${k.meetings_count}</div><div class="kpi-sub">${esc(k.earliest_meeting)} &rarr; ${esc(k.latest_meeting)}</div></div>
    <div class="kpi"><div class="kpi-lbl">Executive Summary PDFs</div><div class="kpi-val" style="color:#fca5a5;">${k.pdfs_count}</div><div class="kpi-sub">Ready in meetings table</div></div>
    <div class="kpi"><div class="kpi-lbl">Substantive Votes</div><div class="kpi-val" style="color:#38bdf8;">${k.votes_count}</div><div class="kpi-sub">${k.unanimous_pct}% unanimous (excl. consent)</div></div>
    <div class="kpi"><div class="kpi-lbl">Split / Contested Votes</div><div class="kpi-val" style="color:#fcd34d;">${k.split_votes_count}</div><div class="kpi-sub">Cohesion: ${esc(coh.label)}</div></div>
    <div class="kpi"><div class="kpi-lbl">Major Conflicts</div><div class="kpi-val" style="color:#c4b5fd;">${k.conflicts_count}</div><div class="kpi-sub">Debates &amp; split roll calls</div></div>
  `;

  document.getElementById("termRoster").innerHTML = (TERM_DATA.roster || []).map(r => {
    const st = r.stats || {};
    return `
      <div class="roster-chip">
        <div class="roster-name">${esc(r.name)}</div>
        <div class="roster-role">${esc(r.role)}${r.district ? " &bull; " + esc(r.district) : ""}</div>
        <div class="roster-stat">${st.votes_cast || 0} votes &bull; ${st.nays || 0} nays &bull; ${st.dissent_rate || 0}% dissent</div>
      </div>
    `;
  }).join("");
}

function renderTopicChips() {
  const wrap = document.getElementById("termTopicChips");
  wrap.innerHTML = (TERM_DATA.topics || []).map(t => `
    <button class="topic-chip ${ACTIVE_TOPIC === t.label ? "active" : ""}" onclick="toggleTermTopic('${esc(t.label)}')">
      <span class="topic-dot" style="background:${esc(t.color)};"></span>
      <span>${esc(t.label)}</span>
      <span style="color:var(--dim);font-size:11px;">(${t.meetings_count}m${t.split_votes_count ? ", " + t.split_votes_count + " split" : ""})</span>
    </button>
  `).join("");
}

window.toggleTermTopic = function (label) {
  ACTIVE_TOPIC = (ACTIVE_TOPIC === label) ? "" : label;
  if (ACTIVE_TOPIC) BLOC_TAB = "topics";
  renderTopicChips();
  renderAllFilteredSections();
};

window.clearTermFilters = function () {
  ACTIVE_TOPIC = "";
  SEARCH_Q = "";
  MTG_FILTER = "all";
  SORT_BY = "date_desc";
  document.getElementById("termSearchInput").value = "";
  document.getElementById("termMtgFilter").value = "all";
  document.getElementById("termSortSelect").value = "date_desc";
  renderTopicChips();
  renderAllFilteredSections();
};

function renderAllFilteredSections() {
  const hasFilter = Boolean(ACTIVE_TOPIC || SEARCH_Q || MTG_FILTER !== "all");
  document.getElementById("termClearBtn").style.display = hasFilter ? "inline-block" : "none";
  renderConflicts();
  renderBlocs();
  renderMeetingsTable();
}

function renderConflicts() {
  const themesBar = document.getElementById("conflictThemesBar");
  const topicBlocMap = Object.fromEntries((TERM_DATA.topic_blocs || []).map(tb => [tb.topic, tb]));
  themesBar.innerHTML = (TERM_DATA.top_conflict_themes || []).map(th => {
    const tb = topicBlocMap[th.topic];
    let alignHtml = "";
    if (tb && (tb.blocs || []).length >= 2) {
      const aNames = tb.blocs[0].members.map(m => m.short_name).join(", ");
      const bNames = tb.blocs[1].members.map(m => m.short_name).join(", ");
      alignHtml = `<div class="theme-area-align"><span style="color:#93c5fd;">${esc(aNames)}</span> <span style="color:var(--dim);">vs</span> <span style="color:#fcd34d;">${esc(bNames)}</span></div>`;
    }
    return `
      <button class="theme-area-card ${ACTIVE_TOPIC === th.topic ? "active" : ""}" onclick="toggleTermTopic('${esc(th.topic)}')">
        <div class="theme-area-top">
          <div class="theme-area-name"><span class="topic-dot" style="background:${esc(th.color)};"></span>${esc(th.topic)}</div>
          <span class="pill pill-split">${th.split_votes_count} split${th.split_votes_count === 1 ? "" : "s"}</span>
        </div>
        <div class="theme-area-meta">${th.conflicts_count} recorded debate(s) &amp; contested votes &bull; Click to filter</div>
        ${alignHtml}
      </button>
    `;
  }).join("");

  const filtered = (TERM_DATA.conflicts || []).filter(c => {
    if (ACTIVE_TOPIC && c.category !== ACTIVE_TOPIC) return false;
    if (SEARCH_Q) {
      const hay = `${c.issue} ${c.category} ${c.summary} ${c.resolution} ${c.meeting_title} ${(c.side_a_members || []).join(" ")} ${(c.side_b_members || []).join(" ")}`.toLowerCase();
      if (!hay.includes(SEARCH_Q)) return false;
    }
    return true;
  });

  document.getElementById("conflictsCountBadge").innerHTML =
    `<span class="pill pill-split">${filtered.length} conflict(s)${ACTIVE_TOPIC ? " in " + esc(ACTIVE_TOPIC) : ""}</span>`;

  const limit = SHOW_ALL_CONFLICTS ? filtered.length : 8;
  const shown = filtered.slice(0, limit);
  const grid = document.getElementById("conflictsGrid");

  if (!shown.length) {
    grid.innerHTML = `<div class="card-box empty-msg" style="grid-column:1/-1;">No recorded conflicts match the current topic/keyword filter.</div>`;
    document.getElementById("conflictsMoreWrap").innerHTML = "";
    return;
  }

  grid.innerHTML = shown.map(c => {
    const argsA = (c.side_a_arguments || []).slice(0, 3).map(a => `<li>${esc(a)}</li>`).join("");
    const argsB = (c.side_b_arguments || []).slice(0, 3).map(a => `<li>${esc(a)}</li>`).join("");
    const memsA = (c.side_a_members || []).map(m => `<span class="mem-tag">${esc(m)}</span>`).join("");
    const memsB = (c.side_b_members || []).map(m => `<span class="mem-tag">${esc(m)}</span>`).join("");
    return `
      <article class="conflict-card">
        <div class="conflict-top">
          <div>
            <div class="conflict-title">${esc(c.issue)}</div>
            <div style="font-size:12px;color:var(--muted);margin-top:3px;">${esc(c.date)} &bull; ${esc(c.meeting_title)}</div>
          </div>
          <span class="pill pill-cat">${esc(c.category)}</span>
        </div>
        <div class="conflict-summary">${esc(c.summary)}</div>
        <div class="sides-grid">
          <div class="side-box a">
            <div class="side-lbl">Side A / Majority Position</div>
            <div class="side-pos">${esc(c.side_a_position || "—")}</div>
            ${argsA ? `<ul class="side-args">${argsA}</ul>` : ""}
            ${memsA ? `<div class="side-mems">${memsA}</div>` : ""}
          </div>
          <div class="side-box b">
            <div class="side-lbl">Side B / Dissenting Position</div>
            <div class="side-pos">${esc(c.side_b_position || "—")}</div>
            ${argsB ? `<ul class="side-args">${argsB}</ul>` : ""}
            ${memsB ? `<div class="side-mems">${memsB}</div>` : ""}
          </div>
        </div>
        <div class="conflict-foot">
          <div><strong>Outcome:</strong> <span style="color:#fff;">${esc(c.resolution || "—")}</span></div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            ${c.pdf_url ? `<a class="pdf-btn sm" href="${esc(c.pdf_url)}" target="_blank" rel="noopener">&#128196; Executive Summary PDF</a>` : ""}
            ${c.video_url ? `<a class="vid-btn sm" href="${esc(c.video_url)}" target="_blank" rel="noopener">&#9654; Video${c.timestamp_label ? " @" + esc(c.timestamp_label) : ""}</a>` : ""}
          </div>
        </div>
      </article>
    `;
  }).join("");

  const moreWrap = document.getElementById("conflictsMoreWrap");
  if (filtered.length > 8) {
    moreWrap.innerHTML = `<button class="nav-btn" onclick="toggleShowAllConflicts()">${SHOW_ALL_CONFLICTS ? "Show Fewer Conflicts" : `Show All ${filtered.length} Conflicts`}</button>`;
  } else {
    moreWrap.innerHTML = "";
  }
}

window.toggleShowAllConflicts = function () {
  SHOW_ALL_CONFLICTS = !SHOW_ALL_CONFLICTS;
  renderConflicts();
};

window.setBlocTab = function (tab) {
  BLOC_TAB = tab;
  renderBlocs();
};

window.setMatrixMode = function (mode) {
  MATRIX_MODE = mode;
  renderBlocs();
};

function renderBlocPairBoxes(blocObj) {
  if (!blocObj || !(blocObj.blocs || []).length) {
    return `<div style="font-size:12.5px;color:var(--muted);margin-top:8px;">${esc((blocObj && blocObj.summary) || "Not enough split votes to cluster.")}</div>`;
  }
  const boxes = blocObj.blocs.map(b => `
    <div class="bloc-box ${esc(b.tone)}">
      <div class="bloc-box-lbl">${esc(b.label)}</div>
      <div class="bloc-box-agr">${b.internal_agreement_pct}% internal split-vote agreement</div>
      <div class="bloc-mems">
        ${b.members.map(m => `<span class="mem-tag" title="${m.splits_cast} splits, ${m.split_nays} nays">${esc(m.name)} <span style="color:var(--dim);">(${m.split_nays}N)</span></span>`).join("")}
      </div>
    </div>
  `).join("");

  const swingHtml = (blocObj.swing_members || []).length
    ? `<div class="swing-strip"><strong>Swing / Cross-Bloc Voters:</strong> ${blocObj.swing_members.map(m => esc(m.name)).join(", ")}</div>`
    : "";

  return `<div style="font-size:12.5px;color:#cbd5e1;">${esc(blocObj.summary)}</div><div class="bloc-row">${boxes}</div>${swingHtml}`;
}

function renderBlocs() {
  const coh = TERM_DATA.cohesion;
  const banner = document.getElementById("cohesionBanner");
  banner.className = `cohesion-banner ${coh.mode}`;
  const shiftHtml = (coh.shifting_examples || []).length
    ? `<div style="font-size:12px;color:#fde68a;margin-top:6px;"><strong>Cross-Topic Shifts Observed:</strong> ${coh.shifting_examples.map(esc).join(" &bull; ")}</div>`
    : "";
  banner.innerHTML = `
    <div>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <span class="pill ${coh.mode === "cohesive" ? "pill-cohesive" : coh.mode === "consensus" ? "pill-consensus" : "pill-fluid"}">${esc(coh.label)}</span>
        <strong style="font-size:14px;">${esc(coh.note)}</strong>
      </div>
      ${shiftHtml}
    </div>
    <div style="font-size:12px;color:var(--muted);text-align:right;white-space:nowrap;">
      Split separation score: <strong style="color:#fff;">${coh.separation_score} pts</strong>
    </div>
  `;

  document.querySelectorAll("#blocTabBar .tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === BLOC_TAB);
  });

  const out = document.getElementById("blocContent");

  if (BLOC_TAB === "topics") {
    let tbs = TERM_DATA.topic_blocs || [];
    if (ACTIVE_TOPIC) {
      tbs = tbs.filter(t => t.topic === ACTIVE_TOPIC);
    }
    if (!tbs.length) {
      out.innerHTML = `<div class="card-box empty-msg">No split votes recorded${ACTIVE_TOPIC ? " in " + esc(ACTIVE_TOPIC) : ""} for this board-term.</div>`;
      return;
    }
    out.innerHTML = `<div class="bloc-cards-grid">${tbs.map(tb => {
      const exHtml = (tb.example_votes || []).slice(0, 3).map(ev => `
        <div class="ex-vote-item">
          <div>
            <div style="font-weight:600;color:#e2e8f0;">${esc(ev.item_title)}</div>
            <div style="font-size:11px;color:var(--muted);">${esc(ev.date)} &bull; <strong>${esc(ev.outcome)} (${esc(ev.tally)})</strong>${ev.nays.length ? " &bull; Nays: " + esc(ev.nays.join(", ")) : ""}</div>
          </div>
          ${ev.pdf_url ? `<a class="pdf-btn sm" href="${esc(ev.pdf_url)}" target="_blank" rel="noopener">&#128196; PDF</a>` : ""}
        </div>
      `).join("");
      return `
        <div class="topic-bloc-card">
          <div class="tb-hdr">
            <div class="tb-title"><span class="topic-dot" style="background:${esc(tb.color)};width:10px;height:10px;"></span>${esc(tb.topic)}</div>
            <span class="pill pill-split">${tb.split_votes_count} split / ${tb.total_votes_count} votes</span>
          </div>
          ${renderBlocPairBoxes(tb)}
          ${exHtml ? `<div class="ex-votes"><div style="font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;color:var(--dim);margin-bottom:4px;">Key Split Votes on ${esc(tb.topic)}</div>${exHtml}</div>` : ""}
        </div>
      `;
    }).join("")}</div>`;
    return;
  }

  if (BLOC_TAB === "overall") {
    const ob = TERM_DATA.overall_blocs;
    const pairsA = (ob.strongest_pairs || []).map(p =>
      `<div style="font-size:12.5px;padding:5px 0;border-bottom:1px solid rgba(36,52,84,0.4);"><strong>${esc(p.a_name)}</strong> &amp; <strong>${esc(p.b_name)}</strong>: <span style="color:#6ee7b7;font-weight:700;">${p.agreement_pct}%</span> (${p.shared_splits} split votes)</div>`
    ).join("") || `<div style="font-size:12px;color:var(--dim);">No high-agreement split pairs yet.</div>`;
    const pairsB = (ob.most_opposed_pairs || []).map(p =>
      `<div style="font-size:12.5px;padding:5px 0;border-bottom:1px solid rgba(36,52,84,0.4);"><strong>${esc(p.a_name)}</strong> vs <strong>${esc(p.b_name)}</strong>: <span style="color:#fca5a5;font-weight:700;">${p.agreement_pct}%</span> (${p.shared_splits} split votes)</div>`
    ).join("") || `<div style="font-size:12px;color:var(--dim);">No sharply opposed pairs yet.</div>`;

    out.innerHTML = `
      <div class="card-box">
        ${renderBlocPairBoxes(ob)}
        <div class="drawer-grid" style="margin-top:16px;">
          <div class="drawer-box"><h4>Strongest Split-Vote Allies</h4>${pairsA}</div>
          <div class="drawer-box"><h4>Most Frequent Split-Vote Opponents</h4>${pairsB}</div>
        </div>
      </div>
    `;
    return;
  }

  // Pairwise Agreement Matrix
  const pw = TERM_DATA.pairwise || {};
  const ids = pw.member_ids || [];
  const rosterMap = Object.fromEntries((TERM_DATA.roster || []).map(r => [r.id, r]));
  const mat = MATRIX_MODE === "split" ? pw.split : pw.all;
  const cnt = MATRIX_MODE === "split" ? pw.split_counts : pw.all_counts;

  function cellBg(val, isDiag) {
    if (isDiag) return "background:#1e293b;color:#64748b;";
    if (val == null) return "background:#0a101d;color:#475569;";
    if (val >= 80) return "background:rgba(16,185,129,0.28);color:#6ee7b7;";
    if (val >= 60) return "background:rgba(56,189,248,0.2);color:#bae6fd;";
    if (val >= 40) return "background:rgba(245,158,11,0.2);color:#fde68a;";
    return "background:rgba(239,68,68,0.28);color:#fca5a5;";
  }

  const hdrCells = ids.map(id => `<th style="text-align:center;">${esc((rosterMap[id] || {}).short_name || id)}</th>`).join("");
  const rows = ids.map(rId => {
    const rName = (rosterMap[rId] || {}).name || rId;
    const cells = ids.map(cId => {
      const val = (mat[rId] || {})[cId];
      const n = (cnt[rId] || {})[cId] || 0;
      const isDiag = rId === cId;
      const txt = isDiag ? "—" : (val == null ? "·" : `${val.toFixed(0)}%`);
      return `<td class="hm-cell" style="${cellBg(val, isDiag)}" title="${esc(rName)} vs ${esc((rosterMap[cId] || {}).name || cId)}: ${val == null ? "no shared votes" : val + "% across " + n + " votes"}">${txt}</td>`;
    }).join("");
    return `<tr><td style="font-weight:700;white-space:nowrap;">${esc(rName)}</td>${cells}</tr>`;
  }).join("");

  out.innerHTML = `
    <div class="card-box">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px;">
        <div style="font-size:13px;color:var(--muted);">
          Showing <strong>${MATRIX_MODE === "split" ? "Split-Vote Only" : "All Non-Consent Votes"}</strong> pairwise agreement (hover cell for vote count).
        </div>
        <div style="display:flex;gap:6px;">
          <button class="tab-btn ${MATRIX_MODE === "split" ? "active" : ""}" style="padding:5px 11px;font-size:12px;" onclick="setMatrixMode('split')">Split Votes Only</button>
          <button class="tab-btn ${MATRIX_MODE === "all" ? "active" : ""}" style="padding:5px 11px;font-size:12px;" onclick="setMatrixMode('all')">All Votes</button>
        </div>
      </div>
      <table class="data-table">
        <thead><tr><th>Member</th>${hdrCells}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function renderMeetingsTable() {
  let list = (TERM_DATA.meetings || []).filter(m => {
    if (ACTIVE_TOPIC && !(m.topics || []).includes(ACTIVE_TOPIC)) return false;
    if (MTG_FILTER === "splits" && !m.split_votes_count) return false;
    if (MTG_FILTER === "debates" && !m.debates_count) return false;
    if (MTG_FILTER === "pdfs" && !m.pdf_exists) return false;
    if (SEARCH_Q && !(m.search_blob || "").includes(SEARCH_Q)) return false;
    return true;
  });

  list = [...list].sort((a, b) => {
    if (SORT_BY === "date_asc") return (a.date || "").localeCompare(b.date || "");
    if (SORT_BY === "splits_desc") return (b.split_votes_count - a.split_votes_count) || (b.date || "").localeCompare(a.date || "");
    if (SORT_BY === "votes_desc") return (b.votes_count - a.votes_count) || (b.date || "").localeCompare(a.date || "");
    return (b.date || "").localeCompare(a.date || "");
  });

  document.getElementById("meetingsSub").textContent =
    `Showing ${list.length} of ${(TERM_DATA.meetings || []).length} meetings in this term — click any row for full timestamped agenda, votes, and debates`;

  const tbody = document.getElementById("meetingsTableBody");
  if (!list.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-msg">No meetings match the current topic/keyword filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(m => {
    const isOpen = OPEN_DRAWERS.has(m.id);
    const topicPills = (m.topics || []).slice(0, 3).map(t => `<span class="pill pill-cat" style="margin:2px 3px 2px 0;">${esc(t)}</span>`).join("");
    const pdfBtn = m.pdf_exists
      ? `<a class="pdf-btn sm" href="${esc(m.pdf_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">&#128196; Executive Summary PDF</a>`
      : `<span style="font-size:11.5px;color:var(--dim);">Pending PDF</span>`;
    const vidBtn = m.video_url
      ? `<a class="vid-btn sm" href="${esc(m.video_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">&#9654; Video</a>`
      : "";
    const obBtn = m.onbase_url
      ? `<a class="nav-link" style="font-size:11px;padding:3px 8px;border-color:rgba(16,185,129,0.4);color:#6ee7b7;" href="${esc(m.onbase_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">&#128206; OnBase (${m.onbase_docs_count || 0} docs)</a>`
      : "";

    let drawerHtml = "";
    if (isOpen) {
      const agHtml = (m.agenda_items || []).map(a => `
        <div class="ag-item">
          <div style="display:flex;justify-content:space-between;gap:8px;align-items:baseline;">
            <strong>${esc(a.title)}</strong>
            ${a.video_timestamp_url ? `<a href="${esc(a.video_timestamp_url)}" target="_blank" rel="noopener" style="font-family:monospace;font-size:11.5px;white-space:nowrap;">&#9654; ${esc(a.timestamp_label || "Watch")}</a>` : ""}
          </div>
          ${a.discussion_summary ? `<div style="color:var(--muted);font-size:12px;margin-top:3px;">${esc(a.discussion_summary)}</div>` : ""}
          ${a.vote_summary ? `<div style="color:#6ee7b7;font-size:11.5px;margin-top:2px;">${esc(a.vote_summary)}</div>` : ""}
        </div>
      `).join("") || `<div style="color:var(--dim);font-size:12px;">No itemized agenda breakdown recorded.</div>`;

      const vtHtml = (m.votes || []).map(v => `
        <div class="vt-item">
          <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap;">
            <strong>${esc(v.item_title)}</strong>
            <span class="pill ${v.is_split ? "pill-split" : "pill-pass"}">${esc(v.outcome)} (${esc(v.tally)})</span>
          </div>
          ${v.is_split && v.ayes && v.ayes.length ? `<div style="font-size:11.5px;color:#6ee7b7;margin-top:3px;"><strong>Ayes:</strong> ${esc(v.ayes.join(", "))}</div>` : ""}
          ${v.nays.length ? `<div style="font-size:11.5px;color:#fca5a5;margin-top:3px;"><strong>Nays:</strong> ${esc(v.nays.join(", "))}</div>` : ""}
          ${v.abstentions.length ? `<div style="font-size:11.5px;color:#fde68a;margin-top:2px;"><strong>Abstentions:</strong> ${esc(v.abstentions.join(", "))}</div>` : ""}
          ${v.discussion_detail || v.notes ? `<div style="font-size:11.5px;color:var(--muted);margin-top:3px;">${esc(v.discussion_detail || v.notes)}</div>` : ""}
        </div>
      `).join("") || `<div style="color:var(--dim);font-size:12px;">No formal non-consent roll-call votes recorded.</div>`;

      const obItemsHtml = (m.onbase_items || []).length ? `
        <div class="drawer-box" style="margin-top:12px;">
          <h4>Official OnBase Agenda Items &amp; Supporting Documents (${m.onbase_docs_count || 0} PDFs)</h4>
          ${(m.onbase_items || []).map(oi => `
            <details style="border-bottom:1px solid rgba(36,52,84,0.45);padding:6px 0;">
              <summary style="cursor:pointer;font-size:12.5px;color:#e2e8f0;font-weight:600;">
                ${oi.num ? esc(oi.num) + ". " : ""}${esc(oi.title)}
                ${oi.case_num ? `<span class="pill pill-cat" style="margin-left:6px;font-size:10px;">${esc(oi.case_num)}</span>` : ""}
                ${oi.vote ? `<span class="pill pill-pass" style="margin-left:6px;font-size:10px;">${esc(oi.vote)}</span>` : ""}
                <span style="color:var(--dim);font-size:11px;margin-left:6px;">(${(oi.docs || []).length} docs)</span>
              </summary>
              <div style="display:flex;flex-wrap:wrap;gap:6px;margin:7px 0 4px 12px;">
                ${(oi.docs || []).map(d => `<a href="${esc(d.u)}" target="_blank" rel="noopener" style="font-size:11px;padding:3px 8px;border-radius:6px;background:var(--surface-2);border:1px solid var(--border);color:#cbd5e1;"><strong style="color:#7dd3fc;">[${esc(d.c)}]</strong> ${esc(d.t)}</a>`).join("")}
              </div>
            </details>
          `).join("")}
        </div>
      ` : "";

      const splitSumItems = (m.votes || []).filter(v => v.is_split).map(v => {
        const sides = [];
        if (v.ayes && v.ayes.length) sides.push(`<span style="color:#6ee7b7;"><strong>Ayes:</strong> ${esc(v.ayes.join(", "))}</span>`);
        if (v.nays && v.nays.length) sides.push(`<span style="color:#fca5a5;"><strong>Nays:</strong> ${esc(v.nays.join(", "))}</span>`);
        if (v.abstentions && v.abstentions.length) sides.push(`<span style="color:#fde68a;"><strong>Abstain:</strong> ${esc(v.abstentions.join(", "))}</span>`);
        return `<div style="font-size:12px;margin-top:4px;"><strong>${esc(v.item_title)}</strong> (${esc(v.outcome)} ${esc(v.tally)}) &mdash; ${sides.join(" &bull; ") || "Roll-call names not recorded"}</div>`;
      }).join("");

      const splitSumBox = splitSumItems
        ? `<div style="margin-top:10px;padding:10px 12px;border-radius:8px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);"><div style="font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;color:#fca5a5;">Split Votes Breakdown (Names on Each Side)</div>${splitSumItems}</div>`
        : "";

      drawerHtml = `
        <tr class="drawer-row">
          <td colspan="5">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;">
              <div style="max-width:860px;font-size:13px;color:#e2e8f0;">
                <strong style="color:var(--accent);">Executive Summary:</strong> ${esc(m.executive_summary)}
                ${splitSumBox}
              </div>
              <div style="display:flex;gap:8px;flex-wrap:wrap;">
                ${m.pdf_exists ? `<a class="pdf-btn" href="${esc(m.pdf_url)}" target="_blank" rel="noopener">&#128196; Open Full Executive Summary PDF</a>` : ""}
                ${m.video_url ? `<a class="vid-btn" href="${esc(m.video_url)}" target="_blank" rel="noopener">&#9654; Watch Full Video</a>` : ""}
                ${m.onbase_url ? `<a class="nav-btn" style="border-color:var(--city);color:#6ee7b7;" href="${esc(m.onbase_url)}" target="_blank" rel="noopener">&#128206; Official OnBase Agenda</a>` : ""}
              </div>
            </div>
            <div class="drawer-grid">
              <div class="drawer-box"><h4>Timestamped Agenda Topics (${(m.agenda_items || []).length})</h4>${agHtml}</div>
              <div class="drawer-box"><h4>Recorded Votes (${(m.votes || []).length})</h4>${vtHtml}</div>
            </div>
            ${obItemsHtml}
          </td>
        </tr>
      `;
    }

    return `
      <tr class="mtg-row" onclick="toggleMtgDrawer('${esc(m.id)}')">
        <td style="white-space:nowrap;">
          <strong>${esc(m.date)}</strong>
          <div style="font-size:11px;color:var(--dim);">${esc(m.meeting_type)}</div>
          ${m.duration ? `<div style="font-size:11px;color:var(--dim);">${esc(m.duration)}</div>` : ""}
        </td>
        <td>
          <div style="font-weight:700;color:#fff;">${isOpen ? "&#9662;" : "&#9656;"} ${esc(m.title)}</div>
          <div style="font-size:12px;color:var(--muted);margin-top:4px;max-width:520px;">${esc((m.executive_summary || "").slice(0, 190))}${(m.executive_summary || "").length > 190 ? "..." : ""}</div>
        </td>
        <td style="white-space:nowrap;">
          <div style="display:flex;flex-direction:column;gap:6px;align-items:flex-start;">
            ${pdfBtn}
            ${vidBtn}
            ${obBtn}
          </div>
        </td>
        <td>${topicPills}</td>
        <td style="white-space:nowrap;">
          <div><strong>${m.votes_count}</strong> votes</div>
          ${m.split_votes_count ? `<div style="margin-top:4px;"><span class="pill pill-split">${m.split_votes_count} split</span></div>` : `<div style="font-size:11px;color:var(--dim);">Unanimous</div>`}
          ${m.debates_count ? `<div style="font-size:11px;color:#c4b5fd;margin-top:3px;">${m.debates_count} debate(s)</div>` : ""}
        </td>
      </tr>
      ${drawerHtml}
    `;
  }).join("");
}

window.toggleMtgDrawer = function (id) {
  if (OPEN_DRAWERS.has(id)) OPEN_DRAWERS.delete(id);
  else OPEN_DRAWERS.add(id);
  renderMeetingsTable();
};
