import json
import re

def update_beta_html():
    with open('/home/rann/src/elections/2026 analysis/beta/index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Load CD data
    with open('/home/rann/src/elections/2026 analysis/nc_cd_data.json', 'r', encoding='utf-8') as f:
        cd_data = json.load(f)

    county_to_cd = {}
    for cd_id, info in cd_data.items():
        for cb in info['county_breakdown']:
            c_name = cb['county'].upper()
            if c_name not in county_to_cd or cb['ev_voters_in_cd'] > county_to_cd[c_name]['ev_voters']:
                county_to_cd[c_name] = {
                    'primary_cd': cd_id,
                    'ev_voters': cb['ev_voters_in_cd'],
                    'is_split': cb['is_split']
                }

    full_cd_bundle = {
        'districts': cd_data,
        'county_to_cd': {k: v['primary_cd'] for k, v in county_to_cd.items()},
        'county_splits': {k: v['is_split'] for k, v in county_to_cd.items()}
    }

    # Embed window.NC_CD_DATA right before window.NC_MAP_DATA or after
    cd_script = f"""  <!-- Embedded Congressional District (CD) Model Data -->
  <script>
    window.NC_CD_DATA = {json.dumps(full_cd_bundle)};
  </script>
"""
    if 'window.NC_CD_DATA =' not in html:
        target = '<!-- Main Application Logic -->'
        html = html.replace(target, cd_script + '\n  ' + target)

    # 2. Add CD mode button to the display mode group
    btn_cd_html = """          <button id="btnModeCD" onclick="setMapMode('cd')" class="px-2.5 py-1 rounded-md text-xs font-semibold text-purple-300 hover:text-white transition flex items-center gap-1.5 border border-purple-500/30 bg-purple-950/30">
            <span class="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
            CD Mode
          </button>"""
    if 'id="btnModeCD"' not in html:
        target_btn = '<button id="btnModeEditorial"'
        html = html.replace(target_btn, btn_cd_html + '\n          ' + target_btn)

    # 3. Add CD dropdown selector next to countySelector
    cd_selector_html = """        <!-- CD Mode Selector Dropdown -->
        <div id="cdSelectorGroup" class="hidden items-center gap-1.5">
          <select id="cdSelector" onchange="selectCongressionalDistrict(this.value)" class="bg-purple-950/70 border border-purple-500/60 text-purple-200 text-xs rounded-lg px-2.5 py-1.5 focus:ring-2 focus:ring-purple-500 focus:outline-none font-semibold">
            <option value="">All Congressional Districts (14 CDs)...</option>
            <option value="NC-01">NC-01 &bull; Northeast NC (Safe R -10.7%)</option>
            <option value="NC-02">NC-02 &bull; Wake County (Safe D +34.7%)</option>
            <option value="NC-03">NC-03 &bull; Coastal Plain (Safe R -5.9%)</option>
            <option value="NC-04">NC-04 &bull; Research Triangle (Safe D +50.5%)</option>
            <option value="NC-05">NC-05 &bull; NW Piedmont (Safe R -14.2%)</option>
            <option value="NC-06">NC-06 &bull; Central Piedmont (Safe R -5.8%)</option>
            <option value="NC-07">NC-07 &bull; Cape Fear / SE (Likely R -3.0%)</option>
            <option value="NC-08">NC-08 &bull; Sandhills / SC (Likely R -2.7%)</option>
            <option value="NC-09">NC-09 &bull; Central Sandhills (Likely R -3.4%)</option>
            <option value="NC-10">NC-10 &bull; Piedmont Foothills (Safe R -11.8%)</option>
            <option value="NC-11">NC-11 &bull; Western Mountains (Lean R -1.7%)</option>
            <option value="NC-12">NC-12 &bull; Mecklenburg / Charlotte (Safe D +47.6%)</option>
            <option value="NC-13">NC-13 &bull; Triangle Exurbs (Lean D +1.7%)</option>
            <option value="NC-14">NC-14 &bull; SW Charlotte Foothills (Likely D +3.4%)</option>
          </select>
        </div>"""
    if 'id="cdSelectorGroup"' not in html:
        target_group = '<!-- 5. Arrow Prominence Controls -->'
        html = html.replace(target_group, cd_selector_html + '\n\n        ' + target_group)

    # 4. Inject JavaScript support for CD Mode
    js_vars = "let selectedCDId = null;\n"
    if 'let selectedCDId =' not in html:
        html = html.replace("let currentMapMode = 'swing';", "let currentMapMode = 'swing';\n    let selectedCDId = null;")

    # In getEntityFill, add CD Mode logic
    cd_fill_logic = """      if (currentMapMode === 'cd') {
        const cdData = window.NC_CD_DATA;
        if (!cdData || !entity) return '#1e293b';
        const cName = (entity.name || entity.id || '').toUpperCase();
        const cdId = cdData.county_to_cd[cName];
        if (!cdId) return '#334155';

        // If a specific CD is selected, dim counties outside of it
        if (selectedCDId && cdId !== selectedCDId) {
          return '#0f172a'; // Dimmed background
        }

        const dist = cdData.districts[cdId];
        if (!dist) return '#334155';
        const m = dist.pred_margin;
        const absM = Math.abs(m);
        if (m > 0) {
          if (absM > 35) return '#172554'; // Deep Solid Dem
          if (absM > 20) return '#1e40af'; // Solid Dem
          if (absM > 10) return '#2563eb'; // Likely Dem
          if (absM > 5)  return '#3b82f6'; // Lean Dem
          return '#60a5fa'; // Tilt Dem (<5% margin)
        } else {
          if (absM > 35) return '#7f1d1d'; // Deep Solid Rep
          if (absM > 20) return '#991b1b'; // Solid Rep
          if (absM > 10) return '#dc2626'; // Likely Rep
          if (absM > 5)  return '#ef4444'; // Lean Rep
          return '#f87171'; // Tilt Rep (<5% margin)
        }
      }
"""
    if "if (currentMapMode === 'cd')" not in html:
        html = html.replace("function getEntityFill(m, entity) {", "function getEntityFill(m, entity) {\n" + cd_fill_logic)

    # In renderCounties: apply outline stroke when selectedCDId is active
    cd_render_county = """        if (currentMapMode === 'cd' && selectedCDId) {
          const cdData = window.NC_CD_DATA;
          const cName = (county.name || county.id || '').toUpperCase();
          const cdId = cdData && cdData.county_to_cd[cName];
          if (cdId === selectedCDId) {
            path.setAttribute('stroke', '#c084fc');
            path.setAttribute('stroke-width', '2.0');
            path.style.opacity = '1.0';
          } else {
            path.setAttribute('stroke', '#1e293b');
            path.setAttribute('stroke-width', '0.5');
            path.style.opacity = '0.30';
          }
        }
"""
    if "if (currentMapMode === 'cd' && selectedCDId)" not in html:
        html = html.replace("countiesGroup.appendChild(path);", cd_render_county + "        countiesGroup.appendChild(path);")

    # In onCountyClick: if in CD Mode, select the county's CD!
    if "if (currentMapMode === 'cd')" not in html:
        html = html.replace("path.addEventListener('click', () => zoomToCounty(county.id));",
                            """path.addEventListener('click', () => {
          if (currentMapMode === 'cd') {
            const cdData = window.NC_CD_DATA;
            const cName = (county.name || county.id || '').toUpperCase();
            const cdId = cdData && cdData.county_to_cd[cName];
            if (cdId) selectCongressionalDistrict(cdId);
          } else {
            zoomToCounty(county.id);
          }
        });""")

    # Suppress arrows in CD Mode
    if "currentMapMode === 'cd'" not in html:
        html = html.replace("if (!showArrows || activeCountyId || currentMapMode === 'forecast') return;",
                            "if (!showArrows || activeCountyId || currentMapMode === 'forecast' || currentMapMode === 'cd') return;")

    # In setMapMode: handle 'CD'
    html = html.replace("['Swing', 'Margin', 'Forecast', 'Editorial'].forEach(m => {",
                        "['Swing', 'Margin', 'Forecast', 'Editorial', 'CD'].forEach(m => {")
    
    cd_mode_toggle = """      const cdGroup = document.getElementById('cdSelectorGroup');
      if (cdGroup) {
        if (mode === 'cd') {
          cdGroup.classList.remove('hidden');
          cdGroup.classList.add('flex');
        } else {
          cdGroup.classList.remove('flex');
          cdGroup.classList.add('hidden');
        }
      }
      if (mode === 'cd') {
        renderCDInspector(selectedCDId);
      }
"""
    if "const cdGroup = document.getElementById('cdSelectorGroup');" not in html:
        html = html.replace("updateLegendUI();", cd_mode_toggle + "      updateLegendUI();")

    # Add selectCongressionalDistrict & renderCDInspector functions
    cd_functions = """
    // ==========================================
    // CONGRESSIONAL DISTRICT (CD) MODE ENGINE
    // ==========================================
    function selectCongressionalDistrict(cdId) {
      selectedCDId = cdId || null;
      const selector = document.getElementById('cdSelector');
      if (selector) selector.value = selectedCDId || '';

      if (currentMapMode !== 'cd') {
        setMapMode('cd');
        return;
      }

      renderCounties();
      renderCDInspector(selectedCDId);
      updateLegendUI();
    }

    function renderCDInspector(cdId) {
      const card = document.getElementById('inspectorCard');
      const cdData = window.NC_CD_DATA;
      if (!card || !cdData) return;

      const subTitle = document.getElementById('cardSubtitle');
      const mainTitle = document.getElementById('cardTitle');
      const badge = document.getElementById('cardBadge');
      const forecastSec = document.getElementById('forecastSection');
      if (forecastSec) forecastSec.classList.add('hidden');

      if (!cdId) {
        // Statewide CD Overview / Leaderboard
        if (subTitle) subTitle.textContent = 'North Carolina Congressional Map';
        if (mainTitle) mainTitle.innerHTML = 'All 14 Congressional Districts <span class=\"text-xs font-normal text-purple-300 font-mono\">[2026 Model]</span>';
        if (badge) {
          badge.className = 'px-3 py-1 rounded-full text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 font-mono shadow-sm';
          badge.innerHTML = '14 CDs &bull; 5 D / 9 R';
        }

        // Summary metric tiles
        document.getElementById('metricTitleYearA').textContent = 'Projected Dem Seats';
        document.getElementById('metricTotA').innerHTML = '<span class=\"text-blue-400\">5 Districts</span>';
        document.getElementById('metricTurnoutGrowth').innerHTML = '<span class=\"text-slate-400 font-normal\">NC-02, 04, 12, 13, 14</span>';

        document.getElementById('metricTitleYearB').textContent = 'Projected Rep Seats';
        document.getElementById('metricTotB').innerHTML = '<span class=\"text-red-400\">9 Districts</span>';
        document.getElementById('metricDaySubtitle').innerHTML = '<span class=\"text-slate-400 font-normal\">NC-01, 03, 05, 06, 07, 08, 09, 10, 11</span>';

        document.getElementById('shareBarTitle').textContent = 'Delegation Balance Projection';
        document.getElementById('metricMarginVal').textContent = 'R +4 Net Seat Advantage';
        document.getElementById('metricMarginVal').className = 'font-bold text-purple-300 font-mono';

        const seg1 = document.getElementById('barSegment1');
        const seg2 = document.getElementById('barSegment2');
        const seg3 = document.getElementById('barSegment3');
        if (seg1) { seg1.style.width = '35.7%'; seg1.className = 'bg-blue-600 transition-all'; } // 5 of 14
        if (seg3) { seg3.style.width = '0%'; }
        if (seg2) { seg2.style.width = '64.3%'; seg2.className = 'bg-red-600 transition-all'; }  // 9 of 14

        const barLabels = document.getElementById('shareBarLabels');
        if (barLabels) {
          barLabels.innerHTML = '<span>5 Dem Seats (35.7%)</span><span class=\"text-purple-300 font-bold\">6 Battlegrounds (&plusmn;5%)</span><span>9 Rep Seats (64.3%)</span>';
        }

        document.getElementById('tblMetricHeader').textContent = 'District Leaderboard (Click row to inspect)';
        document.getElementById('tblHeadA').textContent = 'Margin';
        document.getElementById('tblHeadB').textContent = 'Rating';
        const tblHeadDiff = document.getElementById('tblHeadDiff');
        if (tblHeadDiff) tblHeadDiff.textContent = 'Win Prob';

        let rowsHtml = '';
        Object.keys(cdData.districts).sort().forEach(id => {
          const d = cdData.districts[id];
          const isDem = d.pred_margin > 0;
          const colorClass = isDem ? 'text-blue-400' : 'text-red-400';
          const badgeClass = isDem ? 'bg-blue-500/20 text-blue-300 border-blue-500/30' : 'bg-red-500/20 text-red-300 border-red-500/30';
          const probStr = isDem ? `${d.p_dem}% D` : `${d.p_rep}% R`;
          const marginStr = `${isDem ? '+' : ''}${d.pred_margin.toFixed(1)}%`;

          rowsHtml += `
            <div onclick=\"selectCongressionalDistrict('${id}')\" class=\"flex items-center justify-between p-2 rounded-lg bg-slate-900/60 hover:bg-purple-950/40 border border-slate-800 hover:border-purple-500/50 cursor-pointer transition text-xs\">
              <div class=\"flex items-center gap-2\">
                <span class=\"font-bold font-mono text-purple-300 w-12\">${id}</span>
                <span class=\"text-[11px] text-slate-300 truncate max-w-[170px]\" title=\"${d.region}\">${d.region}</span>
              </div>
              <div class=\"flex items-center gap-3 font-mono\">
                <span class=\"w-16 text-right font-bold ${colorClass}\">${marginStr}</span>
                <span class=\"text-[10px] px-1.5 py-0.5 rounded border ${badgeClass}\">${d.rating}</span>
                <span class=\"w-16 text-right text-[11px] text-slate-400\">${probStr}</span>
              </div>
            </div>
          `;
        });

        const rowsContainer = document.getElementById('tableRowsContainer');
        if (rowsContainer) rowsContainer.innerHTML = rowsHtml;

      } else {
        // Individual CD Scorecard
        const d = cdData.districts[cdId];
        if (!d) return;

        const isDem = d.pred_margin > 0;
        const colorClass = isDem ? 'text-blue-400' : 'text-red-400';
        const badgeClass = isDem ? 'bg-blue-500/20 text-blue-300 border-blue-500/30' : 'bg-red-500/20 text-red-300 border-red-500/30';

        if (subTitle) {
          subTitle.innerHTML = `<span class=\"cursor-pointer hover:underline text-purple-300\" onclick=\"selectCongressionalDistrict('')\">&larr; All 14 Districts</span> &bull; ${d.name}`;
        }
        if (mainTitle) {
          mainTitle.innerHTML = `${d.id}: ${d.region}`;
        }
        if (badge) {
          badge.className = `px-3 py-1 rounded-full text-xs font-bold border font-mono shadow-sm ${badgeClass}`;
          badge.innerHTML = `${d.rating} &bull; ${d.p_dem > d.p_rep ? d.p_dem + '% D' : d.p_rep + '% R'} Win Prob`;
        }

        document.getElementById('metricTitleYearA').textContent = 'Projected Final Turnout';
        document.getElementById('metricTotA').innerHTML = `${d.proj_turnout.toLocaleString()} <span class=\"text-xs font-normal text-slate-400\">votes</span>`;
        document.getElementById('metricTurnoutGrowth').innerHTML = `<span class=\"text-purple-300 font-semibold\">Day 7 EV: ${d.ev_day7_total.toLocaleString()} ballots</span>`;

        document.getElementById('metricTitleYearB').textContent = 'Projected Margin';
        const netStr = `${d.net_margin_votes > 0 ? '+' : ''}${d.net_margin_votes.toLocaleString()} net`;
        document.getElementById('metricTotB').innerHTML = `<span class=\"${colorClass}\">${d.pred_margin > 0 ? '+' : ''}${d.pred_margin.toFixed(1)}%</span>`;
        document.getElementById('metricDaySubtitle').innerHTML = `<span class=\"font-mono ${colorClass}\">${netStr}</span>`;

        document.getElementById('shareBarTitle').textContent = 'Projected Vote Share';
        document.getElementById('metricMarginVal').textContent = `${d.pred_final_dem.toFixed(1)}% D vs ${d.pred_final_rep.toFixed(1)}% R`;
        document.getElementById('metricMarginVal').className = `font-bold ${colorClass} font-mono`;

        const seg1 = document.getElementById('barSegment1');
        const seg2 = document.getElementById('barSegment2');
        const seg3 = document.getElementById('barSegment3');
        if (seg1) { seg1.style.width = `${d.pred_final_dem}%`; seg1.className = 'bg-blue-600 transition-all'; }
        if (seg3) { seg3.style.width = '0%'; }
        if (seg2) { seg2.style.width = `${d.pred_final_rep}%`; seg2.className = 'bg-red-600 transition-all'; }

        const barLabels = document.getElementById('shareBarLabels');
        if (barLabels) {
          barLabels.innerHTML = `<span>Dem: ${d.pred_final_dem.toFixed(1)}%</span><span class=\"text-slate-400 text-[10px]\">95% CI: ${d.ci_margin_low > 0 ? '+' : ''}${d.ci_margin_low.toFixed(1)}% to ${d.ci_margin_high > 0 ? '+' : ''}${d.ci_margin_high.toFixed(1)}%</span><span>Rep: ${d.pred_final_rep.toFixed(1)}%</span>`;
        }

        document.getElementById('tblMetricHeader').textContent = `Component Counties in ${d.id} (${d.county_breakdown.length} total)`;
        document.getElementById('tblHeadA').textContent = 'EV Share';
        document.getElementById('tblHeadB').textContent = 'Margin';
        const tblHeadDiff = document.getElementById('tblHeadDiff');
        if (tblHeadDiff) tblHeadDiff.textContent = 'Rating';

        let rowsHtml = '';
        d.county_breakdown.forEach(cb => {
          const cIsDem = cb.margin_pct > 0;
          const cColor = cIsDem ? 'text-blue-400' : 'text-red-400';
          const splitBadge = cb.is_split ? `<span class=\"text-[9px] bg-slate-800 text-slate-400 px-1 rounded\" title=\"County split across multiple CDs\">Split (${cb.county_frac_in_cd}%)</span>` : '';

          rowsHtml += `
            <div class=\"flex items-center justify-between p-2 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs\">
              <div class=\"flex items-center gap-1.5\">
                <span class=\"font-medium text-white\">${cb.county}</span>
                ${splitBadge}
              </div>
              <div class=\"flex items-center gap-3 font-mono\">
                <span class=\"w-14 text-right text-slate-400 text-[11px]\">${cb.ev_share_in_cd}%</span>
                <span class=\"w-14 text-right font-bold ${cColor}\">${cb.margin_pct > 0 ? '+' : ''}${cb.margin_pct.toFixed(1)}%</span>
                <span class=\"w-16 text-right text-[10px] text-slate-300\">${cb.rating}</span>
              </div>
            </div>
          `;
        });

        const rowsContainer = document.getElementById('tableRowsContainer');
        if (rowsContainer) rowsContainer.innerHTML = rowsHtml;
      }
    }
"""

    if 'function selectCongressionalDistrict' not in html:
        html += cd_functions

    # In updateLegendUI:
    cd_legend = """      if (currentMapMode === 'cd') {
        if (title) title.textContent = 'Congressional Districts';
        if (subtitle) subtitle.textContent = selectedCDId ? `${selectedCDId} (${window.NC_CD_DATA.districts[selectedCDId].region})` : '14 Districts Model';
        if (rowPos) rowPos.style.color = '#3b82f6';
        if (rowNeg) rowNeg.style.color = '#ef4444';
        if (iconPos) iconPos.innerHTML = '&#9632;';
        if (iconNeg) iconNeg.innerHTML = '&#9632;';
        if (labelPos) labelPos.textContent = 'Projected Dem Lead (5 Seats)';
        if (labelNeg) labelNeg.textContent = 'Projected Rep Lead (9 Seats)';
        if (note) note.textContent = 'Counties shaded by their Congressional District model outcome. Click any district row or county to inspect component margins.';
        return;
      }
"""
    if "if (currentMapMode === 'cd') {" not in html:
        html = html.replace("if (currentMapMode === 'forecast') {", cd_legend + "      if (currentMapMode === 'forecast') {")

    with open('/home/rann/src/elections/2026 analysis/beta/index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print('Successfully updated /home/rann/src/elections/2026 analysis/beta/index.html with CD Mode!')

if __name__ == '__main__':
    update_beta_html()

