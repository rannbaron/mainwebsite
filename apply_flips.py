import glob, re, os, json
import pandas as pd
import geopandas as gpd

print("1. Loading precinct data and mappings...")

def norm_prec(s):
    if pd.isna(s): return ''
    s_str = str(s).strip()
    try: return str(int(float(s_str)))
    except Exception: pass
    s_clean = s_str.upper()
    s_clean = re.sub(r'^(PRECINCT|PCT|PREC)\s*[\#\:\-]?\s*', '', s_clean)
    s_clean = re.sub(r'[^A-Z0-9]', '', s_clean)
    return s_clean.lstrip('0') or '0'

with open('/home/rann/src/elections/2026 analysis/nc_map_data.json') as f:
    map_data = json.load(f)

prec_lookup = {}
for county, plist in map_data['precincts'].items():
    c_norm = county.upper().strip()
    for p in plist:
        p_id = norm_prec(p['id'])
        p_name = norm_prec(p['name'])
        t22 = p['data']['2022']['tot']
        act22 = p['forecast'].get('actual_2022', 50.0)
        info = {'t22': t22, 'act22': act22}
        prec_lookup[(c_norm, p_id)] = info
        prec_lookup[(c_norm, p_name)] = info

csvs = glob.glob('/home/rann/src/elections/2026 analysis/nc_elections_data/2026/*_absentee_20261103.csv')
frames = []
for c in csvs:
    df = pd.read_csv(c, usecols=['county_desc', 'precinct_desc', 'nc_house_desc', 'nc_senate_desc'], encoding='latin1', low_memory=False).dropna()
    df['c_norm'] = df['county_desc'].str.upper().str.strip()
    df['p_norm'] = df['precinct_desc'].apply(norm_prec)
    frames.append(df)
all_df = pd.concat(frames, ignore_index=True)
house_map = all_df.groupby(['c_norm', 'p_norm'])['nc_house_desc'].agg(lambda x: x.value_counts().index[0]).to_dict()
senate_map = all_df.groupby(['c_norm', 'p_norm'])['nc_senate_desc'].agg(lambda x: x.value_counts().index[0]).to_dict()
county_dom_house = all_df.groupby('c_norm')['nc_house_desc'].agg(lambda x: x.value_counts().index[0]).to_dict()
county_dom_senate = all_df.groupby('c_norm')['nc_senate_desc'].agg(lambda x: x.value_counts().index[0]).to_dict()

gdf = gpd.read_file('/home/rann/src/elections/2026 analysis/nc_elections_data/precincts_2026/SBE_PRECINCTS_20260824.shp')
gdf['c_norm'] = gdf['county_nam'].str.upper().str.strip()
gdf['p_norm'] = gdf['prec_id'].apply(norm_prec)
gdf['enr_norm'] = gdf['enr_desc'].apply(norm_prec)
assigned_house = []
assigned_senate = []
for _, row in gdf.iterrows():
    c = row['c_norm']
    p = row['p_norm']
    enr = row['enr_norm']
    h = house_map.get((c, p)) or house_map.get((c, enr)) or county_dom_house.get(c)
    s = senate_map.get((c, p)) or senate_map.get((c, enr)) or county_dom_senate.get(c)
    assigned_house.append(h)
    assigned_senate.append(s)
gdf['house_dist'] = assigned_house
gdf['senate_dist'] = assigned_senate

with open('/home/rann/src/elections/2026 analysis/nc_senate_data.json') as f:
    senate = json.load(f)
with open('/home/rann/src/elections/2026 analysis/nc_house_data.json') as f:
    house = json.load(f)

# Update Senate Flips
s_flips_r_to_d = []
s_flips_d_to_r = []

for s_id, d in senate.items():
    s_raw = f"NC SENATE DISTRICT {d['number']}"
    sub = gdf[gdf['senate_dist'] == s_raw]
    tot_v = 0
    dem_v = 0
    for _, r in sub.iterrows():
        info = prec_lookup.get((r['c_norm'], r['p_norm'])) or prec_lookup.get((r['c_norm'], r['enr_norm']))
        if info:
            tot_v += info['t22']
            dem_v += info['t22'] * (info['act22'] / 100.0)
    act22_dem = (dem_v / tot_v * 100.0) if tot_v > 0 else 50.0
    pred_dem = d['pred_final_dem']
    
    d['actual_2022_dem'] = round(act22_dem, 2)
    d['actual_2022_rep'] = round(100.0 - act22_dem, 2)
    d['prior_winner_party'] = 'D' if act22_dem > 50.0 else 'R'
    
    if act22_dem <= 50.0 and pred_dem > 50.0:
        d['flip_status'] = 'FLIP_R_TO_D'
        d['is_flip'] = True
        s_flips_r_to_d.append(s_id)
    elif act22_dem > 50.0 and pred_dem <= 50.0:
        d['flip_status'] = 'FLIP_D_TO_R'
        d['is_flip'] = True
        s_flips_d_to_r.append(s_id)
    else:
        d['flip_status'] = 'HOLD'
        d['is_flip'] = False

print(f"Senate: {len(s_flips_r_to_d)} Flips R->D ({s_flips_r_to_d}), {len(s_flips_d_to_r)} Flips D->R ({s_flips_d_to_r})")

# Update House Flips
h_flips_r_to_d = []
h_flips_d_to_r = []

