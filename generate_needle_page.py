#!/usr/bin/env python3
"""
NC Election Night Needle Generator (rannbar-on.com/needle)
---------------------------------------------------------
Constructs the New York Times-style probabilistic Needle forecast dashboard
for North Carolina General Assembly races (all 50 NC Senate and 120 NC House districts)
at the precinct level with full 3-mode voting method decomposition (Absentee Mail,
One-Stop Early Voting, Election Day In-Person), along with marquee statewide races
(US Senate, NC Supreme Court, NC Court of Appeals Seats 1-3), interactive vector maps,
and chamber control needles.

Outputs:
  - needle/needle_data.json
  - needle/index.html
  - needle.html
"""

import os
import re
import json
import math
import shutil
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'needle')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def build_needle_dataset():
    out_json = os.path.join(OUTPUT_DIR, 'needle_data.json')
    senate_json = os.path.join(BASE_DIR, 'nc_senate_data.json')

    # If raw legislative metadata is not found but compiled needle_data.json exists, load and refresh it
    if not os.path.exists(senate_json) and os.path.exists(out_json):
        print(f"Loading existing compiled dataset from {out_json} and refreshing forecasts...")
        with open(out_json, 'r') as f:
            output = json.load(f)

        from datetime import datetime
        output["generated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-05:00")

        # Refresh statewide races from nc_map_base.json if available
        map_base_path = os.path.join(BASE_DIR, 'nc_map_base.json')
        if os.path.exists(map_base_path):
            try:
                with open(map_base_path, 'r') as mf:
                    mb = json.load(mf)
                st_fc = mb.get('state', {}).get('forecast', {})
                if st_fc and 'US-SENATE' in output.get('statewide', {}):
                    us_fc = st_fc.get('races', {}).get('us_senate', st_fc)
                    output['statewide']['US-SENATE']['pred_margin'] = us_fc.get('pred_margin', output['statewide']['US-SENATE']['pred_margin'])
                    output['statewide']['US-SENATE']['p_dem'] = us_fc.get('p_dem', output['statewide']['US-SENATE']['p_dem'])
                    output['statewide']['US-SENATE']['p_rep'] = us_fc.get('p_rep', output['statewide']['US-SENATE']['p_rep'])
                    output['statewide']['US-SENATE']['rating'] = us_fc.get('rating', output['statewide']['US-SENATE']['rating'])
                if st_fc and 'NC-SC' in output.get('statewide', {}):
                    sc_fc = st_fc.get('races', {}).get('supreme_court', {})
                    if sc_fc:
                        output['statewide']['NC-SC']['pred_margin'] = sc_fc.get('pred_margin', output['statewide']['NC-SC']['pred_margin'])
                        output['statewide']['NC-SC']['p_dem'] = sc_fc.get('p_dem', output['statewide']['NC-SC']['p_dem'])
                        output['statewide']['NC-SC']['p_rep'] = sc_fc.get('p_rep', output['statewide']['NC-SC']['p_rep'])
                        output['statewide']['NC-SC']['rating'] = sc_fc.get('rating', output['statewide']['NC-SC']['rating'])
            except Exception as e:
                print(f"Warning: Could not refresh statewide forecasts from nc_map_base: {e}")

        try:
            with open(out_json, 'w') as f:
                json.dump(output, f, separators=(',', ':'))
            print(f"Successfully refreshed {out_json} (size: {os.path.getsize(out_json)/1024:.1f} KB).")
        except OSError as e:
            print(f"Notice: {out_json} is read-only in this environment ({e}), using existing dataset.")
        return output

    print("1. Loading legislative models & base geometries...")
    with open(senate_json) as f:
        senate_meta = json.load(f)
    with open(os.path.join(BASE_DIR, 'nc_house_data.json')) as f:
        house_meta = json.load(f)
    with open(os.path.join(BASE_DIR, 'nc_cd_data.json')) as f:
        cd_meta = json.load(f)
    with open(os.path.join(BASE_DIR, 'nc_map_base.json')) as f:
        county_base = json.load(f)

    county_paths = {c['name'].upper(): {
        'path': c['path'],
        'bbox': c.get('bbox'),
        'centroid': c.get('centroid')
    } for c in county_base.get('counties', [])}

    print("2. Parsing benchmark sheet county dataset...")
    benchmark_gs = '/home/rann/src/nc-election-night-benchmark/create_nc_benchmark.gs'
    if not os.path.exists(benchmark_gs):
        benchmark_gs = '/home/rann/.config/Code/User/History/727a5dbc/GSEm.gs'
    
    with open(benchmark_gs) as f:
        gs_text = f.read()

    start = gs_text.find('function getFullCountyCandidateDataset_()')
    end = gs_text.find('function applyOverUnderConditionalFormatting_', start)
    code = gs_text[start:end]
    bench_rows = re.findall(r'\[\s*\'([^\']+)\'\s*,\s*\'([^\']+)\'\s*,\s*([0-9\.]+)\s*,\s*([\-0-9\.]+)\s*,\s*([\-0-9\.]+)\s*,\s*([\-0-9\.]+)\s*,\s*([\-0-9\.]+)\s*,\s*([\-0-9\.]+)\s*\]', code)

    print("3. Parsing precinct-level 2024 returns with voting method breakdown (Mail, Early, E-Day)...")
    txt_path = '/home/rann/Documents/elections/voterlist/results_pct_20241105.txt'
    if not os.path.exists(txt_path):
        txt_path = '/home/rann/.gemini/antigravity/brain/4b3aec10-8dbc-428a-9aa3-166e86178a59/scratch/historical_results/results_pct_20241105.txt'

    df = pd.read_csv(txt_path, sep='\t',
                     usecols=['County', 'Precinct', 'Contest Name', 'Choice Party', 
                              'Election Day', 'Early Voting', 'Absentee by Mail', 'Total Votes'])

    # Build universal precinct baseline with 3-mode decomposition from AG contest
    ag_df = df[df['Contest Name'] == 'NC ATTORNEY GENERAL'].copy()
    ag_pivot = ag_df.pivot_table(index=['County', 'Precinct'], columns='Choice Party',
                                 values=['Election Day', 'Early Voting', 'Absentee by Mail', 'Total Votes'],
                                 aggfunc='sum', fill_value=0)

    # Load exact voter-level historical precinct mode ratios
    prec_hist_modes_path = os.path.join(BASE_DIR, 'nc_precinct_historical_modes.json')
    if os.path.exists(prec_hist_modes_path):
        with open(prec_hist_modes_path) as f:
            prec_hist_modes = json.load(f)
        print("Loaded " + str(len(prec_hist_modes)) + " exact precinct historical mode profiles from " + prec_hist_modes_path)
    else:
        prec_hist_modes = {}

    prec_modes = {}
    ag_map = {}
    for (c, p) in ag_pivot.index:
        c_str = str(c).upper().strip()
        p_str = str(p).upper().strip()
        row = ag_pivot.loc[(c, p)]

        m_dem = int(row.get(('Absentee by Mail', 'DEM'), 0))
        m_rep = int(row.get(('Absentee by Mail', 'REP'), 0))
        e_dem = int(row.get(('Early Voting', 'DEM'), 0))
        e_rep = int(row.get(('Early Voting', 'REP'), 0))
        ed_dem = int(row.get(('Election Day', 'DEM'), 0))
        ed_rep = int(row.get(('Election Day', 'REP'), 0))
        t_dem = int(row.get(('Total Votes', 'DEM'), 0))
        t_rep = int(row.get(('Total Votes', 'REP'), 0))

        t_tot = t_dem + t_rep
        m_tot = m_dem + m_rep
        e_tot = e_dem + e_rep
        ed_tot = ed_dem + ed_rep

        m_all = (t_dem - t_rep) / t_tot * 100.0 if t_tot > 0 else 0.0
        m_mail = (m_dem - m_rep) / m_tot * 100.0 if m_tot > 0 else m_all + 30.6
        m_early = (e_dem - e_rep) / e_tot * 100.0 if e_tot > 0 else m_all + 0.5
        m_eday = (ed_dem - ed_rep) / ed_tot * 100.0 if ed_tot > 0 else m_all - 9.6

        ag_map[(c_str, p_str)] = {'dem': t_dem, 'rep': t_rep, 'tot': t_tot, 'margin': m_all}

        # Exact precinct voter-level share from matched absentee file if available
        hist_p = prec_hist_modes.get(f"{c_str}-{p_str}")
        if hist_p:
            share_mail = hist_p['share_mail']
            share_early = hist_p['share_early']
            share_eday = hist_p['share_eday']
        else:
            share_mail = m_tot / t_tot if t_tot > 0 else 0.052
            share_early = e_tot / t_tot if t_tot > 0 else 0.741
            share_eday = ed_tot / t_tot if t_tot > 0 else 0.207

        prec_modes[(c_str, p_str)] = {
            'share_mail': share_mail,
            'share_early': share_early,
            'share_eday': share_eday,
            'diff_mail': m_mail - m_all,
            'diff_early': m_early - m_all,
            'diff_eday': m_eday - m_all
        }

    # Build county-level mode breakdown from AG
    county_piv = ag_df.pivot_table(index='County', columns='Choice Party',
                                   values=['Election Day', 'Early Voting', 'Absentee by Mail', 'Total Votes'],
                                   aggfunc='sum', fill_value=0)
    county_modes = {}
    for c in county_piv.index:
        c_up = str(c).upper().strip()
        row = county_piv.loc[c]
        m_dem = int(row.get(('Absentee by Mail', 'DEM'), 0))
        m_rep = int(row.get(('Absentee by Mail', 'REP'), 0))
        e_dem = int(row.get(('Early Voting', 'DEM'), 0))
        e_rep = int(row.get(('Early Voting', 'REP'), 0))
        ed_dem = int(row.get(('Election Day', 'DEM'), 0))
        ed_rep = int(row.get(('Election Day', 'REP'), 0))
        t_dem = int(row.get(('Total Votes', 'DEM'), 0))
        t_rep = int(row.get(('Total Votes', 'REP'), 0))

        t_tot = t_dem + t_rep
        m_tot = m_dem + m_rep
        e_tot = e_dem + e_rep
        ed_tot = ed_dem + ed_rep

        m_all = (t_dem - t_rep) / t_tot * 100.0 if t_tot > 0 else 0.0
        m_mail = (m_dem - m_rep) / m_tot * 100.0 if m_tot > 0 else m_all + 30.6
        m_early = (e_dem - e_rep) / e_tot * 100.0 if e_tot > 0 else m_all + 0.5
        m_eday = (ed_dem - ed_rep) / ed_tot * 100.0 if ed_tot > 0 else m_all - 9.6

        county_modes[c_up] = {
            'share_mail': m_tot / t_tot if t_tot > 0 else 0.052,
            'share_early': e_tot / t_tot if t_tot > 0 else 0.741,
            'share_eday': ed_tot / t_tot if t_tot > 0 else 0.207,
            'diff_mail': m_mail - m_all,
            'diff_early': m_early - m_all,
            'diff_eday': m_eday - m_all
        }

    print("4. Building statewide marquee races with mode benchmarks...")
    def build_statewide_race(key, title, short_title, dem_cand, rep_cand, target_col_idx, baseline_m, sigma, rating):
        counties = []
        tot_proj_turnout = 0

        # Exact statewide calibration: shift county benchmarks so their volume-weighted sum exactly matches baseline_m
        raw_tot_turnout = sum(float(r[2]) for r in bench_rows)
        raw_tot_dem = sum(round(float(r[2]) * (100.0 + float(r[target_col_idx]) * 100.0) / 200.0) for r in bench_rows)
        raw_statewide_m = (raw_tot_dem - (raw_tot_turnout - raw_tot_dem)) / raw_tot_turnout * 100.0 if raw_tot_turnout > 0 else 0.0
        calib_shift = baseline_m - raw_statewide_m

        for r in bench_rows:
            c_name = r[0]
            c_up = c_name.upper().strip()
            cluster = r[1]
            turnout = int(float(r[2]))
            tot_proj_turnout += turnout
            target_m = round(max(-100.0, min(100.0, float(r[target_col_idx]) * 100.0 + calib_shift)), 2)
            cushion = int(round(turnout * (target_m / 100.0)))
            geom = county_paths.get(c_up, {})

            # Mode benchmark calculations for county
            c_mode = county_modes.get(c_up, {
                'share_mail': 0.052, 'share_early': 0.741, 'share_eday': 0.207,
                'diff_mail': 30.6, 'diff_early': 0.5, 'diff_eday': -9.6
            })
            c_m_mail = max(-100.0, min(100.0, target_m + c_mode['diff_mail']))
            c_m_early = max(-100.0, min(100.0, target_m + c_mode['diff_early']))
            c_m_eday = max(-100.0, min(100.0, target_m + c_mode['diff_eday']))

            c_proj_mail = int(round(turnout * c_mode['share_mail']))
            c_proj_early = int(round(turnout * c_mode['share_early']))
            c_proj_eday = max(0, turnout - c_proj_mail - c_proj_early)

            c_cush_mail = int(round(c_proj_mail * (c_m_mail / 100.0)))
            c_cush_early = int(round(c_proj_early * (c_m_early / 100.0)))
            c_cush_eday = int(round(c_proj_eday * (c_m_eday / 100.0)))

            counties.append({
                'name': c_name,
                'county': c_up,
                'cluster': cluster,
                'proj_turnout': turnout,
                'bench_margin': target_m,
                'target_cushion': cushion,
                'path': geom.get('path', ''),
                'bbox': geom.get('bbox', []),
                'centroid': geom.get('centroid', []),
                'modes': {
                    'mail': {
                        'proj': c_proj_mail,
                        'bench_m': round(c_m_mail, 2),
                        'cushion': c_cush_mail
                    },
                    'early': {
                        'proj': c_proj_early,
                        'bench_m': round(c_m_early, 2),
                        'cushion': c_cush_early
                    },
                    'eday': {
                        'proj': c_proj_eday,
                        'bench_m': round(c_m_eday, 2),
                        'cushion': c_cush_eday
                    }
                }
            })
        
        z = baseline_m / sigma
        p_dem = round(0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100.0, 1)
        
        return {
            'id': key,
            'title': title,
            'short_title': short_title,
            'dem_candidate': dem_cand,
            'rep_candidate': rep_cand,
            'pred_margin': baseline_m,
            'proj_turnout': tot_proj_turnout,
            'sigma': sigma,
            'rating': rating,
            'p_dem': p_dem,
            'p_rep': round(100.0 - p_dem, 1),
            'counties': counties
        }

    statewide_races = {
        'US-SENATE': build_statewide_race('US-SENATE', '2026 US Senate: Roy Cooper (D) vs. Michael Whatley (R)', 'US Senate', 'Roy Cooper', 'Michael Whatley', 3, 2.5, 3.65, 'Lean D'),
        'NC-SC': build_statewide_race('NC-SC', '2026 NC Supreme Court: Anita Earls (D - Incumbent) vs. Sarah Stevens (R)', 'NC Supreme Court', 'Anita Earls', 'Sarah Stevens', 4, 1.0, 3.90, 'Toss Up / Tilt D'),
        'NC-COA-1': build_statewide_race('NC-COA-1', '2026 NC Court of Appeals Seat 1: John S. Arrowood (D - Incumbent) vs. Michael C. Byrne (R)', 'NC CoA Seat 1', 'John S. Arrowood', 'Michael C. Byrne', 5, 0.5, 4.10, 'Toss Up / Tilt D'),
        'NC-COA-2': build_statewide_race('NC-COA-2', '2026 NC Court of Appeals Seat 2: Tobias (Toby) Hampson (D - Incumbent) vs. George Cooper Bell (R)', 'NC CoA Seat 2', 'Tobias (Toby) Hampson', 'George Cooper Bell', 5, 0.5, 4.10, 'Toss Up / Tilt D'),
        'NC-COA-3': build_statewide_race('NC-COA-3', '2026 NC Court of Appeals Seat 3: Christine Marie Walczyk (D) vs. Craig Collins (R)', 'NC CoA Seat 3', 'Christine Marie Walczyk', 'Craig Collins', 5, 0.5, 4.10, 'Toss Up / Tilt D')
    }

    print("4b. Building constitutional amendments with county & mode decomposition...")
    def build_amendment(key, title, short_title, ballot_q, baseline_m, sigma, rating, p_against, p_for, elast, shift):
        counties = []
        tot_proj_turnout = 0
        for r in bench_rows:
            c_name = r[0]
            c_up = c_name.upper().strip()
            cluster = r[1]
            turnout = int(float(r[2]))
            tot_proj_turnout += turnout
            sc_m = float(r[4]) * 100.0
            target_m = round(max(-100.0, min(100.0, sc_m * elast + shift)), 2)
            cushion = int(round(turnout * (target_m / 100.0)))
            geom = county_paths.get(c_up, {})

            c_mode = county_modes.get(c_up, {
                'share_mail': 0.052, 'share_early': 0.741, 'share_eday': 0.207,
                'diff_mail': 30.6, 'diff_early': 0.5, 'diff_eday': -9.6
            })
            c_m_mail = max(-100.0, min(100.0, target_m + c_mode['diff_mail'] * 0.7))
            c_m_early = max(-100.0, min(100.0, target_m + c_mode['diff_early'] * 0.7))
            c_m_eday = max(-100.0, min(100.0, target_m + c_mode['diff_eday'] * 0.7))

            c_proj_mail = int(round(turnout * c_mode['share_mail']))
            c_proj_early = int(round(turnout * c_mode['share_early']))
            c_proj_eday = max(0, turnout - c_proj_mail - c_proj_early)

            c_cush_mail = int(round(c_proj_mail * (c_m_mail / 100.0)))
            c_cush_early = int(round(c_proj_early * (c_m_early / 100.0)))
            c_cush_eday = int(round(c_proj_eday * (c_m_eday / 100.0)))

            counties.append({
                'name': c_name,
                'county': c_up,
                'cluster': cluster,
                'proj_turnout': turnout,
                'bench_margin': target_m,
                'target_cushion': cushion,
                'path': geom.get('path', ''),
                'bbox': geom.get('bbox', []),
                'centroid': geom.get('centroid', []),
                'modes': {
                    'mail': {
                        'proj': c_proj_mail,
                        'bench_m': round(c_m_mail, 2),
                        'cushion': c_cush_mail
                    },
                    'early': {
                        'proj': c_proj_early,
                        'bench_m': round(c_m_early, 2),
                        'cushion': c_cush_early
                    },
                    'eday': {
                        'proj': c_proj_eday,
                        'bench_m': round(c_m_eday, 2),
                        'cushion': c_cush_eday
                    }
                }
            })

        return {
            'id': key,
            'title': title,
            'short_title': short_title,
            'ballot_question': ballot_q,
            'dem_candidate': 'Against (No)',
            'rep_candidate': 'For (Yes)',
            'dem_stance': 'Against (No)',
            'rep_stance': 'For (Yes)',
            'is_amendment': True,
            'pred_margin': baseline_m,
            'proj_turnout': tot_proj_turnout,
            'sigma': sigma,
            'rating': rating,
            'p_dem': p_against,
            'p_rep': p_for,
            'counties': counties
        }

    amendments_data = {
        'NC-CONST-AMEND-1': build_amendment(
            'NC-CONST-AMEND-1',
            'Constitutional Amendment 1: Require Photo ID for All Voters',
            'Photo ID Amendment',
            'Constitutional requirement for photo ID across all voting methods, including in-person and mail-in/absentee ballots.',
            -13.7, 2.1, 'Likely For (Passes)', 0.1, 99.9, 0.85, -14.734
        ),
        'NC-CONST-AMEND-2': build_amendment(
            'NC-CONST-AMEND-2',
            'Constitutional Amendment 2: 3.5% Income Tax Cap Amendment',
            '3.5% Income Tax Cap',
            'Reduces the constitutional ceiling on maximum personal and corporate state income tax rate from 7.0% to 3.5%.',
            -6.9, 2.2, 'Lean For (Passes)', 5.2, 94.8, 0.82, -7.898
        ),
        'NC-CONST-AMEND-3': build_amendment(
            'NC-CONST-AMEND-3',
            'Constitutional Amendment 3: Property Tax Levy Limit Amendment',
            'Property Tax Levy Limit',
            'Requires General Assembly to impose statutory restrictions and caps on local government property tax increases.',
            2.9, 2.3, 'Toss Up / Lean Against', 68.4, 31.6, 0.80, 1.926
        )
    }

    # Add amendments directly into statewide_races dictionary as well for universal lookup
    for ak, av in amendments_data.items():
        statewide_races[ak] = av

    print("5. Building legislative chambers with precinct-level mode benchmarks...")
    def process_chamber(chamber_name, contest_filter, meta_dict):
        if chamber_name == "senate":
            sub_df = df[df['Contest Name'].str.contains('STATE SENATE', na=False)].copy()
        elif chamber_name == "house":
            sub_df = df[df['Contest Name'].str.contains('HOUSE OF REPRESENTATIVES', na=False) & ~df['Contest Name'].str.contains('US HOUSE', na=False)].copy()
        else: # congress
            sub_df = df[df['Contest Name'].str.contains('US HOUSE OF REPRESENTATIVES', na=False)].copy()
        piv = sub_df.pivot_table(index=['Contest Name', 'County', 'Precinct'], columns='Choice Party', values='Total Votes', aggfunc='sum', fill_value=0).reset_index()
        
        districts = {}
        for c_name, grp in piv.groupby('Contest Name'):
            m_num = re.search(r'DISTRICT\s+(\d+)', c_name)
            if not m_num: continue
            d_num = int(m_num.group(1))
            if chamber_name == "senate":
                d_key = f"SD-{d_num:02d}"
            elif chamber_name == "house":
                d_key = f"HD-{d_num:03d}"
            else:
                d_key = f"NC-{d_num:02d}"
            
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

                # Mode-specific decomposition
                mode_info = prec_modes.get((c, p), {
                    'share_mail': 0.052, 'share_early': 0.741, 'share_eday': 0.207,
                    'diff_mail': 30.6, 'diff_early': 0.5, 'diff_eday': -9.6
                })

                bench_m_mail = max(-100.0, min(100.0, bench_m + mode_info['diff_mail']))
                bench_m_early = max(-100.0, min(100.0, bench_m + mode_info['diff_early']))
                bench_m_eday = max(-100.0, min(100.0, bench_m + mode_info['diff_eday']))

                proj_mail = int(round(prec_proj_turnout * mode_info['share_mail']))
                proj_early = int(round(prec_proj_turnout * mode_info['share_early']))
                proj_eday = max(0, prec_proj_turnout - proj_mail - proj_early)

                cushion_mail = int(round(proj_mail * (bench_m_mail / 100.0)))
                cushion_early = int(round(proj_early * (bench_m_early / 100.0)))
                cushion_eday = int(round(proj_eday * (bench_m_eday / 100.0)))
                
                precinct_list.append({
                    "id": f"{c}-{p}",
                    "county": c,
                    "precinct": p,
                    "hist_turnout_2024": int(tot_24),
                    "proj_turnout": int(prec_proj_turnout),
                    "bench_margin": round(bench_m, 2),
                    "bench_dem": int(bench_dem),
                    "bench_rep": int(bench_rep),
                    "target_cushion": int(cushion),
                    "modes": {
                        "mail": {
                            "proj": proj_mail,
                            "bench_m": round(bench_m_mail, 2),
                            "cushion": cushion_mail
                        },
                        "early": {
                            "proj": proj_early,
                            "bench_m": round(bench_m_early, 2),
                            "cushion": cushion_early
                        },
                        "eday": {
                            "proj": proj_eday,
                            "bench_m": round(bench_m_eday, 2),
                            "cushion": cushion_eday
                        }
                    }
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
                "sigma": 3.5 if chamber_name == "senate" else (3.8 if chamber_name == "house" else 2.8),
                "path": meta.get('path', ''),
                "bbox": meta.get('bbox', []),
                "centroid": meta.get('centroid', []),
                "precinct_count": len(precinct_list),
                "precincts": precinct_list
            }
        return districts

    senate_districts = process_chamber("senate", "STATE SENATE", senate_meta)
    house_districts = process_chamber("house", "HOUSE OF REPRESENTATIVES", house_meta)
    congress_districts = process_chamber("congress", "US HOUSE OF REPRESENTATIVES", cd_meta)

    dem_senate_exp = sum(d['p_dem'] / 100.0 for d in senate_districts.values())
    dem_house_exp = sum(d['p_dem'] / 100.0 for d in house_districts.values())
    dem_congress_exp = sum(d['p_dem'] / 100.0 for d in congress_districts.values())

    output = {
        "generated_at": "2026-10-31T17:45:00-04:00",
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
            },
            "congress": {
                "total_seats": 14,
                "majority_threshold": 8,
                "baseline_exp_dem": round(dem_congress_exp, 1),
                "baseline_exp_rep": round(14.0 - dem_congress_exp, 1),
                "sigma_seats": 0.8,
                "districts": congress_districts
            }
        },
        "statewide": statewide_races,
        "amendments": amendments_data
    }

    out_json = os.path.join(OUTPUT_DIR, 'needle_data.json')
    with open(out_json, 'w') as f:
        json.dump(output, f, separators=(',', ':'))
    print(f"Generated {out_json} successfully (size: {os.path.getsize(out_json)/1024:.1f} KB).")
    return output



