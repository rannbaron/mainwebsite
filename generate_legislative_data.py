import glob, re, os, json, math
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon

ox = 107870.16004014212
oy = 333451.0423580661
scale = 0.0014308286314556736

def norm_prec(s):
    if pd.isna(s):
        return ''
    s_str = str(s).strip()
    try:
        return str(int(float(s_str)))
    except Exception:
        pass
    s_clean = s_str.upper()
    s_clean = re.sub(r'^(PRECINCT|PCT|PREC)\s*[\#\:\-]?\s*', '', s_clean)
    s_clean = re.sub(r'[^A-Z0-9]', '', s_clean)
    return s_clean.lstrip('0') or '0'

def geom_to_svg(geom, tolerance=70.0):
    if tolerance > 0:
        geom = geom.simplify(tolerance, preserve_topology=True)
    parts = []
    polys = [geom] if isinstance(geom, Polygon) else (geom.geoms if isinstance(geom, MultiPolygon) else [])
    for poly in polys:
        ext = poly.exterior.coords
        coords = [f"{(x - ox)*scale:.1f},{(oy - y)*scale:.1f}" for x, y in ext]
        parts.append("M" + "L".join(coords) + "Z")
    return "".join(parts)

def get_svg_bbox(geom):
    b = geom.bounds
    x0 = (b[0] - ox) * scale
    y1 = (oy - b[3]) * scale
    x1 = (b[2] - ox) * scale
    y0 = (oy - b[1]) * scale
    w = max(10, x1 - x0)
    h = max(10, y0 - y1)
    pad_x = w * 0.08
    pad_y = h * 0.08
    return [round(x0 - pad_x, 1), round(y1 - pad_y, 1), round(w + pad_x * 2, 1), round(h + pad_y * 2, 1)]

print("1. Loading candidate data...")
cand_df = pd.read_csv('/home/rann/src/elections/shapefiles/Candidate_Listing_2026.csv', low_memory=False)
gen_cand = cand_df[cand_df['election_dt'] == '11/03/2026']

senate_cands = {}
for _, row in gen_cand.iterrows():
    c_name = str(row['contest_name']).strip()
    m_s = re.match(r'NC STATE SENATE DISTRICT (\d+)', c_name)
    if m_s:
        s_num = int(m_s.group(1))
        if s_num not in senate_cands: senate_cands[s_num] = []
        b_name = str(row['name_on_ballot']).strip()
        party = str(row['party_candidate']).strip().upper()
        if not any(c['name'] == b_name for c in senate_cands[s_num]):
            senate_cands[s_num].append({'name': b_name, 'party': party})

house_cands = {}
for _, row in gen_cand.iterrows():
    c_name = str(row['contest_name']).strip()
    m_h = re.match(r'NC HOUSE OF REPRESENTATIVES DISTRICT (\d+)', c_name)
    if m_h:
        h_num = int(m_h.group(1))
        if h_num not in house_cands: house_cands[h_num] = []
        b_name = str(row['name_on_ballot']).strip()
        party = str(row['party_candidate']).strip().upper()
        if not any(c['name'] == b_name for c in house_cands[h_num]):
            house_cands[h_num].append({'name': b_name, 'party': party})

print(f"Loaded candidates: {len(senate_cands)} Senate districts, {len(house_cands)} House districts")

print("2. Loading absentee CSV mappings...")
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

print("3. Loading precinct shapefile & dissolving...")
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
gdf = gdf.to_crs(epsg=32119)

print("4. Loading nc_map_data.json precinct forecasts...")
with open('/home/rann/src/elections/2026 analysis/nc_map_data.json') as f:
    map_data = json.load(f)

# Build precinct lookup for forecasts and voter counts
prec_data_lookup = {}
for county, plist in map_data['precincts'].items():
    c_norm = county.upper().strip()
    for p in plist:
        p_id = norm_prec(p['id'])
        p_name = norm_prec(p['name'])
        ev_tot = p['data']['2026']['tot']
        ev_dem = p['data']['2026']['dem']
        ev_rep = p['data']['2026']['rep']
        ev_una = p['data']['2026']['una']
        t_22 = p['data']['2022']['tot']
        t_18 = p['data']['2018']['tot']
        fc = p['forecast']
        pred_dem = fc.get('pred_final_dem', 50.0)
        pred_rep = fc.get('pred_final_rep', 50.0)
        
        info = {
            'county': county,
            'ev_tot': ev_tot,
            'ev_dem': ev_dem,
            'ev_rep': ev_rep,
            'ev_una': ev_una,
            'turnout_22': t_22,
            'turnout_18': t_18,
            'proj_turnout': max(ev_tot * 3, int(t_22 * 1.05) if t_22 > 0 else 1500),
            'pred_dem': pred_dem,
            'pred_rep': pred_rep
        }
        prec_data_lookup[(c_norm, p_id)] = info
        prec_data_lookup[(c_norm, p_name)] = info

