#!/usr/bin/env python3
"""
NC Election Night Needle Generator (rannbar-on.com/needle)
---------------------------------------------------------
Constructs the New York Times-style probabilistic Needle forecast dashboard
for North Carolina General Assembly races (all 50 NC Senate and 120 NC House districts)
at the precinct level, along with chamber control needles for total Dem seats.

Outputs:
  - needle/needle_data.json
  - needle/index.html
  - needle.html
"""

import os
import re
import json
import math
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'needle')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def build_needle_dataset():
    print("1. Loading legislative models & metadata...")
    with open(os.path.join(BASE_DIR, 'nc_senate_data.json')) as f:
        senate_meta = json.load(f)
    with open(os.path.join(BASE_DIR, 'nc_house_data.json')) as f:
        house_meta = json.load(f)

    print("2. Parsing precinct-level 2024 returns and baseline models...")
    txt_path = '/home/rann/Documents/elections/voterlist/results_pct_20241105.txt'
    if not os.path.exists(txt_path):
        txt_path = '/home/rann/.gemini/antigravity/brain/4b3aec10-8dbc-428a-9aa3-166e86178a59/scratch/historical_results/results_pct_20241105.txt'

    df = pd.read_csv(txt_path, sep='\t',
                     usecols=['County', 'Precinct', 'Contest Name', 'Choice Party', 'Total Votes'])

    # Build universal precinct AG baseline
    ag_df = df[df['Contest Name'] == 'NC ATTORNEY GENERAL'].copy()
    ag_pivot = ag_df.pivot_table(index=['County', 'Precinct'], columns='Choice Party', values='Total Votes', aggfunc='sum', fill_value=0).reset_index()
    ag_map = {}
    for _, row in ag_pivot.iterrows():
        c = str(row['County']).upper().strip()
        p = str(row['Precinct']).upper().strip()
        dem_v = int(row.get('DEM', 0))
        rep_v = int(row.get('REP', 0))
        tot = dem_v + rep_v
        m = (dem_v - rep_v) / tot * 100.0 if tot > 0 else 0.0
        ag_map[(c, p)] = {'dem': dem_v, 'rep': rep_v, 'tot': tot, 'margin': m}

    def process_chamber(chamber_name, contest_filter, meta_dict):
        sub_df = df[df['Contest Name'].str.contains(contest_filter, na=False) & ~df['Contest Name'].str.contains('US HOUSE', na=False)].copy()
        piv = sub_df.pivot_table(index=['Contest Name', 'County', 'Precinct'], columns='Choice Party', values='Total Votes', aggfunc='sum', fill_value=0).reset_index()
        
        districts = {}
        for c_name, grp in piv.groupby('Contest Name'):
            m_num = re.search(r'DISTRICT\s+(\d+)', c_name)
            if not m_num: continue
            d_num = int(m_num.group(1))
            d_key = f"SD-{d_num:02d}" if chamber_name == "senate" else f"HD-{d_num:03d}"
            
            meta = meta_dict.get(d_key, {})
            proj_turnout = meta.get('proj_turnout', 50000)
            pred_margin = meta.get('pred_margin', 0.0)
            dem_candidate = meta.get('dem_candidate', 'Democratic Candidate')
            rep_candidate = meta.get('rep_candidate', 'Republican Candidate')
            rating = meta.get('rating', 'Toss Up')
            incumbent_party = meta.get('incumbent_party', 'R')
            p_dem = meta.get('p_dem', 50.0)
            is_uncontested = meta.get('is_uncontested', False)
            
            tot_2024_votes = grp['DEM'].sum() + grp['REP'].sum() + (grp['LIB'].sum() if 'LIB' in grp.columns else 0)
            has_both_parties = (grp['DEM'].sum() > 0) and (grp['REP'].sum() > 0)
            
            precinct_list = []
            for _, row in grp.iterrows():
                c = str(row['County']).upper().strip()
                p = str(row['Precinct']).upper().strip()
                dem_24 = int(row.get('DEM', 0))
                rep_24 = int(row.get('REP', 0))
                tot_24 = dem_24 + rep_24 + (int(row.get('LIB', 0)) if 'LIB' in grp.columns else 0)
                
                if has_both_parties and (dem_24 + rep_24) > 0:
                    raw_m24 = (dem_24 - rep_24) / (dem_24 + rep_24) * 100.0
                    dist_24_dem = grp['DEM'].sum()
                    dist_24_rep = grp['REP'].sum()
                    dist_24_m = (dist_24_dem - dist_24_rep) / (dist_24_dem + dist_24_rep) * 100.0
                    swing_to_apply = pred_margin - dist_24_m
                    bench_m = max(-100.0, min(100.0, raw_m24 + swing_to_apply))
                else:
                    ag_prec = ag_map.get((c, p))
                    if ag_prec and ag_prec['tot'] > 0:
                        raw_m24 = ag_prec['margin']
                        rel_lean = raw_m24 - 3.6
                        bench_m = max(-100.0, min(100.0, pred_margin + rel_lean * 0.75))
                    else:
                        bench_m = pred_margin
                
                weight = tot_24 / tot_2024_votes if tot_2024_votes > 0 else (1.0 / len(grp))
                prec_proj_turnout = int(round(proj_turnout * weight))
                if prec_proj_turnout < 10: prec_proj_turnout = max(10, tot_24)
                
                cushion = int(round(prec_proj_turnout * (bench_m / 100.0)))
                bench_dem = int(round(prec_proj_turnout * (100.0 + bench_m) / 200.0))
                bench_rep = prec_proj_turnout - bench_dem
                
                precinct_list.append({
                    "id": f"{c}-{p}",
                    "county": c,
                    "precinct": p,
                    "hist_turnout_2024": int(tot_24),
                    "proj_turnout": int(prec_proj_turnout),
                    "bench_margin": round(bench_m, 2),
                    "bench_dem": int(bench_dem),
                    "bench_rep": int(bench_rep),
                    "target_cushion": int(cushion)
                })
                
            districts[d_key] = {
                "id": d_key,
                "number": d_num,
                "name": meta.get('name', f"NC {chamber_name.title()} District {d_num}"),
                "chamber": chamber_name,
                "dem_candidate": dem_candidate,
                "rep_candidate": rep_candidate,
                "incumbent_party": incumbent_party,
                "rating": rating,
                "p_dem": p_dem,
                "p_rep": round(100.0 - p_dem, 1),
                "pred_margin": round(pred_margin, 2),
                "proj_turnout": proj_turnout,
                "is_uncontested": is_uncontested,
                "region": meta.get('region', ''),
                "counties": meta.get('counties', []),
                "sigma": 3.5 if chamber_name == "senate" else 3.8,
                "precinct_count": len(precinct_list),
                "precincts": precinct_list
            }
        return districts

    senate_districts = process_chamber("senate", "STATE SENATE", senate_meta)
    house_districts = process_chamber("house", "HOUSE OF REPRESENTATIVES", house_meta)

    dem_senate_exp = sum(d['p_dem'] / 100.0 for d in senate_districts.values())
    dem_house_exp = sum(d['p_dem'] / 100.0 for d in house_districts.values())

    output = {
        "generated_at": "2026-10-31T17:00:00-04:00",
        "chambers": {
            "senate": {
                "total_seats": 50,
                "majority_threshold": 26,
                "supermajority_breaker_threshold": 20,
                "baseline_exp_dem": round(dem_senate_exp, 1),
                "baseline_exp_rep": round(50.0 - dem_senate_exp, 1),
                "sigma_seats": 1.7,
                "districts": senate_districts
            },
            "house": {
                "total_seats": 120,
                "majority_threshold": 61,
                "supermajority_breaker_threshold": 49,
                "baseline_exp_dem": round(dem_house_exp, 1),
                "baseline_exp_rep": round(120.0 - dem_house_exp, 1),
                "sigma_seats": 2.8,
                "districts": house_districts
            }
        }
    }

    out_json = os.path.join(OUTPUT_DIR, 'needle_data.json')
    with open(out_json, 'w') as f:
        json.dump(output, f, separators=(',', ':'))
    print(f"Generated {out_json} successfully.")
    return output

if __name__ == '__main__':
    build_needle_dataset()
