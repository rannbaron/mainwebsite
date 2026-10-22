import json, re, math

print("1. Parsing official 2024 NC House results...")
with open('/home/rann/src/elections/2026 analysis/nc_house_2024_wiki.txt') as f:
    text = f.read()

sections = re.split(r'===District (\d+)===', text)
house_2024 = {}
for i in range(1, len(sections), 2):
    d_num = int(sections[i])
    sec = sections[i+1]
    pct1 = re.search(r'\|\s*percentage1\s*=\s*\'*([0-9\.]+)', sec)
    party1 = re.search(r'\|\s*party1\s*=\s*([^\n|]+)', sec)
    pct2 = re.search(r'\|\s*percentage2\s*=\s*\'*([0-9\.]+)', sec)
    party2 = re.search(r'\|\s*party2\s*=\s*([^\n|]+)', sec)
    after_p = re.search(r'\|\s*after_party\s*=\s*([^\n|]+)', sec)
    winner_p = 'R' if (after_p and 'Republican' in after_p.group(1)) else ('D' if (after_p and 'Democratic' in after_p.group(1)) else None)
    
    dem_pct = None
    rep_pct = None
    if party1 and 'Democratic' in party1.group(1) and pct1: dem_pct = float(pct1.group(1))
    elif party1 and 'Republican' in party1.group(1) and pct1: rep_pct = float(pct1.group(1))
    if party2 and 'Democratic' in party2.group(1) and pct2: dem_pct = float(pct2.group(1))
    elif party2 and 'Republican' in party2.group(1) and pct2: rep_pct = float(pct2.group(1))
    
    if dem_pct is None and rep_pct is not None: dem_pct = 0.0
    if rep_pct is None and dem_pct is not None: rep_pct = 0.0
    
    m_24 = (dem_pct - rep_pct) if (dem_pct is not None and rep_pct is not None) else (-40.0 if winner_p == 'R' else 40.0)
    house_2024[d_num] = {
        'dem_pct': dem_pct,
        'rep_pct': rep_pct,
        'margin_2024': m_24,
        'winner_2024': winner_p
    }

print("2. Parsing official 2024 NC Senate results...")
with open('/home/rann/src/elections/2026 analysis/nc_senate_2024_wiki.txt') as f:
    s_text = f.read()

s_sections = re.split(r'===District (\d+)===', s_text)
senate_2024 = {}
for i in range(1, len(s_sections), 2):
    d_num = int(s_sections[i])
    sec = s_sections[i+1]
    boxes = re.findall(r'{{Election box (?:winning )?candidate[^\}]*?\|\s*party\s*=\s*([^\n|]+)[\s\S]*?\|\s*percentage\s*=\s*([0-9\.]+)', sec)
    dem_pct = None
    rep_pct = None
    for party, pct in boxes:
        if 'Democratic' in party: dem_pct = float(pct)
        elif 'Republican' in party: rep_pct = float(pct)
    m_win = re.search(r'{{Election box (?:hold|new seat win)[^}]*\|\s*winner\s*=\s*([^\n|]+)', sec)
    winner_p = 'R' if (m_win and 'Republican' in m_win.group(1)) else ('D' if (m_win and 'Democratic' in m_win.group(1)) else None)
    if not winner_p:
        if dem_pct is not None and rep_pct is not None:
            winner_p = 'D' if dem_pct > rep_pct else 'R'
        elif dem_pct is not None: winner_p = 'D'
        elif rep_pct is not None: winner_p = 'R'
    
    m_24 = (dem_pct - rep_pct) if (dem_pct is not None and rep_pct is not None) else (-40.0 if winner_p == 'R' else 40.0)
    senate_2024[d_num] = {
        'dem_pct': dem_pct,
        'rep_pct': rep_pct,
        'margin_2024': m_24,
        'winner_2024': winner_p
    }

print("3. Loading county swings and json data...")
with open('/home/rann/src/elections/2026 analysis/nc_map_data.json') as f:
    map_data = json.load(f)
county_swings = {c['name'].upper(): c['forecast']['swing_vs_2022'] for c in map_data['counties']}

with open('/home/rann/src/elections/2026 analysis/nc_house_data.json') as f:
    house = json.load(f)
with open('/home/rann/src/elections/2026 analysis/nc_senate_data.json') as f:
    senate = json.load(f)