print("5. Dissolving Senate districts...")
senate_dissolved = gdf.dissolve(by='senate_dist').reset_index()

senate_results = {}
for _, row in senate_dissolved.iterrows():
    raw_s = str(row['senate_dist']).strip()
    m = re.match(r'NC SENATE DISTRICT (\d+)', raw_s)
    if not m: continue
    s_num = int(m.group(1))
    s_id = f"SD-{s_num:02d}"
    
    # Dissolve geom
    svg_path = geom_to_svg(row.geometry, tolerance=60.0)
    c_pt = row.geometry.representative_point()
    cx = round((c_pt.x - ox) * scale, 1)
    cy = round((oy - c_pt.y) * scale, 1)
    bbox = get_svg_bbox(row.geometry)
    
    # Precincts in this senate district
    sub = gdf[gdf['senate_dist'] == raw_s]
    total_ev = 0
    total_dem_ev = 0
    total_rep_ev = 0
    total_una_ev = 0
    proj_turnout = 0
    proj_dem_votes = 0
    proj_rep_votes = 0
    counties_in_dist = set()
    county_prec_counts = {}
    
    for _, prow in sub.iterrows():
        c_n = prow['c_norm']
        p_n = prow['p_norm']
        enr_n = prow['enr_norm']
        info = prec_data_lookup.get((c_n, p_n)) or prec_data_lookup.get((c_n, enr_n))
        counties_in_dist.add(prow['county_nam'])
        county_prec_counts[prow['county_nam']] = county_prec_counts.get(prow['county_nam'], 0) + 1
        if info:
            total_ev += info['ev_tot']
            total_dem_ev += info['ev_dem']
            total_rep_ev += info['ev_rep']
            total_una_ev += info['ev_una']
            t_proj = info['proj_turnout']
            proj_turnout += t_proj
            proj_dem_votes += t_proj * (info['pred_dem'] / 100.0)
            proj_rep_votes += t_proj * (info['pred_rep'] / 100.0)
            
    if proj_turnout == 0:
        proj_turnout = 80000
        proj_dem_votes = 40000
        proj_rep_votes = 40000

    pred_dem_pct = round((proj_dem_votes / proj_turnout) * 100.0, 2)
    pred_rep_pct = round((proj_rep_votes / proj_turnout) * 100.0, 2)
    margin = round(pred_dem_pct - pred_rep_pct, 2)
    
    # Candidate info
    cands = senate_cands.get(s_num, [])
    dem_c = next((c['name'] for c in cands if c['party'] == 'DEM'), None)
    rep_c = next((c['name'] for c in cands if c['party'] == 'REP'), None)
    other_c = [c['name'] for c in cands if c['party'] not in ['DEM', 'REP']]
    
    # Check uncontested
    is_uncontested = len(cands) == 1
    uncontested_party = cands[0]['party'] if is_uncontested else None
    
    if is_uncontested:
        if uncontested_party == 'DEM':
            pred_dem_pct = 100.0
            pred_rep_pct = 0.0
            margin = 100.0
            p_dem = 100.0
            p_rep = 0.0
            winner_party = 'D'
            winner_name = dem_c or cands[0]['name']
            rating = 'Safe D'
            conf = 'very high confidence'
            ci_str = 'Uncontested DEM'
            proj_str = f"{winner_name} (D) Uncontested"
        else:
            pred_dem_pct = 0.0
            pred_rep_pct = 100.0
            margin = -100.0
            p_dem = 0.0
            p_rep = 100.0
            winner_party = 'R'
            winner_name = rep_c or cands[0]['name']
            rating = 'Safe R'
            conf = 'very high confidence'
            ci_str = 'Uncontested REP'
            proj_str = f"{winner_name} (R) Uncontested"
    else:
        # Competitive normal race
        z = margin / 3.5  # standard error approx 3.5%
        p_dem = round(0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100.0, 1)
        p_rep = round(100.0 - p_dem, 1)
        abs_m = abs(margin)
        if margin > 0:
            winner_party = 'D'
            winner_name = dem_c or 'Democrat'
            last_name = winner_name.split()[-1]
            proj_str = f"{last_name} (D) +{abs_m:.1f}%"
            if abs_m >= 15: rating = 'Safe D'
            elif abs_m >= 8: rating = 'Likely D'
            elif abs_m >= 3: rating = 'Lean D'
            else: rating = 'Tilt D'
        else:
            winner_party = 'R'
            winner_name = rep_c or 'Republican'
            last_name = winner_name.split()[-1]
            proj_str = f"{last_name} (R) +{abs_m:.1f}%"
            if abs_m >= 15: rating = 'Safe R'
            elif abs_m >= 8: rating = 'Likely R'
            elif abs_m >= 3: rating = 'Lean R'
            else: rating = 'Tilt R'
            
        ci_low = round(margin - 6.8, 1)
        ci_high = round(margin + 6.8, 1)
        
        def fmt_m(val):
            return f"D +{val:.1f}%" if val > 0 else (f"R +{abs(val):.1f}%" if val < 0 else "EVEN")
        ci_str = f"{fmt_m(ci_low)} to {fmt_m(ci_high)}"
        conf = 'very high confidence' if abs_m >= 12 else ('high confidence' if abs_m >= 6 else 'moderate confidence')

    senate_results[s_id] = {
        'id': s_id,
        'number': s_num,
        'name': f"NC Senate District {s_num}",
        'region': ", ".join(sorted(counties_in_dist)[:3]) + (f" (+{len(counties_in_dist)-3} more)" if len(counties_in_dist) > 3 else ""),
        'ev_day7_total': total_ev,
        'proj_turnout': proj_turnout,
        'pred_final_dem': pred_dem_pct,
        'pred_final_rep': pred_rep_pct,
        'pred_margin': margin,
        'net_margin_votes': int(round(proj_turnout * (margin / 100.0))),
        'rating': rating,
        'p_dem': p_dem,
        'p_rep': p_rep,
        'call_confidence': conf,
        'ci_str': ci_str,
        'dem_candidate': dem_c,
        'rep_candidate': rep_c,
        'other_candidates': other_c,
        'is_uncontested': is_uncontested,
        'projected_winner_party': winner_party,
        'projected_winner_name': winner_name.split()[-1] if winner_name else winner_party,
        'projected_winner_full': winner_name,
        'projected_margin_str': proj_str,
        'counties': sorted(list(counties_in_dist)),
        'path': svg_path,
        'centroid': [cx, cy],
        'bbox': bbox,
        'flip_status': 'HOLD',
        'is_flip': False
    }