def update_needle_html_files():
    print("6. Updating needle HTML dashboards...")
    index_path = os.path.join(OUTPUT_DIR, 'index.html')
    needle_root = os.path.join(BASE_DIR, 'needle.html')
    data_path = os.path.join(OUTPUT_DIR, 'needle_data.json')
    
    with open(data_path) as f:
        data_json = f.read()
    with open(index_path) as f:
        orig_html = f.read()

    m1 = orig_html.find('window.NEEDLE_DATA =')
    m2 = orig_html.find(';\n', m1)
    prefix = orig_html[:m1]
    
    # Check if app JS is after m2
    js_marker = orig_html.find('<!-- APPLICATION LOGIC SCRIPT -->')
    suffix = orig_html[js_marker:] if js_marker != -1 else orig_html[m2:]

    full_html = prefix + "window.NEEDLE_DATA = " + data_json + ";\n  </script>\n\n  " + suffix
    try:
        with open(index_path, 'w') as f:
            f.write(full_html)
        print(f"Successfully updated {index_path} ({os.path.getsize(index_path)/1024:.1f} KB).")
    except OSError as e:
        print(f"Notice: Could not write {index_path}: {e}")

    try:
        shutil.copyfile(index_path, needle_root)
        print(f"Successfully updated {needle_root} ({os.path.getsize(needle_root)/1024:.1f} KB).")
    except OSError as e:
        print(f"Notice: {needle_root} is read-only ({e}), updated {index_path}.")

if __name__ == '__main__':
    build_needle_dataset()
    update_needle_html_files()