# Calibrate House
h_flips_r_to_d = []
h_flips_d_to_r = []

for h_id, d in sorted(house.items(), key=lambda x: x[1]['number']):
    num = d['number']
    r24 = house_2024[num]
    m24 = r24['margin_2024']
    inc_p = r24['winner_2024']
    d['incumbent_party'] = inc_p
    d['prior_winner_party'] = inc_p
    
    if d['is_uncontested']:
        if d['dem_candidate']:
            d['pred_final_dem'] = 100.0
            d['pred_final_rep'] = 0.0
            d['pred_margin'] = 100.0
            d['rating'] = 'Safe D'
            d['p_dem'] = 100.0
            d['p_rep'] = 0.0
            d['projected_winner_party'] = 'D'
            d['projected_winner_name'] = d['dem_candidate'].split()[-1]
            d['projected_winner_full'] = d['dem_candidate']
            d['projected_margin_str'] = f"{d['dem_candidate']} (D) Uncontested"
            d['ci_str'] = 'Uncontested DEM'
            d['flip_status'] = 'HOLD' if inc_p == 'D' else 'FLIP_R_TO_D'
            d['is_flip'] = (inc_p != 'D')
        else:
            d['pred_final_dem'] = 0.0
            d['pred_final_rep'] = 100.0
            d['pred_margin'] = -100.0
            d['rating'] = 'Safe R'
            d['p_dem'] = 0.0
            d['p_rep'] = 100.0
            d['projected_winner_party'] = 'R'
            d['projected_winner_name'] = d['rep_candidate'].split()[-1]
            d['projected_winner_full'] = d['rep_candidate']
            d['projected_margin_str'] = f"{d['rep_candidate']} (R) Uncontested"
            d['ci_str'] = 'Uncontested REP'
            d['flip_status'] = 'HOLD' if inc_p == 'R' else 'FLIP_D_TO_R'
            d['is_flip'] = (inc_p != 'R')
        continue

    # Down-ballot legislative swing calculation using empirical 2024 cross-sectional elasticity (Beta = 0.860)
    c_swings = [county_swings.get(c.upper(), 4.0) for c in d['counties']]
    avg_c_swing = sum(c_swings) / len(c_swings) if c_swings else 4.0
    leg_swing = avg_c_swing * 0.860
    
    # Baseline margin calibrated
    m26 = round(m24 + leg_swing, 2)
    # Convert margin to dem/rep shares (assuming two-party sum = 100)
    dem_share = round((100.0 + m26) / 2.0, 2)
    rep_share = round((100.0 - m26) / 2.0, 2)
    dem_share = max(0.0, min(100.0, dem_share))
    rep_share = max(0.0, min(100.0, rep_share))
    
    d['pred_final_dem'] = dem_share
    d['pred_final_rep'] = rep_share
    d['pred_margin'] = m26
    d['net_margin_votes'] = int(round(d['proj_turnout'] * (m26 / 100.0)))
    
    proj_p = 'D' if m26 > 0 else 'R'
    abs_m = abs(m26)
    
    if abs_m >= 15: rating = f"Safe {proj_p}"
    elif abs_m >= 8: rating = f"Likely {proj_p}"
    elif abs_m >= 3: rating = f"Lean {proj_p}"
    else: rating = f"Tilt {proj_p}"
    d['rating'] = rating
    
    # Win prob via standard normal
    z = m26 / 3.8
    p_dem = round(0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100.0, 1)
    p_rep = round(100.0 - p_dem, 1)
    d['p_dem'] = p_dem
    d['p_rep'] = p_rep
    
    ci_low = round(m26 - 7.5, 1)
    ci_high = round(m26 + 7.5, 1)
    def fmt_m(val):
        return f"D +{val:.1f}%" if val > 0 else (f"R +{abs(val):.1f}%" if val < 0 else "EVEN")
    d['ci_str'] = f"{fmt_m(ci_low)} to {fmt_m(ci_high)}"
    
    d['call_confidence'] = 'very high confidence' if abs_m >= 12 else ('high confidence' if abs_m >= 6 else 'moderate confidence')
    
    winner_cand = d['dem_candidate'] if proj_p == 'D' else d['rep_candidate']
    last_name = winner_cand.split()[-1] if winner_cand else proj_p
    d['projected_winner_party'] = proj_p
    d['projected_winner_name'] = last_name
    d['projected_winner_full'] = winner_cand
    d['projected_margin_str'] = f"{last_name} ({proj_p}) +{abs_m:.1f}%"
    
    is_flip = (inc_p != proj_p)
    d['is_flip'] = is_flip
    if is_flip:
        if inc_p == 'R' and proj_p == 'D':
            d['flip_status'] = 'FLIP_R_TO_D'
            h_flips_r_to_d.append(h_id)
        else:
            d['flip_status'] = 'FLIP_D_TO_R'
            h_flips_d_to_r.append(h_id)
    else:
        d['flip_status'] = 'HOLD'