print(f"6. Dissolved {len(senate_results)} Senate districts.")
with open('/home/rann/src/elections/2026 analysis/nc_senate_data.json', 'w') as f:
    json.dump(senate_results, f, indent=2)

print("7. Dissolving House districts...")
house_dissolved = gdf.dissolve(by='house_dist').reset_index()

house_results = {}
for _, row in house_dissolved.iterrows():
    raw_h = str(row['house_dist']).strip()
    m = re.match(r'NC HOUSE OF REPRESENTATIVES DISTRICT (\d+)', raw_h) or re.match(r'NC HOUSE DISTRICT (\d+)', raw_h)
    if not m: continue
    h_num = int(m.group(1))
    h_id = f"HD-{h_num:03d}"
    
    # Dissolve geom
    svg_path = geom_to_svg(row.geometry, tolerance=50.0)
    c_pt = row.geometry.representative_point()
    cx = round((c_pt.x - ox) * scale, 1)
    cy = round((oy - c_pt.y) * scale, 1)
    bbox = get_svg_bbox(row.geometry)
    
    sub = gdf[gdf['house_dist'] == raw_h]
    total_ev = 0
    proj_turnout = 0
    proj_dem_votes = 0
    proj_rep_votes = 0
    counties_in_dist = set()
    
    for _, prow in sub.iterrows():
        c_n = prow['c_norm']
        p_n = prow['p_norm']
        enr_n = prow['enr_norm']
        info = prec_data_lookup.get((c_n, p_n)) or prec_data_lookup.get((c_n, enr_n))
        counties_in_dist.add(prow['county_nam'])
        if info:
            total_ev += info['ev_tot']
            t_proj = info['proj_turnout']
            proj_turnout += t_proj
            proj_dem_votes += t_proj * (info['pred_dem'] / 100.0)
            proj_rep_votes += t_proj * (info['pred_rep'] / 100.0)
            
    if proj_turnout == 0:
        proj_turnout = 35000
        proj_dem_votes = 17500
        proj_rep_votes = 17500

    pred_dem_pct = round((proj_dem_votes / proj_turnout) * 100.0, 2)
    pred_rep_pct = round((proj_rep_votes / proj_turnout) * 100.0, 2)
    margin = round(pred_dem_pct - pred_rep_pct, 2)
    
    # Candidates
    cands = house_cands.get(h_num, [])
    dem_c = next((c['name'] for c in cands if c['party'] == 'DEM'), None)
    rep_c = next((c['name'] for c in cands if c['party'] == 'REP'), None)
    other_c = [c['name'] for c in cands if c['party'] not in ['DEM', 'REP']]
    is_uncontested = len(cands) == 1
    uncontested_party = cands[0]['party'] if is_uncontested else None
    
    if is_uncontested:
        if uncontested_party == 'DEM':
            pred_dem_pct = 100.0
            pred_rep_pct = 0.0
            margin = 100.0
            p_dem = 100.0
            p_rep = 0.0
            winner_party = 'D'
            winner_name = dem_c or cands[0]['name']
            rating = 'Safe D'
            conf = 'very high confidence'
            ci_str = 'Uncontested DEM'
            proj_str = f"{winner_name} (D) Uncontested"
        else:
            pred_dem_pct = 0.0
            pred_rep_pct = 100.0
            margin = -100.0
            p_dem = 0.0
            p_rep = 100.0
            winner_party = 'R'
            winner_name = rep_c or cands[0]['name']
            rating = 'Safe R'
            conf = 'very high confidence'
            ci_str = 'Uncontested REP'
            proj_str = f"{winner_name} (R) Uncontested"
    else:
        z = margin / 4.0
        p_dem = round(0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100.0, 1)
        p_rep = round(100.0 - p_dem, 1)
        abs_m = abs(margin)
        if margin > 0:
            winner_party = 'D'
            winner_name = dem_c or 'Democrat'
            last_name = winner_name.split()[-1]
            proj_str = f"{last_name} (D) +{abs_m:.1f}%"
            if abs_m >= 15: rating = 'Safe D'
            elif abs_m >= 8: rating = 'Likely D'
            elif abs_m >= 3: rating = 'Lean D'
            else: rating = 'Tilt D'
        else:
            winner_party = 'R'
            winner_name = rep_c or 'Republican'
            last_name = winner_name.split()[-1]
            proj_str = f"{last_name} (R) +{abs_m:.1f}%"
            if abs_m >= 15: rating = 'Safe R'
            elif abs_m >= 8: rating = 'Likely R'
            elif abs_m >= 3: rating = 'Lean R'
            else: rating = 'Tilt R'
            
        ci_low = round(margin - 7.8, 1)
        ci_high = round(margin + 7.8, 1)
        def fmt_m(val):
            return f"D +{val:.1f}%" if val > 0 else (f"R +{abs(val):.1f}%" if val < 0 else "EVEN")
        ci_str = f"{fmt_m(ci_low)} to {fmt_m(ci_high)}"
        conf = 'very high confidence' if abs_m >= 14 else ('high confidence' if abs_m >= 7 else 'moderate confidence')

    house_results[h_id] = {
        'id': h_id,
        'number': h_num,
        'name': f"NC House District {h_num}",
        'region': ", ".join(sorted(counties_in_dist)[:3]) + (f" (+{len(counties_in_dist)-3} more)" if len(counties_in_dist) > 3 else ""),
        'ev_day7_total': total_ev,
        'proj_turnout': proj_turnout,
        'pred_final_dem': pred_dem_pct,
        'pred_final_rep': pred_rep_pct,
        'pred_margin': margin,
        'net_margin_votes': int(round(proj_turnout * (margin / 100.0))),
        'rating': rating,
        'p_dem': p_dem,
        'p_rep': p_rep,
        'call_confidence': conf,
        'ci_str': ci_str,
        'dem_candidate': dem_c,
        'rep_candidate': rep_c,
        'other_candidates': other_c,
        'is_uncontested': is_uncontested,
        'projected_winner_party': winner_party,
        'projected_winner_name': winner_name.split()[-1] if winner_name else winner_party,
        'projected_winner_full': winner_name,
        'projected_margin_str': proj_str,
        'counties': sorted(list(counties_in_dist)),
        'path': svg_path,
        'centroid': [cx, cy],
        'bbox': bbox,
        'flip_status': 'HOLD',
        'is_flip': False
    }

print(f"8. Dissolved {len(house_results)} House districts.")
with open('/home/rann/src/elections/2026 analysis/nc_house_data.json', 'w') as f:
    json.dump(house_results, f, indent=2)

print("SUCCESS: Both nc_senate_data.json and nc_house_data.json generated successfully!")

