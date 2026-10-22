import json, re

print("Starting apply_legislative_modes.py...")

with open('/home/rann/src/elections/2026 analysis/nc_senate_data.json', 'r') as f:
    senate_data = json.load(f)

with open('/home/rann/src/elections/2026 analysis/nc_house_data.json', 'r') as f:
    house_data = json.load(f)

with open('/home/rann/src/elections/2026 analysis/beta/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update Mode Buttons
old_cd_btn = """                    <button id="btnModeCD" onclick="setMapMode('cd')" class="px-2.5 py-1 rounded-md text-xs font-semibold text-purple-300 hover:text-white transition flex items-center gap-1.5 border border-purple-500/30 bg-purple-950/30">
            <span class="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
            Congressional Districts Mode
          </button>"""

if old_cd_btn in html:
    new_buttons = """          <button id="btnModeCD" onclick="setMapMode('cd')" class="px-2 py-1 rounded-md text-xs font-semibold text-purple-300 hover:text-white transition flex items-center gap-1 border border-purple-500/30 bg-purple-950/30">
            <span class="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
            US House
          </button>
          <button id="btnModeSenate" onclick="setMapMode('senate')" class="px-2 py-1 rounded-md text-xs font-semibold text-emerald-300 hover:text-white transition flex items-center gap-1 border border-emerald-500/30 bg-emerald-950/30">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            NC Senate
          </button>
          <button id="btnModeHouse" onclick="setMapMode('house')" class="px-2 py-1 rounded-md text-xs font-semibold text-amber-300 hover:text-white transition flex items-center gap-1 border border-amber-500/30 bg-amber-950/30">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            NC House
          </button>"""
    html = html.replace(old_cd_btn, new_buttons)
    print("Updated mode buttons in navigation bar.")
else:
    print("Warning: old_cd_btn pattern not found directly, checking fallback...")

# 2. Add Senate & House Dropdown Selectors
senate_options = ['<option value="">All NC Senate Districts (50 Districts)...</option>']
for s_id in sorted(senate_data.keys(), key=lambda x: senate_data[x]['number']):
    d = senate_data[s_id]
    m_str = d['projected_margin_str']
    reg = d['region'][:25]
    senate_options.append(f'<option value="{s_id}">{s_id} &bull; {reg} &bull; {m_str}</option>')

house_options = ['<option value="">All NC House Districts (120 Districts)...</option>']
for h_id in sorted(house_data.keys(), key=lambda x: house_data[x]['number']):
    d = house_data[h_id]
    m_str = d['projected_margin_str']
    reg = d['region'][:25]
    house_options.append(f'<option value="{h_id}">{h_id} &bull; {reg} &bull; {m_str}</option>')

senate_selector_html = f"""        <!-- NC Senate Mode Selector Dropdown -->
        <div id="senateSelectorGroup" class="hidden items-center gap-1.5">
          <select id="senateSelector" onchange="selectSenateDistrict(this.value)" class="bg-emerald-950/80 border border-emerald-500/60 text-emerald-200 text-xs rounded-lg px-2.5 py-1.5 focus:ring-2 focus:ring-emerald-500 focus:outline-none font-semibold max-w-[280px]">
            {"".join(senate_options)}
          </select>
        </div>

        <!-- NC House Mode Selector Dropdown -->
        <div id="houseSelectorGroup" class="hidden items-center gap-1.5">
          <select id="houseSelector" onchange="selectHouseDistrict(this.value)" class="bg-amber-950/80 border border-amber-500/60 text-amber-200 text-xs rounded-lg px-2.5 py-1.5 focus:ring-2 focus:ring-amber-500 focus:outline-none font-semibold max-w-[280px]">
            {"".join(house_options)}
          </select>
        </div>"""

if 'id="senateSelectorGroup"' not in html:
    target_pos = '</div>\n\n        <!-- 5. Arrow Prominence Controls -->'
    html = html.replace(target_pos, '</div>\n\n' + senate_selector_html + '\n\n        <!-- 5. Arrow Prominence Controls -->')
    print("Added senateSelectorGroup and houseSelectorGroup dropdowns.")

# 3. Add SVG Layers for Senate and House
svg_layers = """          <g id="senateLayer" class="hidden"></g>
          <g id="senateLabelsLayer" class="hidden pointer-events-none"></g>
          <g id="houseLayer" class="hidden"></g>
          <g id="houseLabelsLayer" class="hidden pointer-events-none"></g>"""

if 'id="senateLayer"' not in html:
    target_layer = '<g id="cdLabelsLayer" class="hidden pointer-events-none"></g>'
    html = html.replace(target_layer, target_layer + '\n' + svg_layers)
    print("Added senateLayer and houseLayer SVG groups.")

# 4. Embed window.NC_SENATE_DATA and window.NC_HOUSE_DATA
senate_json = json.dumps(senate_data)
house_json = json.dumps(house_data)
data_embed = f"""    window.NC_SENATE_DATA = {{"districts": {senate_json}}};\n    window.NC_HOUSE_DATA = {{"districts": {house_json}}};\n"""

if 'window.NC_SENATE_DATA =' not in html:
    # Insert right after window.NC_CD_DATA
    m = re.search(r'window\.NC_CD_DATA\s*=\s*\{.*?\};\n', html)
    if m:
        html = html[:m.end()] + data_embed + html[m.end():]
        print("Embedded window.NC_SENATE_DATA and window.NC_HOUSE_DATA.")
    else:
        print("Error: Could not find window.NC_CD_DATA insertion point.")

# 5. Add JS variables
if 'let selectedSenateId =' not in html:
    html = html.replace('let selectedCDId = null;', 'let selectedCDId = null;\n    let selectedSenateId = null;\n    let selectedHouseId = null;')
    print("Added selectedSenateId and selectedHouseId variables.")

# 6. Update resetToStateView
old_reset = """      if (currentMapMode === 'cd') {
        selectCongressionalDistrict(null);
        return;
      }"""
new_reset = """      if (currentMapMode === 'cd') {
        selectCongressionalDistrict(null);
        return;
      }
      if (currentMapMode === 'senate') {
        selectSenateDistrict(null);
        return;
      }
      if (currentMapMode === 'house') {
        selectHouseDistrict(null);
        return;
      }"""
if old_reset in html:
    html = html.replace(old_reset, new_reset)
    print("Updated resetToStateView.")

# 7. Update setMapMode(mode)
old_mode_logic = """      const cdSelectorGroup = document.getElementById('cdSelectorGroup');
      const cdLayer = document.getElementById('cdLayer');
      const cdLabelsLayer = document.getElementById('cdLabelsLayer');

      if (mode === 'cd') {
        if (cdSelectorGroup) { cdSelectorGroup.classList.remove('hidden'); cdSelectorGroup.classList.add('flex'); }
        countiesGroup.classList.add('hidden');
        arrowsGroup.classList.add('hidden');
        precinctsGroup.classList.add('hidden');
        if (cdLayer) cdLayer.classList.remove('hidden');
        if (cdLabelsLayer) cdLabelsLayer.classList.remove('hidden');

        activeViewLabel.textContent = selectedCDId ? `${selectedCDId} - ${window.NC_CD_DATA.districts[selectedCDId].projected_margin_str}` : 'Congressional Districts Mode (14 Districts)';
        mapHintText.textContent = 'Click any Congressional District to view candidate matchup and component counties';

        renderCongressionalDistricts();
        renderCDInspector(selectedCDId);
      } else {
        if (cdSelectorGroup) { cdSelectorGroup.classList.remove('flex'); cdSelectorGroup.classList.add('hidden'); }
        if (cdLayer) cdLayer.classList.add('hidden');
        if (cdLabelsLayer) cdLabelsLayer.classList.add('hidden');
        countiesGroup.classList.remove('hidden');

        if (!activeCountyId) {
          activeViewLabel.textContent = 'Statewide (100 Counties)';
          mapHintText.textContent = 'Click any county to inspect precinct swing and turnout';
        } else {
          activeViewLabel.textContent = `${activeCountyId} County (${DATA.precincts[activeCountyId]?.length || 0} Precincts)`;
          mapHintText.textContent = 'Click precincts to inspect local vote shift';
        }
        refreshEntireVisualization();
      }"""

new_mode_logic = """      const cdSelectorGroup = document.getElementById('cdSelectorGroup');
      const senateSelectorGroup = document.getElementById('senateSelectorGroup');
      const houseSelectorGroup = document.getElementById('houseSelectorGroup');
      const cdLayer = document.getElementById('cdLayer');
      const cdLabelsLayer = document.getElementById('cdLabelsLayer');
      const senateLayer = document.getElementById('senateLayer');
      const senateLabelsLayer = document.getElementById('senateLabelsLayer');
      const houseLayer = document.getElementById('houseLayer');
      const houseLabelsLayer = document.getElementById('houseLabelsLayer');

      // Hide all district layers by default
      if (cdSelectorGroup) { cdSelectorGroup.classList.remove('flex'); cdSelectorGroup.classList.add('hidden'); }
      if (senateSelectorGroup) { senateSelectorGroup.classList.remove('flex'); senateSelectorGroup.classList.add('hidden'); }
      if (houseSelectorGroup) { houseSelectorGroup.classList.remove('flex'); houseSelectorGroup.classList.add('hidden'); }
      if (cdLayer) cdLayer.classList.add('hidden');
      if (cdLabelsLayer) cdLabelsLayer.classList.add('hidden');
      if (senateLayer) senateLayer.classList.add('hidden');
      if (senateLabelsLayer) senateLabelsLayer.classList.add('hidden');
      if (houseLayer) houseLayer.classList.add('hidden');
      if (houseLabelsLayer) houseLabelsLayer.classList.add('hidden');

      if (mode === 'cd') {
        if (cdSelectorGroup) { cdSelectorGroup.classList.remove('hidden'); cdSelectorGroup.classList.add('flex'); }
        countiesGroup.classList.add('hidden');
        arrowsGroup.classList.add('hidden');
        precinctsGroup.classList.add('hidden');
        if (cdLayer) cdLayer.classList.remove('hidden');
        if (cdLabelsLayer) cdLabelsLayer.classList.remove('hidden');

        activeViewLabel.textContent = selectedCDId ? `${selectedCDId} - ${window.NC_CD_DATA.districts[selectedCDId].projected_margin_str}` : 'Congressional Districts Mode (14 Districts)';
        mapHintText.textContent = 'Click any Congressional District to view candidate matchup and component counties';

        renderCongressionalDistricts();
        renderCDInspector(selectedCDId);
      } else if (mode === 'senate') {
        if (senateSelectorGroup) { senateSelectorGroup.classList.remove('hidden'); senateSelectorGroup.classList.add('flex'); }
        countiesGroup.classList.add('hidden');
        arrowsGroup.classList.add('hidden');
        precinctsGroup.classList.add('hidden');
        if (senateLayer) senateLayer.classList.remove('hidden');
        if (senateLabelsLayer) senateLabelsLayer.classList.remove('hidden');

        activeViewLabel.textContent = selectedSenateId ? `${selectedSenateId} - ${window.NC_SENATE_DATA.districts[selectedSenateId].projected_margin_str}` : 'NC Senate Mode (50 Districts)';
        mapHintText.textContent = 'Click any Senate District to view candidates, projected margin, and battleground status';

        renderSenateDistricts();
        renderSenateInspector(selectedSenateId);
      } else if (mode === 'house') {
        if (houseSelectorGroup) { houseSelectorGroup.classList.remove('hidden'); houseSelectorGroup.classList.add('flex'); }
        countiesGroup.classList.add('hidden');
        arrowsGroup.classList.add('hidden');
        precinctsGroup.classList.add('hidden');
        if (houseLayer) houseLayer.classList.remove('hidden');
        if (houseLabelsLayer) houseLabelsLayer.classList.remove('hidden');

        activeViewLabel.textContent = selectedHouseId ? `${selectedHouseId} - ${window.NC_HOUSE_DATA.districts[selectedHouseId].projected_margin_str}` : 'NC House Mode (120 Districts)';
        mapHintText.textContent = 'Click any House District to view candidates, projected margin, and battleground status';

        renderHouseDistricts();
        renderHouseInspector(selectedHouseId);
      } else {
        countiesGroup.classList.remove('hidden');

        if (!activeCountyId) {
          activeViewLabel.textContent = 'Statewide (100 Counties)';
          mapHintText.textContent = 'Click any county to inspect precinct swing and turnout';
        } else {
          activeViewLabel.textContent = `${activeCountyId} County (${DATA.precincts[activeCountyId]?.length || 0} Precincts)`;
          mapHintText.textContent = 'Click precincts to inspect local vote shift';
        }
        refreshEntireVisualization();
      }"""

if old_mode_logic in html:
    html = html.replace(old_mode_logic, new_mode_logic)
    print("Updated setMapMode logic for Senate and House modes.")
else:
    print("Warning: old_mode_logic pattern not matched directly.")

# 8. Update updateLegendUI
old_legend_check = """      if (currentMapMode === 'cd') {
        const title = document.getElementById('legendTitle');
        const subtitle = document.getElementById('legendSubtitle');
        const rowPos = document.getElementById('legendRowPos');
        const rowNeg = document.getElementById('legendRowNeg');
        const labelPos = document.getElementById('legendLabelPos');
        const labelNeg = document.getElementById('legendLabelNeg');
        const note = document.getElementById('legendNote');
        const rowFlip = document.getElementById('legendRowFlip');
        const iconPos = rowPos ? rowPos.querySelector('span:first-child') : null;
        const iconNeg = rowNeg ? rowNeg.querySelector('span:first-child') : null;

        if (rowFlip) rowFlip.style.display = 'flex';
        if (title) title.textContent = 'Congressional Districts Model';
        if (subtitle) subtitle.textContent = '14 Districts (2026 Model)';
        if (rowPos) rowPos.style.color = '#3b82f6';
        if (rowNeg) rowNeg.style.color = '#ef4444';
        if (iconPos) iconPos.innerHTML = '&#9632;';
        if (iconNeg) iconNeg.innerHTML = '&#9632;';
        if (labelPos) labelPos.textContent = 'Dem Advantage (NC-01, 02, 04, 12)';
        if (labelNeg) labelNeg.textContent = 'Rep Advantage (NC-03, 05-11, 13, 14)';
        const labelFlip = document.getElementById('legendLabelFlip');
        if (labelFlip) labelFlip.textContent = 'Predicted Flips: None (all 14 seats projected to hold)';
        if (note) note.textContent = 'Cross-hatching indicates seats projected to change party control. Confidence intervals calculated at 95%.';
        return;
      }"""

new_legend_check = """      if (currentMapMode === 'cd') {
        const title = document.getElementById('legendTitle');
        const subtitle = document.getElementById('legendSubtitle');
        const rowPos = document.getElementById('legendRowPos');
        const rowNeg = document.getElementById('legendRowNeg');
        const labelPos = document.getElementById('legendLabelPos');
        const labelNeg = document.getElementById('legendLabelNeg');
        const note = document.getElementById('legendNote');
        const rowFlip = document.getElementById('legendRowFlip');
        const iconPos = rowPos ? rowPos.querySelector('span:first-child') : null;
        const iconNeg = rowNeg ? rowNeg.querySelector('span:first-child') : null;

        if (rowFlip) rowFlip.style.display = 'flex';
        if (title) title.textContent = 'Congressional Districts Model';
        if (subtitle) subtitle.textContent = '14 Districts (2026 Model)';
        if (rowPos) rowPos.style.color = '#3b82f6';
        if (rowNeg) rowNeg.style.color = '#ef4444';
        if (iconPos) iconPos.innerHTML = '&#9632;';
        if (iconNeg) iconNeg.innerHTML = '&#9632;';
        if (labelPos) labelPos.textContent = 'Dem Advantage (4 Seats: NC-01, 02, 04, 12)';
        if (labelNeg) labelNeg.textContent = 'Rep Advantage (10 Seats: NC-03, 05-11, 13, 14)';
        const labelFlip = document.getElementById('legendLabelFlip');
        if (labelFlip) labelFlip.textContent = 'Projected Delegation: 10 R / 4 D (All seats hold)';
        if (note) note.textContent = 'Cross-hatching indicates seats projected to change party control. 95% Confidence Intervals calculated for all districts.';
        return;
      }
      if (currentMapMode === 'senate') {
        const title = document.getElementById('legendTitle');
        const subtitle = document.getElementById('legendSubtitle');
        const rowPos = document.getElementById('legendRowPos');
        const rowNeg = document.getElementById('legendRowNeg');
        const labelPos = document.getElementById('legendLabelPos');
        const labelNeg = document.getElementById('legendLabelNeg');
        const note = document.getElementById('legendNote');
        const rowFlip = document.getElementById('legendRowFlip');
        const iconPos = rowPos ? rowPos.querySelector('span:first-child') : null;
        const iconNeg = rowNeg ? rowNeg.querySelector('span:first-child') : null;

        if (rowFlip) rowFlip.style.display = 'flex';
        if (title) title.textContent = 'NC Senate Model';
        if (subtitle) subtitle.textContent = '50 Districts (2026 Model)';
        if (rowPos) rowPos.style.color = '#3b82f6';
        if (rowNeg) rowNeg.style.color = '#ef4444';
        if (iconPos) iconPos.innerHTML = '&#9632;';
        if (iconNeg) iconNeg.innerHTML = '&#9632;';
        if (labelPos) labelPos.textContent = 'Dem Projected: 23 Seats';
        if (labelNeg) labelNeg.textContent = 'Rep Projected: 27 Seats';
        const labelFlip = document.getElementById('legendLabelFlip');
        if (labelFlip) labelFlip.textContent = 'GOP Supermajority Status: Broken (27 / 30 needed)';
        if (note) note.textContent = 'Bottom-up precinct aggregation. Cross-hatching indicates seats projected to flip control.';
        return;
      }
      if (currentMapMode === 'house') {
        const title = document.getElementById('legendTitle');
        const subtitle = document.getElementById('legendSubtitle');
        const rowPos = document.getElementById('legendRowPos');
        const rowNeg = document.getElementById('legendRowNeg');
        const labelPos = document.getElementById('legendLabelPos');
        const labelNeg = document.getElementById('legendLabelNeg');
        const note = document.getElementById('legendNote');
        const rowFlip = document.getElementById('legendRowFlip');
        const iconPos = rowPos ? rowPos.querySelector('span:first-child') : null;
        const iconNeg = rowNeg ? rowNeg.querySelector('span:first-child') : null;

        if (rowFlip) rowFlip.style.display = 'flex';
        if (title) title.textContent = 'NC House Model';
        if (subtitle) subtitle.textContent = '120 Districts (2026 Model)';
        if (rowPos) rowPos.style.color = '#3b82f6';
        if (rowNeg) rowNeg.style.color = '#ef4444';
        if (iconPos) iconPos.innerHTML = '&#9632;';
        if (iconNeg) iconNeg.innerHTML = '&#9632;';
        if (labelPos) labelPos.textContent = 'Dem Projected: 62 Seats';
        if (labelNeg) labelNeg.textContent = 'Rep Projected: 58 Seats';
        const labelFlip = document.getElementById('legendLabelFlip');
        if (labelFlip) labelFlip.textContent = 'GOP Supermajority Status: Broken (58 / 72 needed)';
        if (note) note.textContent = 'Bottom-up precinct aggregation. Cross-hatching indicates seats projected to flip control.';
        return;
      }"""

if old_legend_check in html:
    html = html.replace(old_legend_check, new_legend_check)
    print("Updated updateLegendUI with Senate and House branches.")
else:
    print("Warning: old_legend_check pattern not matched directly.")

# 9. Append JavaScript Functions for Senate and House rendering & inspection
js_functions = """
    // ==========================================
    // NC SENATE & NC HOUSE RENDERING & INSPECTORS
    // ==========================================

    function getDistrictFill(dist) {
      if (!dist) return '#1e293b';
      if (dist.flip_status === 'FLIP_R_TO_D') return 'url(#patternFlipRtoD)';
      if (dist.flip_status === 'FLIP_D_TO_R') return 'url(#patternFlipDtoR)';

      const m = dist.pred_margin;
      const absM = Math.abs(m);
      if (m >= 0) {
        if (absM > 35) return '#172554'; // Deep Solid Dem
        if (absM > 20) return '#1e40af'; // Solid Dem
        if (absM > 10) return '#2563eb'; // Likely Dem
        if (absM > 4)  return '#3b82f6'; // Lean Dem
        return '#60a5fa'; // Tilt Dem (<4% margin)
      } else {
        if (absM > 35) return '#7f1d1d'; // Deep Solid Rep
        if (absM > 20) return '#991b1b'; // Solid Rep
        if (absM > 10) return '#dc2626'; // Likely Rep
        if (absM > 4)  return '#ef4444'; // Lean Rep
        return '#f87171'; // Tilt Rep (<4% margin)
      }
    }

    function showDistrictTooltip(dist, typeLabel, e) {
      if (!dist) return;
      tooltipEl.classList.remove('hidden');
      const mStr = dist.projected_margin_str || (dist.pred_margin >= 0 ? `D +${dist.pred_margin.toFixed(1)}%` : `R +${Math.abs(dist.pred_margin).toFixed(1)}%`);
      const badgeBg = dist.projected_winner_party === 'D' ? 'bg-blue-600/30 text-blue-300 border border-blue-500/40' : 'bg-red-600/30 text-red-300 border border-red-500/40';
      const cands = [];
      if (dist.dem_candidate) cands.push(`<span class="text-blue-400 font-semibold">${dist.dem_candidate} (D)</span>`);
      if (dist.rep_candidate) cands.push(`<span class="text-red-400 font-semibold">${dist.rep_candidate} (R)</span>`);
      const candsHtml = cands.length > 0 ? cands.join(' vs ') : '<span class="text-slate-400 italic">Major Party Candidates</span>';

      tooltipEl.innerHTML = `
        <div class="font-bold text-sm text-white flex items-center justify-between gap-3 mb-1">
          <span>${dist.name}</span>
          <span class="text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${badgeBg}">
            ${dist.rating}
          </span>
        </div>
        <div class="text-xs text-slate-300 mb-2">${candsHtml}</div>
        <div class="grid grid-cols-2 gap-2 text-xs border-t border-slate-700/60 pt-2 mb-1.5">
          <div>
            <span class="text-slate-400 block text-[10px]">Projected Outcome</span>
            <span class="font-mono font-bold ${dist.projected_winner_party === 'D' ? 'text-blue-400' : 'text-red-400'}">${mStr}</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[10px]">Win Probability</span>
            <span class="font-mono font-bold text-slate-200">${dist.projected_winner_party === 'D' ? dist.p_dem : dist.p_rep}%</span>
          </div>
        </div>
        <div class="text-[10px] text-slate-400 flex items-center justify-between border-t border-slate-800 pt-1">
          <span>95% CI: <span class="font-mono text-slate-300">${dist.ci_str}</span></span>
          <span class="capitalize text-slate-400">${dist.call_confidence || ''}</span>
        </div>
      `;
      updateTooltipPosition(e);
    }

    function renderSenateDistricts() {
      const data = window.NC_SENATE_DATA;
      if (!data || !data.districts) return;
      const layer = document.getElementById('senateLayer');
      const labelsLayer = document.getElementById('senateLabelsLayer');
      if (!layer || !labelsLayer) return;

      layer.innerHTML = '';
      labelsLayer.innerHTML = '';

      Object.values(data.districts).forEach(dist => {
        if (!dist.path) return;
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('id', `sd-${dist.id}`);
        path.setAttribute('class', 'senate-path cursor-pointer transition-colors duration-150');
        path.setAttribute('d', dist.path);
        path.setAttribute('fill', getDistrictFill(dist));
        path.setAttribute('vector-effect', 'non-scaling-stroke');

        const isSelected = selectedSenateId === dist.id;
        if (selectedSenateId) {
          if (isSelected) {
            path.setAttribute('stroke', '#34d399');
            path.setAttribute('stroke-width', '2.8');
            path.style.opacity = '1.0';
            path.style.filter = 'drop-shadow(0 0 6px rgba(52, 211, 153, 0.5))';
          } else {
            path.setAttribute('stroke', '#0f172a');
            path.setAttribute('stroke-width', '0.75');
            path.style.opacity = '0.35';
          }
        } else {
          path.setAttribute('stroke', '#0f172a');
          path.setAttribute('stroke-width', '1.0');
          path.style.opacity = '0.95';
        }

        path.addEventListener('mouseenter', (e) => {
          if (!selectedSenateId || isSelected) {
            path.setAttribute('stroke', '#ffffff');
            path.setAttribute('stroke-width', '2.5');
          }
          showDistrictTooltip(dist, 'NC Senate', e);
        });

        path.addEventListener('mousemove', (e) => updateTooltipPosition(e));

        path.addEventListener('mouseleave', () => {
          if (selectedSenateId) {
            if (isSelected) {
              path.setAttribute('stroke', '#34d399');
              path.setAttribute('stroke-width', '2.8');
            } else {
              path.setAttribute('stroke', '#0f172a');
              path.setAttribute('stroke-width', '0.75');
            }
          } else {
            path.setAttribute('stroke', '#0f172a');
            path.setAttribute('stroke-width', '1.0');
          }
          hideTooltip();
        });

        path.addEventListener('click', (e) => {
          e.stopPropagation();
          selectSenateDistrict(dist.id === selectedSenateId ? null : dist.id);
        });

        layer.appendChild(path);

        if (dist.centroid) {
          const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          text.setAttribute('x', dist.centroid[0]);
          text.setAttribute('y', dist.centroid[1]);
          text.setAttribute('text-anchor', 'middle');
          text.setAttribute('dominant-baseline', 'central');
          text.setAttribute('fill', '#ffffff');
          text.setAttribute('font-size', '9px');
          text.setAttribute('font-weight', '700');
          text.setAttribute('font-family', 'ui-monospace, SFMono-Regular, Menlo, monospace');
          text.setAttribute('pointer-events', 'none');
          text.setAttribute('stroke', '#020617');
          text.setAttribute('stroke-width', '2.5px');
          text.setAttribute('paint-order', 'stroke fill');
          text.setAttribute('stroke-linejoin', 'round');
          text.textContent = dist.number;
          labelsLayer.appendChild(text);
        }
      });
    }

    function selectSenateDistrict(sdId) {
      selectedSenateId = sdId || null;
      const selector = document.getElementById('senateSelector');
      if (selector) selector.value = selectedSenateId || '';

      if (currentMapMode !== 'senate') {
        setMapMode('senate');
        return;
      }

      renderSenateDistricts();
      renderSenateInspector(selectedSenateId);
      updateLegendUI();

      const data = window.NC_SENATE_DATA;
      if (selectedSenateId && data && data.districts && data.districts[selectedSenateId]) {
        const dist = data.districts[selectedSenateId];
        if (dist.bbox) animateViewBox(dist.bbox, 500);
      } else {
        animateViewBox([0, 0, 1200, 483], 500);
      }
    }

    function renderSenateInspector(sdId) {
      const inspectorEl = document.getElementById('countyDetailCard');
      if (!inspectorEl) return;
      const data = window.NC_SENATE_DATA;
      if (!data || !data.districts) return;

      if (!sdId) {
        // Chamber Overview Card
        const list = Object.values(data.districts);
        const demCount = list.filter(d => d.projected_winner_party === 'D').length;
        const repCount = list.filter(d => d.projected_winner_party === 'R').length;
        const battlegrounds = list.filter(d => Math.abs(d.pred_margin) <= 6.0).sort((a,b) => Math.abs(a.pred_margin) - Math.abs(b.pred_margin));

        inspectorEl.innerHTML = `
          <div class="p-4 bg-slate-900/90 border border-slate-800 rounded-xl">
            <div class="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
              <div>
                <h3 class="font-bold text-base text-white">NC Senate Chamber Model</h3>
                <p class="text-xs text-slate-400">50 Seats &bull; 2026 General Election Forecast</p>
              </div>
              <span class="px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">50 Seats</span>
            </div>

            <div class="grid grid-cols-2 gap-3 mb-4">
              <div class="p-3 bg-blue-950/40 border border-blue-800/50 rounded-lg text-center">
                <span class="text-[11px] text-blue-300 uppercase font-semibold block">Democratic Seats</span>
                <span class="text-2xl font-bold font-mono text-blue-400">${demCount}</span>
                <span class="text-[10px] text-slate-400 block mt-0.5">Supermajority Broken</span>
              </div>
              <div class="p-3 bg-red-950/40 border border-red-800/50 rounded-lg text-center">
                <span class="text-[11px] text-red-300 uppercase font-semibold block">Republican Seats</span>
                <span class="text-2xl font-bold font-mono text-red-400">${repCount}</span>
                <span class="text-[10px] text-slate-400 block mt-0.5">30 Needed for Veto Override</span>
              </div>
            </div>

            <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center justify-between">
              <span>Top Swing Battlegrounds (&le;6% Margin)</span>
              <span class="text-[10px] text-purple-400 font-mono">${battlegrounds.length} Key Seats</span>
            </h4>
            <div class="space-y-1.5 max-h-[380px] overflow-y-auto pr-1">
              ${battlegrounds.map(d => `
                <div onclick="selectSenateDistrict('${d.id}')" class="flex items-center justify-between p-2 rounded bg-slate-800/60 hover:bg-slate-700/80 cursor-pointer transition border border-slate-700/50">
                  <div>
                    <span class="font-bold text-xs text-white">${d.name}</span>
                    <span class="text-[11px] text-slate-400 block">${d.dem_candidate || 'DEM'} vs ${d.rep_candidate || 'REP'}</span>
                  </div>
                  <div class="text-right">
                    <span class="font-mono text-xs font-bold ${d.projected_winner_party === 'D' ? 'text-blue-400' : 'text-red-400'}">${d.projected_margin_str}</span>
                    <span class="text-[10px] text-slate-400 block capitalize">${d.rating}</span>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
        return;
      }

      // Single Senate District Detail
      const dist = data.districts[sdId];
      if (!dist) return;
      const isDem = dist.projected_winner_party === 'D';

      inspectorEl.innerHTML = `
        <div class="p-4 bg-slate-900/90 border border-slate-800 rounded-xl">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
            <div>
              <div class="flex items-center gap-2">
                <h3 class="font-bold text-lg text-white">${dist.name}</h3>
                <span class="text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${isDem ? 'bg-blue-600/30 text-blue-300 border border-blue-500/40' : 'bg-red-600/30 text-red-300 border border-red-500/40'}">
                  ${dist.rating}
                </span>
              </div>
              <p class="text-xs text-slate-400">${dist.region}</p>
            </div>
            <button onclick="selectSenateDistrict(null)" class="text-xs text-slate-400 hover:text-white px-2 py-1 bg-slate-800 rounded border border-slate-700">All Seats</button>
          </div>

          <div class="p-3 mb-3 rounded-lg border ${isDem ? 'bg-blue-950/30 border-blue-800/40' : 'bg-red-950/30 border-red-800/40'}">
            <span class="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-1">Projected Winner & Margin</span>
            <div class="flex items-center justify-between">
              <span class="text-base font-bold text-white">${dist.projected_winner_full || dist.projected_winner_name}</span>
              <span class="text-base font-bold font-mono ${isDem ? 'text-blue-400' : 'text-red-400'}">${dist.projected_margin_str}</span>
            </div>
            <div class="text-[11px] text-slate-400 mt-1 flex justify-between">
              <span>Win Probability: <strong class="text-slate-200">${isDem ? dist.p_dem : dist.p_rep}%</strong></span>
              <span>95% CI: <strong class="text-slate-200">${dist.ci_str}</strong></span>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-2 text-xs mb-3">
            <div class="p-2 bg-slate-800/50 rounded border border-slate-700/50">
              <span class="text-[10px] text-slate-400 block">Democratic Share</span>
              <span class="text-sm font-bold font-mono text-blue-400">${dist.pred_final_dem.toFixed(1)}%</span>
            </div>
            <div class="p-2 bg-slate-800/50 rounded border border-slate-700/50">
              <span class="text-[10px] text-slate-400 block">Republican Share</span>
              <span class="text-sm font-bold font-mono text-red-400">${dist.pred_final_rep.toFixed(1)}%</span>
            </div>
          </div>

          <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Counties in District</h4>
          <div class="flex flex-wrap gap-1.5 max-h-[160px] overflow-y-auto">
            ${dist.counties.map(c => `
              <span class="text-xs bg-slate-800 text-slate-300 px-2 py-1 rounded border border-slate-700">${c}</span>
            `).join('')}
          </div>
        </div>
      `;
    }

    function renderHouseDistricts() {
      const data = window.NC_HOUSE_DATA;
      if (!data || !data.districts) return;
      const layer = document.getElementById('houseLayer');
      const labelsLayer = document.getElementById('houseLabelsLayer');
      if (!layer || !labelsLayer) return;

      layer.innerHTML = '';
      labelsLayer.innerHTML = '';

      Object.values(data.districts).forEach(dist => {
        if (!dist.path) return;
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('id', `hd-${dist.id}`);
        path.setAttribute('class', 'house-path cursor-pointer transition-colors duration-150');
        path.setAttribute('d', dist.path);
        path.setAttribute('fill', getDistrictFill(dist));
        path.setAttribute('vector-effect', 'non-scaling-stroke');

        const isSelected = selectedHouseId === dist.id;
        if (selectedHouseId) {
          if (isSelected) {
            path.setAttribute('stroke', '#fbbf24');
            path.setAttribute('stroke-width', '2.8');
            path.style.opacity = '1.0';
            path.style.filter = 'drop-shadow(0 0 6px rgba(251, 191, 36, 0.5))';
          } else {
            path.setAttribute('stroke', '#0f172a');
            path.setAttribute('stroke-width', '0.75');
            path.style.opacity = '0.35';
          }
        } else {
          path.setAttribute('stroke', '#0f172a');
          path.setAttribute('stroke-width', '0.8');
          path.style.opacity = '0.95';
        }

        path.addEventListener('mouseenter', (e) => {
          if (!selectedHouseId || isSelected) {
            path.setAttribute('stroke', '#ffffff');
            path.setAttribute('stroke-width', '2.2');
          }
          showDistrictTooltip(dist, 'NC House', e);
        });

        path.addEventListener('mousemove', (e) => updateTooltipPosition(e));

        path.addEventListener('mouseleave', () => {
          if (selectedHouseId) {
            if (isSelected) {
              path.setAttribute('stroke', '#fbbf24');
              path.setAttribute('stroke-width', '2.8');
            } else {
              path.setAttribute('stroke', '#0f172a');
              path.setAttribute('stroke-width', '0.75');
            }
          } else {
            path.setAttribute('stroke', '#0f172a');
            path.setAttribute('stroke-width', '0.8');
          }
          hideTooltip();
        });

        path.addEventListener('click', (e) => {
          e.stopPropagation();
          selectHouseDistrict(dist.id === selectedHouseId ? null : dist.id);
        });

        layer.appendChild(path);

        if (dist.centroid) {
          const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          text.setAttribute('x', dist.centroid[0]);
          text.setAttribute('y', dist.centroid[1]);
          text.setAttribute('text-anchor', 'middle');
          text.setAttribute('dominant-baseline', 'central');
          text.setAttribute('fill', '#ffffff');
          text.setAttribute('font-size', '8px');
          text.setAttribute('font-weight', '700');
          text.setAttribute('font-family', 'ui-monospace, SFMono-Regular, Menlo, monospace');
          text.setAttribute('pointer-events', 'none');
          text.setAttribute('stroke', '#020617');
          text.setAttribute('stroke-width', '2px');
          text.setAttribute('paint-order', 'stroke fill');
          text.setAttribute('stroke-linejoin', 'round');
          text.textContent = dist.number;
          labelsLayer.appendChild(text);
        }
      });
    }

    function selectHouseDistrict(hdId) {
      selectedHouseId = hdId || null;
      const selector = document.getElementById('houseSelector');
      if (selector) selector.value = selectedHouseId || '';

      if (currentMapMode !== 'house') {
        setMapMode('house');
        return;
      }

      renderHouseDistricts();
      renderHouseInspector(selectedHouseId);
      updateLegendUI();

      const data = window.NC_HOUSE_DATA;
      if (selectedHouseId && data && data.districts && data.districts[selectedHouseId]) {
        const dist = data.districts[selectedHouseId];
        if (dist.bbox) animateViewBox(dist.bbox, 500);
      } else {
        animateViewBox([0, 0, 1200, 483], 500);
      }
    }

    function renderHouseInspector(hdId) {
      const inspectorEl = document.getElementById('countyDetailCard');
      if (!inspectorEl) return;
      const data = window.NC_HOUSE_DATA;
      if (!data || !data.districts) return;

      if (!hdId) {
        // Chamber Overview Card
        const list = Object.values(data.districts);
        const demCount = list.filter(d => d.projected_winner_party === 'D').length;
        const repCount = list.filter(d => d.projected_winner_party === 'R').length;
        const battlegrounds = list.filter(d => Math.abs(d.pred_margin) <= 6.0).sort((a,b) => Math.abs(a.pred_margin) - Math.abs(b.pred_margin));

        inspectorEl.innerHTML = `
          <div class="p-4 bg-slate-900/90 border border-slate-800 rounded-xl">
            <div class="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
              <div>
                <h3 class="font-bold text-base text-white">NC House Chamber Model</h3>
                <p class="text-xs text-slate-400">120 Seats &bull; 2026 General Election Forecast</p>
              </div>
              <span class="px-2 py-0.5 rounded text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">120 Seats</span>
            </div>

            <div class="grid grid-cols-2 gap-3 mb-4">
              <div class="p-3 bg-blue-950/40 border border-blue-800/50 rounded-lg text-center">
                <span class="text-[11px] text-blue-300 uppercase font-semibold block">Democratic Seats</span>
                <span class="text-2xl font-bold font-mono text-blue-400">${demCount}</span>
                <span class="text-[10px] text-slate-400 block mt-0.5">Supermajority Broken</span>
              </div>
              <div class="p-3 bg-red-950/40 border border-red-800/50 rounded-lg text-center">
                <span class="text-[11px] text-red-300 uppercase font-semibold block">Republican Seats</span>
                <span class="text-2xl font-bold font-mono text-red-400">${repCount}</span>
                <span class="text-[10px] text-slate-400 block mt-0.5">72 Needed for Veto Override</span>
              </div>
            </div>

            <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center justify-between">
              <span>Top Battlegrounds (&le;6% Margin)</span>
              <span class="text-[10px] text-amber-400 font-mono">${battlegrounds.length} Key Seats</span>
            </h4>
            <div class="space-y-1.5 max-h-[380px] overflow-y-auto pr-1">
              ${battlegrounds.map(d => `
                <div onclick="selectHouseDistrict('${d.id}')" class="flex items-center justify-between p-2 rounded bg-slate-800/60 hover:bg-slate-700/80 cursor-pointer transition border border-slate-700/50">
                  <div>
                    <span class="font-bold text-xs text-white">${d.name}</span>
                    <span class="text-[11px] text-slate-400 block">${d.dem_candidate || 'DEM'} vs ${d.rep_candidate || 'REP'}</span>
                  </div>
                  <div class="text-right">
                    <span class="font-mono text-xs font-bold ${d.projected_winner_party === 'D' ? 'text-blue-400' : 'text-red-400'}">${d.projected_margin_str}</span>
                    <span class="text-[10px] text-slate-400 block capitalize">${d.rating}</span>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
        return;
      }

      // Single House District Detail
      const dist = data.districts[hdId];
      if (!dist) return;
      const isDem = dist.projected_winner_party === 'D';

      inspectorEl.innerHTML = `
        <div class="p-4 bg-slate-900/90 border border-slate-800 rounded-xl">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
            <div>
              <div class="flex items-center gap-2">
                <h3 class="font-bold text-lg text-white">${dist.name}</h3>
                <span class="text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${isDem ? 'bg-blue-600/30 text-blue-300 border border-blue-500/40' : 'bg-red-600/30 text-red-300 border border-red-500/40'}">
                  ${dist.rating}
                </span>
              </div>
              <p class="text-xs text-slate-400">${dist.region}</p>
            </div>
            <button onclick="selectHouseDistrict(null)" class="text-xs text-slate-400 hover:text-white px-2 py-1 bg-slate-800 rounded border border-slate-700">All Seats</button>
          </div>

          <div class="p-3 mb-3 rounded-lg border ${isDem ? 'bg-blue-950/30 border-blue-800/40' : 'bg-red-950/30 border-red-800/40'}">
            <span class="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-1">Projected Winner & Margin</span>
            <div class="flex items-center justify-between">
              <span class="text-base font-bold text-white">${dist.projected_winner_full || dist.projected_winner_name}</span>
              <span class="text-base font-bold font-mono ${isDem ? 'text-blue-400' : 'text-red-400'}">${dist.projected_margin_str}</span>
            </div>
            <div class="text-[11px] text-slate-400 mt-1 flex justify-between">
              <span>Win Probability: <strong class="text-slate-200">${isDem ? dist.p_dem : dist.p_rep}%</strong></span>
              <span>95% CI: <strong class="text-slate-200">${dist.ci_str}</strong></span>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-2 text-xs mb-3">
            <div class="p-2 bg-slate-800/50 rounded border border-slate-700/50">
              <span class="text-[10px] text-slate-400 block">Democratic Share</span>
              <span class="text-sm font-bold font-mono text-blue-400">${dist.pred_final_dem.toFixed(1)}%</span>
            </div>
            <div class="p-2 bg-slate-800/50 rounded border border-slate-700/50">
              <span class="text-[10px] text-slate-400 block">Republican Share</span>
              <span class="text-sm font-bold font-mono text-red-400">${dist.pred_final_rep.toFixed(1)}%</span>
            </div>
          </div>

          <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Counties in District</h4>
          <div class="flex flex-wrap gap-1.5 max-h-[160px] overflow-y-auto">
            ${dist.counties.map(c => `
              <span class="text-xs bg-slate-800 text-slate-300 px-2 py-1 rounded border border-slate-700">${c}</span>
            `).join('')}
          </div>
        </div>
      `;
    }
"""

if 'function renderSenateDistricts()' not in html:
    html = html.replace('function renderCongressionalDistricts() {', js_functions + '\n    function renderCongressionalDistricts() {')
    print("Added JavaScript rendering, interaction, and inspector functions for Senate and House.")

with open('/home/rann/src/elections/2026 analysis/beta/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Saved updated beta/index.html successfully!")

