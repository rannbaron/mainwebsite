/* Hub page controller for /durhampolitics/beta/index.html */
let HUB_DATA = null;
let ACTIVE_TOPIC = "";
let ACTIVE_BOARD = "all";
let SEARCH_Q = "";

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

window.__onBetaAuthUnlocked = async function () {
  const res = await fetch("./data/hub_index.json?t=" + Date.now(), { cache: "no-store" });
  HUB_DATA = await res.json();
  document.getElementById("hubUpdated").textContent = HUB_DATA.generated_at || "";

  renderHubKpis();
  renderTopicChips();
  renderBoards();

  const inp = document.getElementById("hubSearchInput");
  inp.addEventListener("input", () => {
    SEARCH_Q = inp.value.trim().toLowerCase();
    renderSearchAndBoards();
  });
  const sel = document.getElementById("hubBoardFilter");
  sel.addEventListener("change", () => {
    ACTIVE_BOARD = sel.value;
    renderSearchAndBoards();
  });
};

function renderHubKpis() {
  const t = HUB_DATA.totals || {};
  document.getElementById("hubKpis").innerHTML = `
    <div class="kpi"><div class="kpi-lbl">Board-Terms Ready</div><div class="kpi-val" style="color:#38bdf8;">${t.terms_ready}</div><div class="kpi-sub">Dedicated deep-dive pages</div></div>
    <div class="kpi"><div class="kpi-lbl">Meetings Analyzed</div><div class="kpi-val" style="color:#6ee7b7;">${(t.meetings || 0).toLocaleString()}</div><div class="kpi-sub">${esc(HUB_DATA.coverage)}</div></div>
    <div class="kpi"><div class="kpi-lbl">Executive Summary PDFs</div><div class="kpi-val" style="color:#fca5a5;">${(t.pdfs || 0).toLocaleString()}</div><div class="kpi-sub">Direct hyperlinked reports</div></div>
    <div class="kpi"><div class="kpi-lbl">Split Votes Tracked</div><div class="kpi-val" style="color:#fcd34d;">${(t.split_votes || 0).toLocaleString()}</div><div class="kpi-sub">Used for voting-bloc clustering</div></div>
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
  renderTopicChips();
  renderSearchAndBoards();
};

window.clearHubSearch = function () {
  ACTIVE_TOPIC = "";
  ACTIVE_BOARD = "all";
  SEARCH_Q = "";
  document.getElementById("hubSearchInput").value = "";
  document.getElementById("hubBoardFilter").value = "all";
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

  const matchConflict = c => {
    if (ACTIVE_BOARD !== "all" && c.body_id !== ACTIVE_BOARD) return false;
    if (ACTIVE_TOPIC && c.category !== ACTIVE_TOPIC) return false;
    if (SEARCH_Q && !c.q.includes(SEARCH_Q)) return false;
    return true;
  };
  const matchMtg = m => {
    if (ACTIVE_BOARD !== "all" && m.body_id !== ACTIVE_BOARD) return false;
    if (ACTIVE_TOPIC && !(m.topics || []).includes(ACTIVE_TOPIC)) return false;
    if (SEARCH_Q && !m.q.includes(SEARCH_Q)) return false;
    return true;
  };

  const cHits = (HUB_DATA.search_conflicts || []).filter(matchConflict);
  const mHits = (HUB_DATA.search_meetings || []).filter(matchMtg);

  const qs = new URLSearchParams();
  if (ACTIVE_TOPIC) qs.set("topic", ACTIVE_TOPIC);
  if (SEARCH_Q) qs.set("q", SEARCH_Q);
  const qSuffix = qs.toString() ? "?" + qs.toString() : "";

  const conflictHtml = cHits.slice(0, 12).map(c => `
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

  const mtgHtml = mHits.slice(0, 12).map(m => `
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

  box.innerHTML = `
    <div style="font-size:13px;font-weight:700;margin-bottom:12px;color:#e2e8f0;">
      Found <span style="color:#38bdf8;">${cHits.length}</span> conflict(s) and <span style="color:#6ee7b7;">${mHits.length}</span> meeting(s) across all board-terms
    </div>
    <div class="sr-grid">
      <div>
        <div style="font-size:11.5px;font-weight:800;text-transform:uppercase;letter-spacing:0.06em;color:#fca5a5;margin-bottom:8px;">Matching Conflicts &amp; Split Debates (Top ${Math.min(12, cHits.length)})</div>
        ${conflictHtml}
      </div>
      <div>
        <div style="font-size:11.5px;font-weight:800;text-transform:uppercase;letter-spacing:0.06em;color:#6ee7b7;margin-bottom:8px;">Matching Meetings &amp; Summaries (Top ${Math.min(12, mHits.length)})</div>
        ${mtgHtml}
      </div>
    </div>
  `;
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
      return `
        <a class="term-card" href="${esc(t.href + qSuffix)}">
          <div>
            <div class="term-card-top">
              <div>
                <div class="term-title">${esc(t.label)}</div>
                <div class="term-dates">${esc(t.date_range_label)}${t.transition_reason ? " &bull; " + esc(t.transition_reason) : ""}</div>
              </div>
              <div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px;">
                ${t.is_current ? `<span class="pill pill-current">Current Term</span>` : ""}
                ${cohesionPill(t.cohesion)}
              </div>
            </div>
            <div class="term-roster"><strong>Seated:</strong> ${esc((t.roster_names || []).join(", ") || "See term page")}</div>
            <div class="term-stats-row">
              <div class="tstat"><b>${k.meetings_count || 0}</b><span>Meetings</span></div>
              <div class="tstat"><b style="color:#fca5a5;">${k.pdfs_count || 0}</b><span>PDFs</span></div>
              <div class="tstat"><b style="color:#fcd34d;">${k.split_votes_count || 0}</b><span>Splits</span></div>
              <div class="tstat"><b style="color:#c4b5fd;">${k.conflicts_count || 0}</b><span>Conflicts</span></div>
            </div>
            ${themesHtml ? `<div style="font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--dim);margin-top:12px;">Primary Areas of Disagreement</div><div class="term-themes" style="margin-top:6px;">${themesHtml}</div>` : ""}
          </div>
          <div class="term-card-cta">
            <span>Open Term Conflicts, Voting Blocs &amp; Meetings</span>
            <span>&rarr;</span>
          </div>
        </a>
      `;
    }).join("") || `<div class="empty-msg">No terms match the active topic filter for this board.</div>`;

    const pendingNote = b.pending_terms_count > 0
      ? ` &bull; ${b.pending_terms_count} earlier historical term(s) backfilling from grid ASR`
      : "";

    return `
      <section class="board-section">
        <div class="board-sec-hdr">
          <div class="board-sec-title">
            <span class="board-stripe" style="background:${esc(b.badge_color)};"></span>
            <span>${esc(b.name)}</span>
          </div>
          <div class="board-sec-meta">${b.terms.length} term(s) ready &bull; ${b.total_seats} seats &bull; ${esc(b.regular_schedule)}${pendingNote}</div>
        </div>
        <div class="terms-grid">${cardsHtml}</div>
      </section>
    `;
  }).join("");
}