print(f"Calibrated House: {len(h_flips_r_to_d)} Flips R->D ({h_flips_r_to_d}), {len(h_flips_d_to_r)} Flips D->R")
proj_house_dem = 49 + len(h_flips_r_to_d) - len(h_flips_d_to_r)
proj_house_rep = 71 - len(h_flips_r_to_d) + len(h_flips_d_to_r)
print(f"Projected House: {proj_house_dem} Dem / {proj_house_rep} Rep")

# Calibrate Senate
s_flips_r_to_d = []
s_flips_d_to_r = []

for s_id, d in sorted(senate.items(), key=lambda x: x[1]['number']):
    num = d['number']
    r24 = senate_2024[num]
    m24 = r24['margin_2024']
    inc_p = r24['winner_2024']
    d['incumbent_party'] = inc_p
    d['prior_winner_party'] = inc_p
    
    if d['is_uncontested']:
        if d['dem_candidate']:
            d['pred_final_dem'] = 100.0
            d['pred_final_rep'] = 0.0
            d['pred_margin'] = 100.0
            d['rating'] = 'Safe D'
            d['p_dem'] = 100.0
            d['p_rep'] = 0.0
            d['projected_winner_party'] = 'D'
            d['projected_winner_name'] = d['dem_candidate'].split()[-1]
            d['projected_winner_full'] = d['dem_candidate']
            d['projected_margin_str'] = f"{d['dem_candidate']} (D) Uncontested"
            d['ci_str'] = 'Uncontested DEM'
            d['flip_status'] = 'HOLD' if inc_p == 'D' else 'FLIP_R_TO_D'
            d['is_flip'] = (inc_p != 'D')
        else:
            d['pred_final_dem'] = 0.0
            d['pred_final_rep'] = 100.0
            d['pred_margin'] = -100.0
            d['rating'] = 'Safe R'
            d['p_dem'] = 0.0
            d['p_rep'] = 100.0
            d['projected_winner_party'] = 'R'
            d['projected_winner_name'] = d['rep_candidate'].split()[-1]
            d['projected_winner_full'] = d['rep_candidate']
            d['projected_margin_str'] = f"{d['rep_candidate']} (R) Uncontested"
            d['ci_str'] = 'Uncontested REP'
            d['flip_status'] = 'HOLD' if inc_p == 'R' else 'FLIP_D_TO_R'
            d['is_flip'] = (inc_p != 'R')
        continue

    # Down-ballot legislative swing calculation using empirical 2024 cross-sectional elasticity (Beta = 0.911)
    c_swings = [county_swings.get(c.upper(), 4.0) for c in d['counties']]
    avg_c_swing = sum(c_swings) / len(c_swings) if c_swings else 4.0
    leg_swing = avg_c_swing * 0.911
    
    m26 = round(m24 + leg_swing, 2)
    dem_share = round((100.0 + m26) / 2.0, 2)
    rep_share = round((100.0 - m26) / 2.0, 2)
    dem_share = max(0.0, min(100.0, dem_share))
    rep_share = max(0.0, min(100.0, rep_share))
    
    d['pred_final_dem'] = dem_share
    d['pred_final_rep'] = rep_share
    d['pred_margin'] = m26
    d['net_margin_votes'] = int(round(d['proj_turnout'] * (m26 / 100.0)))
    
    proj_p = 'D' if m26 > 0 else 'R'
    abs_m = abs(m26)
    
    if abs_m >= 15: rating = f"Safe {proj_p}"
    elif abs_m >= 8: rating = f"Likely {proj_p}"
    elif abs_m >= 3: rating = f"Lean {proj_p}"
    else: rating = f"Tilt {proj_p}"
    d['rating'] = rating
    
    z = m26 / 3.5
    p_dem = round(0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100.0, 1)
    p_rep = round(100.0 - p_dem, 1)
    d['p_dem'] = p_dem
    d['p_rep'] = p_rep
    
    ci_low = round(m26 - 6.8, 1)
    ci_high = round(m26 + 6.8, 1)
    d['ci_str'] = f"{fmt_m(ci_low)} to {fmt_m(ci_high)}"
    d['call_confidence'] = 'very high confidence' if abs_m >= 12 else ('high confidence' if abs_m >= 6 else 'moderate confidence')
    
    winner_cand = d['dem_candidate'] if proj_p == 'D' else d['rep_candidate']
    last_name = winner_cand.split()[-1] if winner_cand else proj_p
    d['projected_winner_party'] = proj_p
    d['projected_winner_name'] = last_name
    d['projected_winner_full'] = winner_cand
    d['projected_margin_str'] = f"{last_name} ({proj_p}) +{abs_m:.1f}%"
    
    is_flip = (inc_p != proj_p)
    d['is_flip'] = is_flip
    if is_flip:
        if inc_p == 'R' and proj_p == 'D':
            d['flip_status'] = 'FLIP_R_TO_D'
            s_flips_r_to_d.append(s_id)
        else:
            d['flip_status'] = 'FLIP_D_TO_R'
            s_flips_d_to_r.append(s_id)
    else:
        d['flip_status'] = 'HOLD'