for h_id, d in house.items():
    sub = gdf[gdf['house_dist'].str.contains(f"\\b{d['number']}\\b", na=False)]
    tot_v = 0
    dem_v = 0
    for _, r in sub.iterrows():
        info = prec_lookup.get((r['c_norm'], r['p_norm'])) or prec_lookup.get((r['c_norm'], r['enr_norm']))
        if info:
            tot_v += info['t22']
            dem_v += info['t22'] * (info['act22'] / 100.0)
    act22_dem = (dem_v / tot_v * 100.0) if tot_v > 0 else 50.0
    pred_dem = d['pred_final_dem']
    
    d['actual_2022_dem'] = round(act22_dem, 2)
    d['actual_2022_rep'] = round(100.0 - act22_dem, 2)
    d['prior_winner_party'] = 'D' if act22_dem > 50.0 else 'R'
    
    if act22_dem <= 50.0 and pred_dem > 50.0:
        d['flip_status'] = 'FLIP_R_TO_D'
        d['is_flip'] = True
        h_flips_r_to_d.append(h_id)
    elif act22_dem > 50.0 and pred_dem <= 50.0:
        d['flip_status'] = 'FLIP_D_TO_R'
        d['is_flip'] = True
        h_flips_d_to_r.append(h_id)
    else:
        d['flip_status'] = 'HOLD'
        d['is_flip'] = False

print(f"House: {len(h_flips_r_to_d)} Flips R->D, {len(h_flips_d_to_r)} Flips D->R")

# Save updated json files
with open('/home/rann/src/elections/2026 analysis/nc_senate_data.json', 'w') as f:
    json.dump(senate, f, indent=2)

with open('/home/rann/src/elections/2026 analysis/nc_house_data.json', 'w') as f:
    json.dump(house, f, indent=2)

print("Saved updated nc_senate_data.json and nc_house_data.json!")

# Now update beta/index.html
with open('/home/rann/src/elections/2026 analysis/beta/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update embedded window.NC_SENATE_DATA and window.NC_HOUSE_DATA
senate_json = json.dumps(senate)
house_json = json.dumps(house)

m_s = re.search(r'window\.NC_SENATE_DATA\s*=\s*\{.*?\};\n', html)
if m_s:
    html = html[:m_s.start()] + f'    window.NC_SENATE_DATA = {{"districts": {senate_json}}};\n' + html[m_s.end():]
    print("Re-embedded window.NC_SENATE_DATA.")

m_h = re.search(r'window\.NC_HOUSE_DATA\s*=\s*\{.*?\};\n', html)
if m_h:
    html = html[:m_h.start()] + f'    window.NC_HOUSE_DATA = {{"districts": {house_json}}};\n' + html[m_h.end():]
    print("Re-embedded window.NC_HOUSE_DATA.")

# 2. Update Senate options with flip tags
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
    print("Updated senateSelector options with flip indicators.")

m_sel_h = re.search(r'<select id="houseSelector"[^>]*>([\s\S]*?)</select>', html)
if m_sel_h:
    html = html[:m_sel_h.start(1)] + "\n            " + "".join(house_options) + "\n          " + html[m_sel_h.end(1):]
    print("Updated houseSelector options with flip indicators.")

# 3. Update legend text for Senate and House flips
old_s_flip = "const labelFlip = document.getElementById('legendLabelFlip');\n        if (labelFlip) labelFlip.textContent = 'GOP Supermajority Status: Broken (27 / 30 needed)';"
new_s_flip = f"const labelFlip = document.getElementById('legendLabelFlip');\n        if (labelFlip) labelFlip.textContent = 'Predicted Flips ({len(s_flips_r_to_d)} R→D): {', '.join(s_flips_r_to_d)}';"

if old_s_flip in html:
    html = html.replace(old_s_flip, new_s_flip)
    print("Updated Senate legend flip status.")

old_h_flip = "const labelFlip = document.getElementById('legendLabelFlip');\n        if (labelFlip) labelFlip.textContent = 'GOP Supermajority Status: Broken (58 / 72 needed)';"
new_h_flip = f"const labelFlip = document.getElementById('legendLabelFlip');\n        if (labelFlip) labelFlip.textContent = 'Predicted Flips ({len(h_flips_r_to_d)} R→D, {len(h_flips_d_to_r)} D→R): Net D+{len(h_flips_r_to_d)-len(h_flips_d_to_r)}';"

if old_h_flip in html:
    html = html.replace(old_h_flip, new_h_flip)
    print("Updated House legend flip status.")

# 4. Enhance inspector cards with flip banner
old_s_card = "<span>Win Probability: <strong class=\"text-slate-200\">${isDem ? dist.p_dem : dist.p_rep}%</strong></span>"
new_s_card = "<span>Win Probability: <strong class=\"text-slate-200\">${isDem ? dist.p_dem : dist.p_rep}%</strong></span>${dist.is_flip ? `<span class=\"ml-2 px-1.5 py-0.5 rounded font-bold text-[10px] bg-purple-600/30 text-purple-300 border border-purple-500/50\">PROJECTED FLIP (${dist.flip_status === 'FLIP_R_TO_D' ? 'R &rarr; D' : 'D &rarr; R'})</span>` : ''}"

html = html.replace(old_s_card, new_s_card)

with open('/home/rann/src/elections/2026 analysis/beta/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Saved updated beta/index.html with cross-hatching and flip badges!")

