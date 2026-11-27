/* Interactive Development Decision Patterns & Council Member Evolution Explorer */
(function () {
  let DEV_DATA = null;
  let ACTIVE_TAB = "criteria";
  let SELECTED_MEMBERS = new Set();
  let OPEN_CASES = new Set();
  let CASES_LIMIT = 40;

  const PALETTE = ["#38bdf8", "#10b981", "#f59e0b", "#f472b6", "#a78bfa", "#fb7185", "#34d399", "#facc15"];
  const CURRENT_COUNCIL_NAMES = ["Leonardo Williams", "Javiera Caballero", "Nate Baker", "Shanetta Burris", "Chelsea Cook", "Matthew Kopac", "Carl Rist"];

  const CRITERIA_COLS = [
    { key: "overall", label: "Overall", filter: {} },
    { key: "contested", label: "Contested Only", filter: { contested: true } },
    { key: "aff_yes", label: "Has Afford. Proffer", filter: { proffer: "aff_yes" } },
    { key: "aff_no", label: "No Afford. Proffer", filter: { proffer: "aff_no" } },
    { key: "aff_60", label: "Afford. <=60% AMI", filter: { proffer: "aff_60" } },
    { key: "dps_yes", label: "DPS Donation", filter: { proffer: "dps_yes" } },
    { key: "env_yes", label: "Env/Tree/Storm.", filter: { proffer: "env_yes" } },
    { key: "transit_yes", label: "Transit/Sidewalk", filter: { proffer: "transit_yes" } },
    { key: "post_pc", label: "Post-PC Proffers", filter: { proffer: "post_pc" } },
    { key: "pc_app", label: "PC Rec: Approve", filter: { pc: "Approval" } },
    { key: "pc_den", label: "PC Rec: Deny", filter: { pc: "Denial" } },
    { key: "staff_con", label: "Staff Consistent", filter: { proffer: "staff_consistent" } },
    { key: "staff_inc", label: "Staff Inconsistent", filter: { proffer: "staff_inconsistent" } },
    { key: "urban", label: "Urban Tier", filter: { tier: "Urban" } },
    { key: "suburban", label: "Suburban Tier", filter: { tier: "Suburban" } },
    { key: "annex", label: "Rural / Annex.", filter: { proffer: "annex" } },
    { key: "large200", label: "200+ Units", filter: { proffer: "large200" } },
  ];

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function pctBg(pct, n) {
    if (pct == null || n === 0) return "background:#0a101d;color:#475569;";
    if (pct >= 85) return "background:rgba(16,185,129,0.30);color:#6ee7b7;";
    if (pct >= 65) return "background:rgba(56,189,248,0.22);color:#bae6fd;";
    if (pct >= 45) return "background:rgba(245,158,11,0.24);color:#fde68a;";
    return "background:rgba(239,68,68,0.30);color:#fca5a5;";
  }

  function caseMatchesCriterion(c, key) {
    if (key === "overall") return true;
    if (key === "contested") return Boolean(c.is_contested);
    if (key === "aff_yes") return Boolean(c.has_aff);
    if (key === "aff_no") return !c.has_aff;
    if (key === "aff_60") return c.aff_ami != null && c.aff_ami <= 60;
    if (key === "dps_yes") return c.dps_usd != null && c.dps_usd > 0;
    if (key === "env_yes") return Boolean(c.has_env || c.has_storm);
    if (key === "transit_yes") return Boolean(c.has_transit);
    if (key === "post_pc") return Boolean(c.post_pc);
    if (key === "pc_app") return c.pc_rec === "Approval";
    if (key === "pc_den") return c.pc_rec === "Denial";
    if (key === "staff_con") return c.staff_con === "Consistent";
    if (key === "staff_inc") return c.staff_con === "Inconsistent";
    if (key === "urban") return c.tier === "Urban";
    if (key === "suburban") return c.tier === "Suburban";
    if (key === "annex") return c.tier === "Rural" || Boolean(c.is_annex);
    if (key === "large200") return c.units != null && c.units >= 200;
    return true;
  }

  window.__onBetaAuthUnlocked = async function () {
    try {
      const resp = await fetch("./data/development_cases.json", { cache: "no-store" });
      DEV_DATA = await resp.json();
      initControls();
      renderKpis();
      selectCurrentCouncil();
      renderCriteriaMatrix();
      renderCases();
    } catch (e) {
      document.getElementById("criteriaMatrixWrap").innerHTML =
        `<div style="padding:20px;color:#fca5a5;">Failed to load development dataset: ${esc(e.message)}</div>`;
    }
  };

  function initControls() {
    const years = Array.from(new Set((DEV_DATA.cases || []).map(c => c.year).filter(Boolean))).sort((a, b) => b - a);
    const ySel = document.getElementById("caseYear");
    years.forEach(y => {
      const opt = document.createElement("option");
      opt.value = String(y);
      opt.textContent = String(y);
      ySel.appendChild(opt);
    });
    const mSel = document.getElementById("caseMember");
    (DEV_DATA.members || []).forEach(m => {
      const opt = document.createElement("option");
      opt.value = m.name;
      opt.textContent = `${m.name} (${m.total_votes} votes)`;
      mSel.appendChild(opt);
    });
  }

  function renderKpis() {
    const s = DEV_DATA.summary || {};
    document.getElementById("devKpis").innerHTML = `
      <div class="kpi"><div class="kpi-lbl">Development Cases</div><div class="kpi-val" style="color:#6ee7b7;">${s.cases_count || 0}</div><div class="kpi-sub">${s.voted_cases_count || 0} with official votes</div></div>
      <div class="kpi"><div class="kpi-lbl">Contested Cases</div><div class="kpi-val" style="color:#fcd34d;">${s.contested_cases_count || 0}</div><div class="kpi-sub">${s.denied_cases_count || 0} denied by Council</div></div>
      <div class="kpi"><div class="kpi-lbl">With Affordable Proffers</div><div class="kpi-val" style="color:#38bdf8;">${s.affordable_proffer_cases || 0}</div><div class="kpi-sub">${s.post_pc_proffer_cases || 0} sweetened post-PC</div></div>
      <div class="kpi"><div class="kpi-lbl">Supporting PDFs Linked</div><div class="kpi-val" style="color:#c4b5fd;">${(s.docs_linked_count || 0).toLocaleString()}</div><div class="kpi-sub">${(s.pdfs_extracted_count || 0).toLocaleString()} reports text-parsed</div></div>
      <div class="kpi"><div class="kpi-lbl">Council Members Tracked</div><div class="kpi-val" style="color:#fca5a5;">${(DEV_DATA.members || []).length}</div><div class="kpi-sub">Spanning ${esc(s.date_range || "2016-2026")}</div></div>
    `;
  }

  window.setDevTab = function (tab) {
    ACTIVE_TAB = tab;
    document.querySelectorAll(".dev-tab").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
    document.querySelectorAll(".dev-panel").forEach(p => p.classList.toggle("active", p.id === "panel-" + tab));
    if (tab === "evolution") renderEvolution();
    if (tab === "cases") renderCases();
  };

  window.renderCriteriaMatrix = function () {
    if (!DEV_DATA) return;
    const contestedOnly = document.getElementById("critContestedOnly").checked;
    const minVotes = parseInt(document.getElementById("critMinVotes").value || "10", 10);

    // Filter to decided zoning/annexation/development cases
    const cases = (DEV_DATA.cases || []).filter(c =>
      (c.outcome === "Approved" || c.outcome === "Denied") &&
      (!contestedOnly || c.is_contested)
    );

    // Build per-member vote lookup
    const members = (DEV_DATA.members || []).filter(m => m.total_votes >= minVotes);
    const hdr = CRITERIA_COLS.map(col => `<th>${esc(col.label)}</th>`).join("");
    const bodyRows = members.map(m => {
      const mCases = cases.filter(c => c.mv && c.mv[m.name]);
      const cells = CRITERIA_COLS.map(col => {
        const sub = mCases.filter(c => caseMatchesCriterion(c, col.key));
        const n = sub.length;
        const ayes = sub.filter(c => c.mv[m.name] === "AYE").length;
        const pct = n > 0 ? Math.round((ayes * 1000) / n) / 10 : null;
        const txt = n > 0 ? `${pct.toFixed(0)}%<span class="crit-n">${ayes}/${n}</span>` : "·";
        return `<td class="crit-cell" style="${pctBg(pct, n)}" onclick="drillIntoCell('${esc(m.name)}','${col.key}',${contestedOnly})" title="${esc(m.name)} — ${esc(col.label)}: ${ayes} Aye / ${n} votes (${pct == null ? "n/a" : pct + "%"})">${txt}</td>`;
      }).join("");
      return `<tr><td>${esc(m.name)} <span style="color:var(--dim);font-weight:500;">(${mCases.length})</span></td>${cells}</tr>`;
    }).join("");

    document.getElementById("criteriaMatrixWrap").innerHTML = `
      <table class="criteria-table">
        <thead><tr><th>Council Member (Votes)</th>${hdr}</tr></thead>
        <tbody>${bodyRows || '<tr><td colspan="18" style="padding:20px;color:var(--muted);">No members match the minimum vote filter.</td></tr>'}</tbody>
      </table>
    `;
  };

  window.drillIntoCell = function (memberName, critKey, contestedOnly) {
    resetCaseFilters(false);
    document.getElementById("caseMember").value = memberName;
    const col = CRITERIA_COLS.find(c => c.key === critKey);
    if (col && col.filter) {
      if (col.filter.contested || contestedOnly) document.getElementById("caseContestedOnly").checked = true;
      if (col.filter.proffer) document.getElementById("caseProfferFilter").value = col.filter.proffer;
      if (col.filter.pc) document.getElementById("casePC").value = col.filter.pc;
      if (col.filter.tier) document.getElementById("caseTier").value = col.filter.tier;
    }
    setDevTab("cases");
    renderCases();
  };

  window.selectTopMembers = function (k) {
    SELECTED_MEMBERS = new Set((DEV_DATA.members || []).slice(0, k).map(m => m.name));
    renderEvolution();
  };

  window.selectCurrentCouncil = function () {
    const avail = new Set((DEV_DATA.members || []).map(m => m.name));
    SELECTED_MEMBERS = new Set(CURRENT_COUNCIL_NAMES.filter(n => avail.has(n)));
    if (SELECTED_MEMBERS.size === 0) selectTopMembers(6);
    else renderEvolution();
  };

  window.toggleEvoMember = function (name) {
    if (SELECTED_MEMBERS.has(name)) SELECTED_MEMBERS.delete(name);
    else SELECTED_MEMBERS.add(name);
    renderEvolution();
  };

  window.renderEvolution = function () {
    if (!DEV_DATA) return;
    const contestedOnly = document.getElementById("evoContestedOnly").checked;
    const members = (DEV_DATA.members || []).filter(m => m.total_votes >= 5);
    const colorMap = {};
    let ci = 0;
    members.forEach(m => {
      if (SELECTED_MEMBERS.has(m.name)) {
        colorMap[m.name] = PALETTE[ci % PALETTE.length];
        ci++;
      }
    });

    document.getElementById("evoMemberChips").innerHTML = members.map(m => {
      const act = SELECTED_MEMBERS.has(m.name);
      const dot = act ? `<span style="width:9px;height:9px;border-radius:50%;background:${colorMap[m.name]};display:inline-block;"></span>` : "";
      return `<button class="mem-sel-chip ${act ? "active" : ""}" onclick="toggleEvoMember('${esc(m.name)}')">${dot}${esc(m.name)} <span style="opacity:0.65;">(${m.total_votes})</span></button>`;
    }).join("");

    const cases = (DEV_DATA.cases || []).filter(c =>
      (c.outcome === "Approved" || c.outcome === "Denied") &&
      c.year && (!contestedOnly || c.is_contested)
    );
    const years = Array.from(new Set(cases.map(c => c.year))).sort((a, b) => a - b);
    const selList = members.filter(m => SELECTED_MEMBERS.has(m.name));

    // Compute per-member per-year approval %
    const series = selList.map(m => {
      const pts = years.map(yr => {
        const sub = cases.filter(c => c.year === yr && c.mv && c.mv[m.name]);
        const n = sub.length;
        const ayes = sub.filter(c => c.mv[m.name] === "AYE").length;
        return { yr, n, ayes, pct: n >= 1 ? Math.round((ayes * 1000) / n) / 10 : null };
      });
      return { name: m.name, color: colorMap[m.name], pts };
    });

    // Render SVG line chart
    const W = 880, H = 300, padL = 48, padR = 24, padT = 22, padB = 36;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const xPos = idx => padL + (years.length <= 1 ? plotW / 2 : (idx / (years.length - 1)) * plotW);
    const yPos = pct => padT + plotH - (pct / 100) * plotH;

    let gridSvg = "";
    [0, 25, 50, 75, 100].forEach(v => {
      const y = yPos(v);
      gridSvg += `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" stroke="rgba(148,163,184,0.18)" stroke-dasharray="3,3" />`;
      gridSvg += `<text x="${padL - 8}" y="${y + 4}" text-anchor="end" fill="#94a3b8" font-size="11">${v}%</text>`;
    });
    years.forEach((yr, idx) => {
      const x = xPos(idx);
      gridSvg += `<text x="${x}" y="${H - 12}" text-anchor="middle" fill="#cbd5e1" font-size="11.5" font-weight="600">${yr}</text>`;
    });

    let linesSvg = "";
    series.forEach(s => {
      let pathD = "";
      s.pts.forEach((p, idx) => {
        if (p.pct == null) return;
        const x = xPos(idx), y = yPos(p.pct);
        pathD += (pathD ? " L " : "M ") + `${x.toFixed(1)} ${y.toFixed(1)}`;
      });
      if (pathD) {
        linesSvg += `<path d="${pathD}" fill="none" stroke="${s.color}" stroke-width="2.6" stroke-linejoin="round" />`;
      }
      s.pts.forEach((p, idx) => {
        if (p.pct == null) return;
        const x = xPos(idx), y = yPos(p.pct);
        linesSvg += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4.5" fill="${s.color}" stroke="#070b14" stroke-width="1.5"><title>${esc(s.name)} (${p.yr}): ${p.pct}% Aye (${p.ayes}/${p.n})</title></circle>`;
      });
    });

    const legendHtml = series.map(s =>
      `<span style="display:inline-flex;align-items:center;gap:6px;margin-right:14px;font-size:12px;"><span style="width:12px;height:3px;background:${s.color};display:inline-block;"></span>${esc(s.name)}</span>`
    ).join("");

    document.getElementById("evoChartBox").innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
        <strong style="font-size:13.5px;">Approval Rate Trajectory on Development Cases (${contestedOnly ? "Contested Votes Only" : "All Voted Cases"})</strong>
        <div>${legendHtml}</div>
      </div>
      <svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:960px;height:auto;display:block;">
        ${gridSvg}${linesSvg}
      </svg>
    `;

    const yrHdrs = years.map(y => `<th>${y}</th>`).join("");
    const tblRows = series.map(s => {
      const cells = s.pts.map(p => {
        const txt = p.n > 0 ? `${p.pct.toFixed(0)}%<span class="crit-n">${p.ayes}/${p.n}</span>` : "·";
        return `<td style="${pctBg(p.pct, p.n)}">${txt}</td>`;
      }).join("");
      return `<tr><td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${s.color};margin-right:6px;"></span>${esc(s.name)}</td>${cells}</tr>`;
    }).join("");

    document.getElementById("evoTableWrap").innerHTML = `
      <table class="criteria-table">
        <thead><tr><th>Council Member</th>${yrHdrs}</tr></thead>
        <tbody>${tblRows}</tbody>
      </table>
    `;
  };

  window.resetCaseFilters = function (doRender = true) {
    document.getElementById("caseSearch").value = "";
    document.getElementById("caseYear").value = "";
    document.getElementById("caseMember").value = "";
    document.getElementById("caseVoteCast").value = "";
    document.getElementById("caseOutcome").value = "";
    document.getElementById("casePC").value = "";
    document.getElementById("caseTier").value = "";
    document.getElementById("caseProfferFilter").value = "";
    document.getElementById("caseContestedOnly").checked = false;
    CASES_LIMIT = 40;
    if (doRender) renderCases();
  };

  window.toggleCaseCard = function (id) {
    if (OPEN_CASES.has(id)) OPEN_CASES.delete(id);
    else OPEN_CASES.add(id);
    renderCases();
  };

  window.loadMoreCases = function () {
    CASES_LIMIT += 50;
    renderCases();
  };

  window.renderCases = function () {
    if (!DEV_DATA) return;
    const q = (document.getElementById("caseSearch").value || "").trim().toLowerCase();
    const yr = document.getElementById("caseYear").value;
    const mem = document.getElementById("caseMember").value;
    const vcast = document.getElementById("caseVoteCast").value;
    const outc = document.getElementById("caseOutcome").value;
    const pc = document.getElementById("casePC").value;
    const tier = document.getElementById("caseTier").value;
    const prof = document.getElementById("caseProfferFilter").value;
    const contestedOnly = document.getElementById("caseContestedOnly").checked;

    const filtered = (DEV_DATA.cases || []).filter(c => {
      if (yr && String(c.year) !== yr) return false;
      if (outc && c.outcome !== outc) return false;
      if (pc && c.pc_rec !== pc) return false;
      if (tier && c.tier !== tier) return false;
      if (contestedOnly && !c.is_contested) return false;
      if (mem) {
        if (!c.mv || !c.mv[mem]) return false;
        if (vcast && c.mv[mem] !== vcast) return false;
      } else if (vcast) {
        const vals = Object.values(c.mv || {});
        if (!vals.includes(vcast)) return false;
      }
      if (prof) {
        if (prof === "staff_consistent" && c.staff_con !== "Consistent") return false;
        else if (prof === "staff_inconsistent" && c.staff_con !== "Inconsistent") return false;
        else if (!["staff_consistent", "staff_inconsistent"].includes(prof) && !caseMatchesCriterion(c, prof)) return false;
      }
      if (q && !(c.q || "").includes(q)) return false;
      return true;
    });

    document.getElementById("caseCountLine").textContent =
      `Showing ${Math.min(filtered.length, CASES_LIMIT)} of ${filtered.length} matching development cases (click any case to view full proffers & supporting OnBase PDFs)`;

    const shown = filtered.slice(0, CASES_LIMIT);
    const listEl = document.getElementById("casesList");

    if (!shown.length) {
      listEl.innerHTML = `<div class="card-box empty-msg">No development cases match the current filters.</div>`;
      document.getElementById("casesMoreWrap").innerHTML = "";
      return;
    }

    listEl.innerHTML = shown.map(c => {
      const open = OPEN_CASES.has(c.id);
      const pills = [];
      if (c.case_num) pills.push(`<span class="p-pill info">${esc(c.case_num)}</span>`);
      if (c.outcome) {
        const cls = c.outcome === "Denied" ? "bad" : (c.is_contested ? "warn" : "");
        pills.push(`<span class="p-pill ${cls}">Council: ${esc(c.outcome)}${c.tally ? " (" + esc(c.tally) + ")" : ""}</span>`);
      }
      if (c.pc_rec) {
        pills.push(`<span class="p-pill ${c.pc_rec === "Denial" ? "bad" : "info"}">PC: ${esc(c.pc_rec)}${c.pc_tally ? " (" + esc(c.pc_tally) + ")" : ""}</span>`);
      }
      if (c.has_aff) {
        let al = "Affordable Proffer";
        if (c.aff_pct) al = `${c.aff_pct}% Afford.`;
        else if (c.aff_units) al = `${c.aff_units} Afford. Units`;
        if (c.aff_ami) al += ` @ ${c.aff_ami}% AMI`;
        pills.push(`<span class="p-pill">${esc(al)}</span>`);
      }
      if (c.dps_usd) pills.push(`<span class="p-pill">DPS $${Number(c.dps_usd).toLocaleString()}</span>`);
      if (c.post_pc) pills.push(`<span class="p-pill warn">Post-PC Proffers Added</span>`);
      if (c.has_env || c.has_storm) pills.push(`<span class="p-pill">Env/Stormwater</span>`);
      if (c.has_transit) pills.push(`<span class="p-pill">Transit/Sidewalk</span>`);
      if (c.units) pills.push(`<span class="p-pill info">${c.units} units</span>`);
      if (c.acres) pills.push(`<span class="p-pill info">${c.acres} ac</span>`);
      if (mem && c.mv && c.mv[mem]) {
        pills.push(`<span class="p-pill ${c.mv[mem] === "NAY" ? "bad" : ""}">${esc(mem)}: ${c.mv[mem]}</span>`);
      }

      let detHtml = "";
      if (open) {
        const profferLis = (c.proffers || []).map(p => `<li style="margin:3px 0;font-size:12px;color:#cbd5e1;">${esc(p)}</li>`).join("");
        const docsHtml = (c.docs || []).map(d =>
          `<a class="doc-link" href="${esc(d.u)}" target="_blank" rel="noopener"><span class="doc-cat">${esc(d.c)}</span>${esc(d.t)}</a>`
        ).join("");
        const ayesStr = (c.ayes || []).join(", ");
        const naysStr = (c.nays || []).join(", ");
        detHtml = `
          <div class="case-details">
            <div class="spec-grid">
              <div class="spec-item"><div class="spec-lbl">Zoning Change</div><div>${esc(c.ez || "—")} &rarr; <strong>${esc(c.pz || "—")}</strong></div></div>
              <div class="spec-item"><div class="spec-lbl">Tier / Place Type</div><div>${esc(c.tier || "—")}${c.place_type ? " &bull; " + esc(c.place_type) : ""}</div></div>
              <div class="spec-item"><div class="spec-lbl">Applicant / Firm</div><div>${esc(c.applicant || "—")}${c.firm ? " (" + esc(c.firm) + ")" : ""}</div></div>
              <div class="spec-item"><div class="spec-lbl">Staff Comp Plan</div><div>${esc(c.staff_con || "—")}${c.watershed ? " &bull; " + esc(c.watershed) : ""}</div></div>
            </div>
            ${ayesStr || naysStr ? `
              <div style="margin-bottom:10px;padding:8px 11px;border-radius:8px;background:rgba(15,23,42,0.7);border:1px solid var(--border);font-size:12px;">
                ${ayesStr ? `<div style="color:#6ee7b7;"><strong>Ayes:</strong> ${esc(ayesStr)}</div>` : ""}
                ${naysStr ? `<div style="color:#fca5a5;margin-top:2px;"><strong>Nays:</strong> ${esc(naysStr)}</div>` : ""}
              </div>
            ` : ""}
            ${profferLis ? `
              <div style="margin-bottom:10px;">
                <div style="font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;color:#6ee7b7;margin-bottom:4px;">Extracted Proffers &amp; Commitments Exceeding UDO</div>
                <ul style="padding-left:18px;">${profferLis}</ul>
              </div>
            ` : ""}
            <div>
              <div style="font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;color:#7dd3fc;margin-bottom:4px;">Official Supporting Documents (${(c.docs || []).length})</div>
              <div class="doc-list">
                ${c.onbase_url ? `<a class="doc-link" style="border-color:var(--city);color:#6ee7b7;" href="${esc(c.onbase_url)}" target="_blank" rel="noopener">&#128279; Open OnBase Agenda</a>` : ""}
                ${c.pdf_url ? `<a class="doc-link" style="border-color:#dc2626;color:#fca5a5;" href="${esc(c.pdf_url)}" target="_blank" rel="noopener">&#128196; Meeting Executive Summary PDF</a>` : ""}
                ${docsHtml}
              </div>
            </div>
          </div>
        `;
      }

      return `
        <article class="case-card">
          <div class="case-hdr" onclick="toggleCaseCard(${c.id})">
            <div>
              <div class="case-title">${open ? "&#9662;" : "&#9656;"} ${esc(c.name)}</div>
              <div class="case-meta">${esc(c.date || "")} &bull; ${esc(c.type || "")}${c.pr ? " &bull; PR# " + esc(c.pr) : ""} &bull; ${(c.docs || []).length} supporting docs</div>
            </div>
          </div>
          <div class="proffer-pills">${pills.join("")}</div>
          ${detHtml}
        </article>
      `;
    }).join("");

    const moreEl = document.getElementById("casesMoreWrap");
    if (filtered.length > CASES_LIMIT) {
      moreEl.innerHTML = `<button class="nav-btn" onclick="loadMoreCases()">Load More (${filtered.length - CASES_LIMIT} remaining)</button>`;
    } else {
      moreEl.innerHTML = "";
    }
  };
})();