print(f"Calibrated Senate: {len(s_flips_r_to_d)} Flips R->D ({s_flips_r_to_d}), {len(s_flips_d_to_r)} Flips D->R")
proj_senate_dem = 20 + len(s_flips_r_to_d) - len(s_flips_d_to_r)
proj_senate_rep = 30 - len(s_flips_r_to_d) + len(s_flips_d_to_r)
print(f"Projected Senate: {proj_senate_dem} Dem / {proj_senate_rep} Rep")

# Save json files
with open('/home/rann/src/elections/2026 analysis/nc_house_data.json', 'w') as f:
    json.dump(house, f, indent=2)

with open('/home/rann/src/elections/2026 analysis/nc_senate_data.json', 'w') as f:
    json.dump(senate, f, indent=2)

# Update beta/index.html
with open('/home/rann/src/elections/2026 analysis/beta/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update embedded data
senate_json = json.dumps(senate)
house_json = json.dumps(house)

m_s = re.search(r'window\.NC_SENATE_DATA\s*=\s*\{.*?\};\n', html)
if m_s:
    html = html[:m_s.start()] + f'    window.NC_SENATE_DATA = {{"districts": {senate_json}}};\n' + html[m_s.end():]

m_h = re.search(r'window\.NC_HOUSE_DATA\s*=\s*\{.*?\};\n', html)
if m_h:
    html = html[:m_h.start()] + f'    window.NC_HOUSE_DATA = {{"districts": {house_json}}};\n' + html[m_h.end():]

# 2. Update Senate options
senate_options = ['<option value="">All NC Senate Districts (50 Districts)...</option>']
for s_id in sorted(senate.keys(), key=lambda x: senate[x]['number']):
    d = senate[s_id]
    m_str = d['projected_margin_str']
    reg = d['region'][:25]
    flip_tag = " [FLIP R→D]" if d['flip_status'] == 'FLIP_R_TO_D' else (" [FLIP D→R]" if d['flip_status'] == 'FLIP_D_TO_R' else "")
    senate_options.append(f'<option value="{s_id}">{s_id} &bull; {reg} &bull; {m_str}{flip_tag}</option>')

house_options = ['<option value="">All NC House Districts (120 Districts)...</option>']
for h_id in sorted(house.keys(), key=lambda x: house[x]['number']):
    d = house[h_id]
    m_str = d['projected_margin_str']
    reg = d['region'][:25]
    flip_tag = " [FLIP R→D]" if d['flip_status'] == 'FLIP_R_TO_D' else (" [FLIP D→R]" if d['flip_status'] == 'FLIP_D_TO_R' else "")
    house_options.append(f'<option value="{h_id}">{h_id} &bull; {reg} &bull; {m_str}{flip_tag}</option>')

m_sel_s = re.search(r'<select id="senateSelector"[^>]*>([\s\S]*?)</select>', html)
if m_sel_s:
    html = html[:m_sel_s.start(1)] + "\n            " + "".join(senate_options) + "\n          " + html[m_sel_s.end(1):]

m_sel_h = re.search(r'<select id="houseSelector"[^>]*>([\s\S]*?)</select>', html)
if m_sel_h:
    html = html[:m_sel_h.start(1)] + "\n            " + "".join(house_options) + "\n          " + html[m_sel_h.end(1):]

# 3. Update legend labels & supermajority stats
# Senate
html = re.sub(
    r"if \(currentMapMode === 'senate'\) \{[\s\S]*?if \(labelPos\) labelPos\.textContent = '[^']*';",
    lambda m: re.sub(r"if \(labelPos\) labelPos\.textContent = '[^']*';", f"if (labelPos) labelPos.textContent = 'Dem Projected: {proj_senate_dem} Seats';", m.group(0)),
    html
)
html = re.sub(
    r"if \(currentMapMode === 'senate'\) \{[\s\S]*?if \(labelNeg\) labelNeg\.textContent = '[^']*';",
    lambda m: re.sub(r"if \(labelNeg\) labelNeg\.textContent = '[^']*';", f"if (labelNeg) labelNeg.textContent = 'Rep Projected: {proj_senate_rep} Seats';", m.group(0)),
    html
)
s_flip_msg = f"Predicted Flips ({len(s_flips_r_to_d)} R→D): {', '.join(s_flips_r_to_d) if s_flips_r_to_d else 'None'} (Supermajority Broken: {proj_senate_rep}/30)"
html = re.sub(
    r"if \(currentMapMode === 'senate'\) \{[\s\S]*?const labelFlip = document\.getElementById\('legendLabelFlip'\);\s*if \(labelFlip\) labelFlip\.textContent = '[^']*';",
    lambda m: re.sub(r"if \(labelFlip\) labelFlip\.textContent = '[^']*';", f"if (labelFlip) labelFlip.textContent = '{s_flip_msg}';", m.group(0)),
    html
)

# House
html = re.sub(
    r"if \(currentMapMode === 'house'\) \{[\s\S]*?if \(labelPos\) labelPos\.textContent = '[^']*';",
    lambda m: re.sub(r"if \(labelPos\) labelPos\.textContent = '[^']*';", f"if (labelPos) labelPos.textContent = 'Dem Projected: {proj_house_dem} Seats';", m.group(0)),
    html
)
html = re.sub(
    r"if \(currentMapMode === 'house'\) \{[\s\S]*?if \(labelNeg\) labelNeg\.textContent = '[^']*';",
    lambda m: re.sub(r"if \(labelNeg\) labelNeg\.textContent = '[^']*';", f"if (labelNeg) labelNeg.textContent = 'Rep Projected: {proj_house_rep} Seats';", m.group(0)),
    html
)
h_flip_msg = f"Predicted Flips ({len(h_flips_r_to_d)} R→D): {', '.join(h_flips_r_to_d)} (Supermajority Broken: {proj_house_rep}/72)"
html = re.sub(
    r"if \(currentMapMode === 'house'\) \{[\s\S]*?const labelFlip = document\.getElementById\('legendLabelFlip'\);\s*if \(labelFlip\) labelFlip\.textContent = '[^']*';",
    lambda m: re.sub(r"if \(labelFlip\) labelFlip\.textContent = '[^']*';", f"if (labelFlip) labelFlip.textContent = '{h_flip_msg}';", m.group(0)),
    html
)

# 4. Update inspector overview banners
html = re.sub(
    r'120 Seats &bull; 2026 Forecast &bull; Baseline: 49 D / 71 R &bull; [^<]+',
    f'120 Seats &bull; 2026 Forecast &bull; Baseline: 49 D / 71 R &bull; {len(h_flips_r_to_d)} Projected Flips (R &rarr; D)',
    html
)
html = re.sub(
    r'50 Seats &bull; 2026 Forecast &bull; Baseline: 20 D / 30 R &bull; [^<]+',
    f'50 Seats &bull; 2026 Forecast &bull; Baseline: 20 D / 30 R &bull; {len(s_flips_r_to_d)} Projected Flips (R &rarr; D)',
    html
)

# Update Dem/Rep seat counts in overview card
html = re.sub(
    r'(<span class="text-2xl font-bold font-mono text-blue-400">\$\{demCount\}</span>)',
    r'\1',
    html
)

with open('/home/rann/src/elections/2026 analysis/beta/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("SUCCESS: Calibrated legislative models written to files and beta/index.html!")
