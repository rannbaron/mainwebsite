#!/usr/bin/env python3
"""
NC Early Voting Daily Change Summary & Rating Email Dispatcher
-------------------------------------------------------------
Generates a comprehensive daily summary comparing today's early voting
returns and 2026 forecast predictions against yesterday's, specifically highlighting:
  - Rating changes for each county (e.g. Safe R -> Lean R, Safe D -> Very Likely D)
  - Statewide early voting turnout & party split of new ballots
  - Statewide 2026 vote forecast changes
  - Projected flip counties and Toss Up battlegrounds
  - Top county margin shifts

Sends a beautifully styled HTML + plain-text email to the designated recipient.
"""

import os
import re
import sys
import glob
import json
import math
import argparse
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid, formataddr

import pandas as pd
import vote_forecast
import subscriptions

DEFAULT_RECIPIENT = "baronrann@gmail.com"
DISPATCH_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".email_dispatch_log.json")

def load_dispatch_log(log_path=DISPATCH_LOG_PATH):
    """Loads the email dispatch tracking log."""
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to read dispatch log {log_path}: {e}")
    return {"last_dispatched_day": 0, "last_dispatched_at": None, "dispatched_days": {}}

def is_day_dispatched(day, log_path=DISPATCH_LOG_PATH):
    """Checks whether early voting update email for a given EV day has already been dispatched."""
    log = load_dispatch_log(log_path)
    days_dict = log.get("dispatched_days", {})
    return str(day) in days_dict or day in days_dict

def record_day_dispatched(day, log_path=DISPATCH_LOG_PATH):
    """Records that an EV day update email was successfully dispatched."""
    log = load_dispatch_log(log_path)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "dispatched_days" not in log:
        log["dispatched_days"] = {}
    log["dispatched_days"][str(day)] = now_str
    log["last_dispatched_day"] = max(log.get("last_dispatched_day", 0), int(day))
    log["last_dispatched_at"] = now_str
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log, f, indent=2)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Recorded EV Day {day} dispatch at {now_str} in {os.path.basename(log_path)}")
        return True
    except Exception as e:
        print(f"Warning: Failed to update dispatch log: {e}")
        return False

def load_env_file():
    """Load credentials from .env if present."""
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_file):
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        k, v = line.split('=', 1)
                        os.environ[k.strip().replace('export ', '')] = v.strip().strip('"').strip("'")
        except Exception as e:
            print(f"Warning: Failed to load .env: {e}")

def get_base_dir():
    return os.path.dirname(os.path.abspath(__file__))

def find_available_days():
    """Finds all available daily party CSV files and returns sorted day numbers."""
    base_dir = get_base_dir()
    patterns = [
        os.path.join(base_dir, "nc_early_voting_party_ev_day_*.csv"),
        "nc_early_voting_party_ev_day_*.csv",
        "/home/rann/src/website/mainwebsite/nc_early_voting_party_ev_day_*.csv"
    ]
    files = set()
    for p in patterns:
        files.update(glob.glob(p))

    days = []
    for f in files:
        m = re.search(r'ev_day_(\d+)\.csv', f)
        if m:
            days.append(int(m.group(1)))
    days = sorted(list(set(days)))
    return days

def compute_daily_changes(prev_day=None, curr_day=None, is_election_day=False):
    """
    Computes all day-over-day changes between prev_day and curr_day.
    Returns a dict with all structured statistics, county change records, and legislative seat models.
    """
    base_dir = get_base_dir()
    days = find_available_days()
    if not days:
        raise FileNotFoundError("No daily party CSV files found (nc_early_voting_party_ev_day_*.csv).")

    if curr_day is None:
        curr_day = days[-1]
    if prev_day is None:
        idx = days.index(curr_day) if curr_day in days else len(days) - 1
        prev_day = days[max(0, idx - 1)]

    prev_candidates = [
        os.path.join(base_dir, f"nc_early_voting_party_ev_day_{prev_day}.csv"),
        f"nc_early_voting_party_ev_day_{prev_day}.csv",
        f"/home/rann/src/website/mainwebsite/nc_early_voting_party_ev_day_{prev_day}.csv"
    ]
    curr_candidates = [
        os.path.join(base_dir, f"nc_early_voting_party_ev_day_{curr_day}.csv"),
        f"nc_early_voting_party_ev_day_{curr_day}.csv",
        f"/home/rann/src/website/mainwebsite/nc_early_voting_party_ev_day_{curr_day}.csv"
    ]

    prev_file = next((f for f in prev_candidates if os.path.exists(f)), None)
    curr_file = next((f for f in curr_candidates if os.path.exists(f)), None)

    if not curr_file or not os.path.exists(curr_file):
        raise FileNotFoundError(f"Current day CSV not found for day {curr_day}")
    if not prev_file or not os.path.exists(prev_file):
        raise FileNotFoundError(f"Previous day CSV not found for day {prev_day}")

    df_prev = pd.read_csv(prev_file)
    df_curr = pd.read_csv(curr_file)

    fc_prev = vote_forecast.predict_all(df_prev, ev_day=prev_day)
    fc_curr = vote_forecast.predict_all(df_curr, ev_day=curr_day)

    st_prev = fc_prev['statewide']
    st_curr = fc_curr['statewide']

    # 1. Statewide Turnout & New Votes
    st_row_prev = df_prev[df_prev['County'] == 'STATEWIDE TOTAL'].iloc[0]
    st_row_curr = df_curr[df_curr['County'] == 'STATEWIDE TOTAL'].iloc[0]

    tot_prev = int(st_row_prev['Total 2026'])
    tot_curr = int(st_row_curr['Total 2026'])
    new_tot = tot_curr - tot_prev

    dem_prev = int(st_row_prev['Democrat (2026)'])
    dem_curr = int(st_row_curr['Democrat (2026)'])
    new_dem = dem_curr - dem_prev

    rep_prev = int(st_row_prev['Republican (2026)'])
    rep_curr = int(st_row_curr['Republican (2026)'])
    new_rep = rep_curr - rep_prev

    una_prev = int(st_row_prev['Unaffiliated (2026)'])
    una_curr = int(st_row_curr['Unaffiliated (2026)'])
    new_una = una_curr - una_prev

    # 2. County by County Analysis
    rating_changes = []
    all_county_shifts = []
    flips_prev = set(st_prev.get('flipped_to_dem', []))
    flips_curr = set(st_curr.get('flipped_to_dem', []))

    for cname in sorted(fc_curr['counties'].keys()):
        c_prev = fc_prev['counties'].get(cname)
        c_curr = fc_curr['counties'].get(cname)
        if not c_prev or not c_curr:
            continue

        r_prev = c_prev['rating']
        r_curr = c_curr['rating']
        d_prev = c_prev['pred_final_dem']
        d_curr = c_curr['pred_final_dem']
        p_dem_prev = c_prev['p_dem']
        p_dem_curr = c_curr['p_dem']
        shift = round(d_curr - d_prev, 2)
        p_shift = round(p_dem_curr - p_dem_prev, 1)

        margin_curr = c_curr.get('pred_margin', round(2 * d_curr - 100.0, 2))
        margin_prev = c_prev.get('pred_margin', round(2 * d_prev - 100.0, 2))

        call_conf_prev = c_prev.get('call_confidence', 'moderate confidence')
        call_conf_curr = c_curr.get('call_confidence', 'moderate confidence')
        call_conf_changed = (call_conf_prev != call_conf_curr)

        margin_conf_prev = c_prev.get('margin_confidence', 'moderate confidence')
        margin_conf_curr = c_curr.get('margin_confidence', 'moderate confidence')
        margin_conf_changed = (margin_conf_prev != margin_conf_curr)

        conf_changed = call_conf_changed or margin_conf_changed

        c_info = {
            'county': cname.title(),
            'rating_prev': r_prev,
            'rating_curr': r_curr,
            'rating_changed': (r_prev != r_curr),
            'dem_prev': d_prev,
            'dem_curr': d_curr,
            'margin_prev': margin_prev,
            'margin_curr': margin_curr,
            'shift': shift,
            'p_dem_prev': p_dem_prev,
            'p_dem_curr': p_dem_curr,
            'p_shift': p_shift,
            'range_low': c_curr['range_low'],
            'range_high': c_curr['range_high'],
            'ci_margin_low': c_curr.get('ci_margin_low', round(2.0 * c_curr['range_low'] - 100.0, 2)),
            'ci_margin_high': c_curr.get('ci_margin_high', round(2.0 * c_curr['range_high'] - 100.0, 2)),
            'margin_width_prev': c_prev.get('margin_width', round(2.0 * (c_prev['range_high'] - c_prev['range_low']), 2)),
            'margin_width_curr': c_curr.get('margin_width', round(2.0 * (c_curr['range_high'] - c_curr['range_low']), 2)),
            'margin_width': c_curr.get('margin_width', round(2.0 * (c_curr['range_high'] - c_curr['range_low']), 2)),
            'call_conf_prev': call_conf_prev,
            'call_conf_curr': call_conf_curr,
            'call_conf_changed': call_conf_changed,
            'margin_conf_prev': margin_conf_prev,
            'margin_conf_curr': margin_conf_curr,
            'margin_conf_changed': margin_conf_changed,
            'conf_changed': conf_changed,
            'margin_confidence': margin_conf_curr,
            'call_confidence': call_conf_curr,
            'actual_2022': c_curr['actual_2022'],
            'winner_2022': 'D' if c_curr['actual_2022'] > 50.0 else 'R'
        }
        all_county_shifts.append(c_info)

        if r_prev != r_curr:
            rating_changes.append(c_info)

    # Sort shifts
    top_dem_shifts = sorted([c for c in all_county_shifts if c['shift'] > 0], key=lambda x: x['shift'], reverse=True)[:5]
    top_rep_shifts = sorted([c for c in all_county_shifts if c['shift'] < 0], key=lambda x: x['shift'])[:5]

    # Confidence Changes
    confidence_changes = [c for c in all_county_shifts if c['conf_changed']]
    confidence_changes.sort(key=lambda x: (not x['call_conf_changed'], x['county']))
    call_conf_changes = [c for c in all_county_shifts if c['call_conf_changed']]
    margin_conf_changes = [c for c in all_county_shifts if c['margin_conf_changed']]

    # Current Projected Flips (2022 R -> 2026 D)
    current_flips = [c for c in all_county_shifts if c['winner_2022'] == 'R' and c['dem_curr'] > 50.0]
    current_flips.sort(key=lambda x: x['p_dem_curr'], reverse=True)

    # Toss Ups (40% - 60% flip probability)
    toss_ups = [c for c in all_county_shifts if c['rating_curr'] == 'Toss Up']

    # Multi-Race Statewide Summary
    races_summary = []
    races_curr = fc_curr.get('races') or fc_curr.get('statewide', {}).get('races', {})
    races_prev = fc_prev.get('races') or fc_prev.get('statewide', {}).get('races', {})
    for r_key, r_info in vote_forecast.RACES_CONFIG.items():
        curr_race = races_curr.get(r_key, {})
        prev_race = races_prev.get(r_key, {})
        if curr_race:
            d_curr = curr_race.get('pred_final_dem', 50.0)
            d_prev = prev_race.get('pred_final_dem', d_curr)
            shift = round(d_curr - d_prev, 2)
            margin = round(curr_race.get('pred_margin', d_curr * 2.0 - 100.0), 2)
            p_dem = curr_race.get('p_dem', curr_race.get('prob_dem', 50.0))
            p_rep = curr_race.get('p_rep', round(100.0 - p_dem, 1))
            ci_low = curr_race.get('ci_95_low', round(d_curr - 3.6, 2))
            ci_high = curr_race.get('ci_95_high', round(d_curr + 3.6, 2))
            ci_m_low = curr_race.get('ci_margin_low', round(margin - 7.2, 2))
            ci_m_high = curr_race.get('ci_margin_high', round(margin + 7.2, 2))
            races_summary.append({
                'key': r_key,
                'name': r_info['name'],
                'full_title': r_info.get('full_title', r_info['name']),
                'dem_candidate': r_info['dem_candidate'],
                'rep_candidate': r_info['rep_candidate'],
                'dem_curr': d_curr,
                'rep_curr': round(100.0 - d_curr, 2),
                'margin': margin,
                'shift': shift,
                'ci_95_low': ci_low,
                'ci_95_high': ci_high,
                'ci_margin_low': ci_m_low,
                'ci_margin_high': ci_m_high,
                'rating': curr_race.get('rating', 'Toss Up'),
                'prob_dem': p_dem,
                'prob_rep': p_rep,
                'call_confidence': curr_race.get('call_confidence', 'moderate confidence'),
                'margin_confidence': curr_race.get('margin_confidence', 'moderate confidence')
            })

    # Statewide Constitutional Amendments
    amendments_summary = []
    amend_dict = fc_curr.get('amendments', {})
    for a_key, a_info in vote_forecast.AMENDMENTS_CONFIG.items():
        curr_amend = amend_dict.get(a_key, a_info)
        d_curr = curr_amend.get('pred_final_dem', 50.0) # Against / No
        r_curr = curr_amend.get('pred_final_rep', 50.0) # For / Yes
        margin = round(curr_amend.get('pred_margin', d_curr - r_curr), 2)
        ci_low = curr_amend.get('ci_95_low', round(d_curr - 3.5, 2))
        ci_high = curr_amend.get('ci_95_high', round(d_curr + 3.5, 2))
        ci_m_low = curr_amend.get('ci_margin_low', round(margin - 7.0, 2))
        ci_m_high = curr_amend.get('ci_margin_high', round(margin + 7.0, 2))
        amendments_summary.append({
            'key': a_key,
            'name': curr_amend.get('name', a_info['name']),
            'short_name': curr_amend.get('short_name', a_info.get('short_name', a_info['name'])),
            'full_title': curr_amend.get('full_title', a_info.get('full_title', '')),
            'ballot_question': curr_amend.get('ballot_question', a_info.get('ballot_question', '')),
            'dem_stance': curr_amend.get('dem_stance', 'Against (No)'),
            'rep_stance': curr_amend.get('rep_stance', 'For (Yes)'),
            'dem_curr': d_curr,
            'rep_curr': r_curr,
            'ci_95_low': ci_low,
            'ci_95_high': ci_high,
            'margin': margin,
            'ci_margin_low': ci_m_low,
            'ci_margin_high': ci_m_high,
            'rating': curr_amend.get('rating', 'Toss Up'),
            'prob_dem': curr_amend.get('p_dem', 50.0),
            'prob_rep': curr_amend.get('p_rep', 50.0),
            'call_confidence': curr_amend.get('call_confidence', 'high confidence'),
            'margin_confidence': curr_amend.get('margin_confidence', 'high confidence')
        })

    return {
        'prev_day': prev_day,
        'curr_day': curr_day,
        'date_str': datetime.now().strftime('%A, %B %d, %Y'),
        'turnout': {
            'prev_tot': tot_prev,
            'curr_tot': tot_curr,
            'new_tot': new_tot,
            'pct_increase': round((new_tot / tot_prev * 100.0) if tot_prev > 0 else 0, 2),
            'new_dem': new_dem,
            'new_rep': new_rep,
            'new_una': new_una,
            'pct_dem': round((new_dem / new_tot * 100.0) if new_tot > 0 else 0, 1),
            'pct_rep': round((new_rep / new_tot * 100.0) if new_tot > 0 else 0, 1),
            'pct_una': round((new_una / new_tot * 100.0) if new_tot > 0 else 0, 1),
        },
        'statewide_forecast': {
            'prev_dem': st_prev['pred_final_dem'],
            'curr_dem': st_curr['pred_final_dem'],
            'dem_shift': round(st_curr['pred_final_dem'] - st_prev['pred_final_dem'], 2),
            'prev_low': st_prev['range_low'],
            'prev_high': st_prev['range_high'],
            'curr_low': st_curr['range_low'],
            'curr_high': st_curr['range_high'],
            'rating': st_curr['rating'],
            'margin_confidence': st_curr.get('margin_confidence', 'moderate confidence'),
            'call_confidence': st_curr.get('call_confidence', 'high confidence'),
            'ratings_summary_prev': st_prev.get('ratings_summary', {}),
            'ratings_summary_curr': st_curr.get('ratings_summary', {})
        },
        'races_summary': races_summary,
        'amendments_summary': amendments_summary,
        'legislative': vote_forecast.predict_legislative_seats(),
        'is_election_day': is_election_day,
        'rating_changes': rating_changes,
        'confidence_changes': confidence_changes,
        'call_conf_changes': call_conf_changes,
        'margin_conf_changes': margin_conf_changes,
        'current_flips': current_flips,
        'toss_ups': toss_ups,
        'top_dem_shifts': top_dem_shifts,
        'top_rep_shifts': top_rep_shifts,
        'all_county_shifts': all_county_shifts
    }

def format_plain_text(data):
    """Generates a clean plain text version focusing exclusively on statewide races, amendments, and legislative chambers."""
    t = data['turnout']
    sf = data['statewide_forecast']
    is_el_day = data.get('is_election_day', False)

    header_title = "NC ELECTION DAY 2026 SPECIAL UPDATE: FINAL BENCHMARKS & MARGINS" if is_el_day else f"NC EARLY VOTING FINAL UPDATE: CUMULATIVE DAY {data['curr_day']} STATEWIDE BENCHMARKS"

    lines = [
        header_title,
        f"Date: {data['date_str']}",
        "=" * 72,
        "",
        "*" * 72,
        "MAJOR MODEL OVERHAUL & PREDICTION PLATFORM ACCESS:",
        "  * Dedicated 2026 Prediction Site: https://rannbar-on.com/prediction/",
        "  * Access Password: nc2026beta",
        "  * Architectural Upgrade: Two-Mode Historical EV vs. Election Day Decomposition",
        "    - Heavy midterm weighting (85%) calibrating the Election Day Republican surge.",
        "    - County-specific partisan calibration + GOP reservoir & cannibalization models.",
        "    - Full polling synthesis weighted by pollster quality rating and recency.",
        "*" * 72,
        "",
        "=" * 72,
        "1. EXECUTIVE TURNOUT SUMMARY (DAY 17 FINAL EARLY VOTING)",
        "=" * 72,
        f"  - Total Early Ballots Cast: {t['curr_tot']:,} (vs {t['prev_tot']:,} prior day, +{t['new_tot']:,} added)",
        f"  - Registered Party Breakdown (Cumulative):",
        f"    * Democrat:     1,080,380 (38.36%)",
        f"    * Republican:     736,859 (26.16%)",
        f"    * Unaffiliated:   990,731 (35.17%)",
        f"    * Others:           8,707 (0.31%)",
        f"  - Statewide US Senate Baseline: Dem {sf['curr_dem']:.2f}% (95% CI: [{sf.get('ci_95_low', sf['curr_low']):.2f}%, {sf.get('ci_95_high', sf['curr_high']):.2f}%])",
        f"  - Statewide Rating: {sf['rating']} [Call: {sf['call_confidence']} | Margin: {sf['margin_confidence']}]",
        "",
        "=" * 72,
        "2. STATEWIDE CANDIDATE RACES (POINT ESTIMATES, MARGINS & 95% CIs)",
        "=" * 72,
    ]

    for r in data.get('races_summary', []):
        m_sign = '+' if r['margin'] > 0 else ''
        lines.extend([
            f"  * {r['name'].upper()}:",
            f"    - Matchup: {r['dem_candidate']} (Dem) vs {r['rep_candidate']} (Rep)",
            f"    - Democratic Vote Share: {r['dem_curr']:.2f}%  -->  95% CI: [{r['ci_95_low']:.2f}%, {r['ci_95_high']:.2f}%]",
            f"    - Republican Vote Share: {r['rep_curr']:.2f}%",
            f"    - Projected Margin:      {m_sign}{r['margin']:.2f}%  -->  95% CI: [{r['ci_margin_low']:+.2f}%, {r['ci_margin_high']:+.2f}%]",
            f"    - Win Probability:       Dem {r['prob_dem']:.1f}% | Rep {r['prob_rep']:.1f}%",
            f"    - Model Rating:          {r['rating']} [{r['call_confidence']}]",
            ""
        ])

    lines.extend([
        "=" * 72,
        "3. STATEWIDE CONSTITUTIONAL AMENDMENTS (PREDICTIONS & 95% CIs)",
        "=" * 72,
    ])

    for a in data.get('amendments_summary', []):
        m_sign = '+' if a['margin'] > 0 else ''
        lines.extend([
            f"  * {a['name'].upper()}:",
            f"    - Ballot Question: {a.get('ballot_question', '')}",
            f"    - For / Yes (GOP-aligned):     {a['rep_curr']:.2f}%",
            f"    - Against / No (Dem-aligned):  {a['dem_curr']:.2f}%  -->  95% CI: [{a['ci_95_low']:.2f}%, {a['ci_95_high']:.2f}%]",
            f"    - Projected Net Margin:        {m_sign}{a['margin']:.2f}%  -->  95% CI: [{a['ci_margin_low']:+.2f}%, {a['ci_margin_high']:+.2f}%]",
            f"    - Outlook / Pass Probability:  {a['rating']} (Yes Prob: {a['prob_rep']:.1f}%)",
            ""
        ])

    leg = data.get('legislative', {})
    if leg:
        sen = leg.get('senate', {})
        hou = leg.get('house', {})
        lines.extend([
            "=" * 72,
            "4. NC GENERAL ASSEMBLY LEGISLATIVE BENCHMARKS & 95% SEAT CIs",
            "=" * 72,
            "  * NC SENATE (50 SEATS TOTAL):",
            f"    - Projected Democratic Seats: {sen.get('point_estimate_dem')} Dem (Point Est.) | {sen.get('expected_seats_dem')} Dem (Expected EV)",
            f"    - 95% Confidence Interval:    {sen.get('ci_str')} Dem",
            f"    - Projected Republican Seats: {sen.get('point_estimate_rep')} Rep (Point Est.) | {sen.get('expected_seats_rep')} Rep (Expected EV)",
            f"    - GOP Supermajority Threshold: 30 seats (60%) -> Democrats Need 21+ to Break",
            f"    - Supermajority Status:       {'SUPERMAJORITY BROKEN' if sen.get('prob_break_supermajority', 0) > 50 else 'GOP Supermajority Holds'} ({sen.get('prob_break_supermajority')}% probability)",
            f"    - Chamber Majority Win Prob:  {sen.get('prob_win_majority')}%\n",
            "  * NC HOUSE (120 SEATS TOTAL):",
            f"    - Projected Democratic Seats: {hou.get('point_estimate_dem')} Dem (Point Est.) | {hou.get('expected_seats_dem')} Dem (Expected EV)",
            f"    - 95% Confidence Interval:    {hou.get('ci_str')} Dem",
            f"    - Projected Republican Seats: {hou.get('point_estimate_rep')} Rep (Point Est.) | {hou.get('expected_seats_rep')} Rep (Expected EV)",
            f"    - GOP Supermajority Threshold: 72 seats (60%) -> Democrats Need 49+ to Break",
            f"    - Supermajority Status:       {'SUPERMAJORITY BROKEN' if hou.get('prob_break_supermajority', 0) > 50 else 'GOP Supermajority Holds'} ({hou.get('prob_break_supermajority')}% probability)",
            f"    - Chamber Majority Win Prob:  {hou.get('prob_win_majority')}%\n",
        ])

    lines.extend([
        "=" * 72,
        "Interactive 2026 Prediction Model: https://rannbar-on.com/prediction/ (Password: nc2026beta)",
        "Early Vote Explorer: https://rannbar-on.com/earlyvote/",
        "To unsubscribe from updates: {{UNSUBSCRIBE_URL}}",
        "=" * 72,
    ])
    return "\n".join(lines)

def format_html(data):
    """Generates an HTML version focusing exclusively on statewide races, amendments, and legislative chambers."""
    t = data['turnout']
    sf = data['statewide_forecast']

    def badge(rating):
        color = "#6c757d"
        bg = "#f8f9fa"
        if "Safe D" in rating:
            bg, color = "#d0e2ff", "#0043ce"
        elif "Very Likely D" in rating:
            bg, color = "#e0e7ff", "#3730a3"
        elif "Likely D" in rating:
            bg, color = "#ede9fe", "#5b21b6"
        elif "Lean D" in rating:
            bg, color = "#e0f2fe", "#0369a1"
        elif "Toss Up" in rating:
            bg, color = "#fef3c7", "#92400e"
        elif "Lean R" in rating or "Lean For" in rating:
            bg, color = "#ffe4e6", "#be123c"
        elif "Likely R" in rating or "Likely For" in rating:
            bg, color = "#fee2e2", "#b91c1c"
        elif "Very Likely R" in rating:
            bg, color = "#fecdd3", "#9f1239"
        elif "Safe R" in rating:
            bg, color = "#ffd7d9", "#da1e28"
        return f'<span style="display:inline-block;padding:3px 8px;font-size:12px;font-weight:700;border-radius:4px;background:{bg};color:{color};">{rating}</span>'

    def conf_badge(conf):
        c_low = conf.lower()
        if "very high" in c_low:
            bg, color = "#dcfce7", "#15803d" # green
        elif "high" in c_low:
            bg, color = "#ecfdf5", "#047857" # emerald
        elif "moderate" in c_low:
            bg, color = "#fef3c7", "#b45309" # amber
        elif "very low" in c_low:
            bg, color = "#fee2e2", "#b91c1c" # red
        else:
            bg, color = "#ffedd5", "#c2410c" # orange (low)
        short_label = conf.title().replace(" Confidence", "")
        return f'<span style="display:inline-block;padding:2px 6px;font-size:11px;font-weight:700;border-radius:4px;background:{bg};color:{color};">{short_label}</span>'

    # Build multi-race table HTML
    races_rows = "".join([
        f"""<tr>
            <td style="padding:10px 12px;font-weight:700;border-bottom:1px solid #e5e7eb;color:#0f172a;">{r['name']}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:12px;">
                <span style="color:#1d4ed8;font-weight:700;">{r['dem_candidate']} (D)</span><br>
                <span style="color:#b91c1c;font-weight:700;">{r['rep_candidate']} (R)</span>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:12px;">
                <strong style="font-size:13px;color:#1e293b;">{r['dem_curr']:.2f}% D</strong> &bull; {r['rep_curr']:.2f}% R<br>
                <span style="display:inline-block;padding:2px 6px;margin-top:3px;font-size:11px;font-weight:700;background:#eff6ff;color:#1d4ed8;border-radius:4px;border:1px solid #bfdbfe;">
                    95% CI: [{r['ci_95_low']:.2f}%, {r['ci_95_high']:.2f}%]
                </span>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:12px;">
                <strong style="font-size:13px;color:{'#1d4ed8' if r['margin']>0 else '#b91c1c'};">{'+' if r['margin']>0 else ''}{r['margin']:.2f}%</strong>
                <span style="color:{'#16a34a' if r['shift'] > 0 else ('#dc2626' if r['shift'] < 0 else '#6b7280')};font-size:11px;font-weight:600;margin-left:4px;">({r['shift']:+.2f}%)</span><br>
                <span style="color:#64748b;font-size:11px;">CI: [{'+' if r['ci_margin_low']>0 else ''}{r['ci_margin_low']:.2f}%, {'+' if r['ci_margin_high']>0 else ''}{r['ci_margin_high']:.2f}%]</span>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:12px;">
                <span style="color:#1d4ed8;font-weight:700;">{r['prob_dem']:.1f}% D</span> / <span style="color:#b91c1c;font-weight:700;">{r['prob_rep']:.1f}% R</span>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">
                {badge(r['rating'])}<br>
                <span style="font-size:10px;color:#64748b;font-weight:600;">{conf_badge(r['call_confidence'])}</span>
            </td>
        </tr>"""
        for r in data.get('races_summary', [])
    ])
    races_html = f"""
    <h2 style="font-size:16px;font-weight:800;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:6px;margin:24px 0 12px 0;">
        ⚖️ Statewide Candidate Contests & 95% Confidence Intervals
    </h2>
    <table style="width:100%;border-collapse:collapse;margin:12px 0 24px 0;background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;font-size:13px;">
        <thead>
            <tr style="background:#f3f4f6;text-align:left;font-size:11px;color:#4b5563;text-transform:uppercase;">
                <th style="padding:10px 12px;">Contest</th>
                <th style="padding:10px 12px;">Candidates</th>
                <th style="padding:10px 12px;">Projected Share (95% CI)</th>
                <th style="padding:10px 12px;">Margin (95% CI)</th>
                <th style="padding:10px 12px;">Win Probability</th>
                <th style="padding:10px 12px;">Model Rating</th>
            </tr>
        </thead>
        <tbody>{races_rows}</tbody>
    </table>
    """

    # Build constitutional amendments HTML
    amend_rows = "".join([
        f"""<tr>
            <td style="padding:10px 12px;font-weight:700;border-bottom:1px solid #e5e7eb;color:#0f172a;">
                {a['name']}<br>
                <span style="font-size:11px;color:#64748b;font-weight:400;">{a.get('ballot_question', '')}</span>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:12px;">
                <strong style="color:#b91c1c;">{a['rep_curr']:.2f}%</strong> (For / Yes)
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:12px;">
                <strong style="color:#1d4ed8;">{a['dem_curr']:.2f}%</strong> (Against / No)<br>
                <span style="display:inline-block;padding:2px 6px;margin-top:3px;font-size:11px;font-weight:700;background:#eff6ff;color:#1d4ed8;border-radius:4px;border:1px solid #bfdbfe;">
                    95% CI: [{a['ci_95_low']:.2f}%, {a['ci_95_high']:.2f}%]
                </span>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:12px;">
                <strong>{'+' if a['margin']>0 else ''}{a['margin']:.2f}%</strong><br>
                <span style="color:#64748b;font-size:11px;">CI: [{'+' if a['ci_margin_low']>0 else ''}{a['ci_margin_low']:.2f}%, {'+' if a['ci_margin_high']>0 else ''}{a['ci_margin_high']:.2f}%]</span>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">
                {badge(a['rating'])}<br>
                <span style="font-size:11px;color:{'#15803d' if a['prob_rep']>50 else '#b91c1c'};font-weight:700;">{a['prob_rep']:.1f}% Yes Prob</span>
            </td>
        </tr>"""
        for a in data.get('amendments_summary', [])
    ])
    amend_html = f"""
    <h2 style="font-size:16px;font-weight:800;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:6px;margin:28px 0 12px 0;">
        📜 Statewide Constitutional Amendments (Pass/Fail Predictions & 95% CIs)
    </h2>
    <table style="width:100%;border-collapse:collapse;margin:12px 0 24px 0;background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;font-size:13px;">
        <thead>
            <tr style="background:#f3f4f6;text-align:left;font-size:11px;color:#4b5563;text-transform:uppercase;">
                <th style="padding:10px 12px;width:38%;">Amendment & Ballot Question</th>
                <th style="padding:10px 12px;">For (Yes)</th>
                <th style="padding:10px 12px;">Against (No & 95% CI)</th>
                <th style="padding:10px 12px;">Net Margin & 95% CI</th>
                <th style="padding:10px 12px;">Outlook & Probability</th>
            </tr>
        </thead>
        <tbody>{amend_rows}</tbody>
    </table>
    """

    # Build NC General Assembly legislative cards HTML
    leg = data.get('legislative', {})
    sen = leg.get('senate', {})
    hou = leg.get('house', {})
    leg_html = f"""
    <h2 style="font-size:16px;font-weight:800;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:6px;margin:28px 0 12px 0;">
        🏛️ NC General Assembly Legislative Benchmarks & 95% Seat CIs
    </h2>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0 24px 0;">
        <!-- NC Senate Card -->
        <div style="background:#ffffff;border:1px solid #cbd5e1;border-radius:8px;padding:16px;box-shadow:0 1px 2px rgba(0,0,0,0.05);">
            <div style="font-size:14px;font-weight:800;color:#0f172a;border-bottom:1px solid #e2e8f0;padding-bottom:8px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;">
                <span>NC SENATE</span>
                <span style="font-size:11px;color:#64748b;font-weight:600;">50 SEATS TOTAL</span>
            </div>
            <div style="margin-bottom:8px;">
                <div style="font-size:12px;color:#475569;">Projected Democratic Seats:</div>
                <div style="font-size:22px;font-weight:800;color:#1d4ed8;margin-top:2px;">
                    {sen.get('point_estimate_dem')} Dem <span style="font-size:12px;color:#64748b;font-weight:600;">(Exp: {sen.get('expected_seats_dem')})</span>
                </div>
                <div style="margin-top:6px;">
                    <span style="display:inline-block;padding:3px 8px;font-size:12px;font-weight:800;background:#dbeafe;color:#1e40af;border-radius:4px;border:1px solid #bfdbfe;">
                        95% CI: {sen.get('ci_str')} Dem
                    </span>
                </div>
            </div>
            <div style="font-size:12px;color:#475569;margin-top:8px;">
                Projected Republican Seats: <strong style="color:#b91c1c;">{sen.get('point_estimate_rep')} Rep</strong> (Exp: {sen.get('expected_seats_rep')})
            </div>
            <div style="font-size:11px;color:#64748b;margin-top:6px;">
                Supermajority threshold: 30 GOP seats (60%) &bull; Dems need 21+ to break.
            </div>
            <div style="margin-top:12px;padding:10px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;text-align:center;">
                <div style="font-size:11px;font-weight:700;color:#166534;text-transform:uppercase;">Supermajority Probability</div>
                <div style="font-size:16px;font-weight:800;color:#15803d;margin-top:2px;">
                    {sen.get('prob_break_supermajority')}% Probability Broken
                </div>
            </div>
        </div>

        <!-- NC House Card -->
        <div style="background:#ffffff;border:1px solid #cbd5e1;border-radius:8px;padding:16px;box-shadow:0 1px 2px rgba(0,0,0,0.05);">
            <div style="font-size:14px;font-weight:800;color:#0f172a;border-bottom:1px solid #e2e8f0;padding-bottom:8px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;">
                <span>NC HOUSE</span>
                <span style="font-size:11px;color:#64748b;font-weight:600;">120 SEATS TOTAL</span>
            </div>
            <div style="margin-bottom:8px;">
                <div style="font-size:12px;color:#475569;">Projected Democratic Seats:</div>
                <div style="font-size:22px;font-weight:800;color:#1d4ed8;margin-top:2px;">
                    {hou.get('point_estimate_dem')} Dem <span style="font-size:12px;color:#64748b;font-weight:600;">(Exp: {hou.get('expected_seats_dem')})</span>
                </div>
                <div style="margin-top:6px;">
                    <span style="display:inline-block;padding:3px 8px;font-size:12px;font-weight:800;background:#dbeafe;color:#1e40af;border-radius:4px;border:1px solid #bfdbfe;">
                        95% CI: {hou.get('ci_str')} Dem
                    </span>
                </div>
            </div>
            <div style="font-size:12px;color:#475569;margin-top:8px;">
                Projected Republican Seats: <strong style="color:#b91c1c;">{hou.get('point_estimate_rep')} Rep</strong> (Exp: {hou.get('expected_seats_rep')})
            </div>
            <div style="font-size:11px;color:#64748b;margin-top:6px;">
                Supermajority threshold: 72 GOP seats (60%) &bull; Dems need 49+ to break.
            </div>
            <div style="margin-top:12px;padding:10px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;text-align:center;">
                <div style="font-size:11px;font-weight:700;color:#166534;text-transform:uppercase;">Supermajority Probability</div>
                <div style="font-size:16px;font-weight:800;color:#15803d;margin-top:2px;">
                    {hou.get('prob_break_supermajority')}% Probability Broken
                </div>
            </div>
        </div>
    </div>
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NC Early Voting Daily Update</title>
    </head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.5;color:#1f2937;background-color:#f9fafb;margin:0;padding:24px;">
        <div style="max-width:700px;margin:0 auto;background:#ffffff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);border:1px solid #e5e7eb;overflow:hidden;">
            <!-- Header -->
            <div style="background:linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);color:#ffffff;padding:24px 28px;">
                <div style="font-size:12px;text-transform:uppercase;letter-spacing:1px;font-weight:700;color:#93c5fd;">Election Intelligence Report</div>
                <h1 style="margin:6px 0 4px 0;font-size:22px;font-weight:800;color:#ffffff;">NC Early Voting: Final Cumulative Day {data['curr_day']} Benchmarks</h1>
                <div style="font-size:13px;color:#bfdbfe;">{data['date_str']} &bull; 2-Mode Historical Decomposition Engine</div>
            </div>

            <div style="padding:24px 28px;">
                <!-- Major Model Update Banner & Prediction Site Password Access -->
                <div style="background:#eff6ff;border:2px solid #3b82f6;border-radius:8px;padding:16px 20px;margin-bottom:22px;line-height:1.5;">
                    <div style="font-size:16px;font-weight:800;color:#1e40af;margin-bottom:8px;">
                        🚀 MAJOR MODEL UPDATE: 2-Mode Historical EV vs. Election Day Decomposition
                    </div>
                    <div style="font-size:13px;color:#1e293b;margin-bottom:12px;">
                        The election prediction engine has been upgraded to an empirical two-mode turnout decomposition architecture, explicitly accounting for historical Election Day Republican turnout surges (with midterms weighted at 85%), county-level GOP cannibalization/reservoir dynamics, and quality-weighted polling synthesis across all contests.
                    </div>
                    <div style="background:#ffffff;border:1px solid #bfdbfe;border-radius:6px;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
                        <div>
                            <div style="font-size:11px;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Dedicated Prediction Site</div>
                            <a href="https://rannbar-on.com/prediction/" style="font-size:15px;font-weight:700;color:#2563eb;text-decoration:underline;">https://rannbar-on.com/prediction/</a>
                        </div>
                        <div style="background:#f1f5f9;padding:6px 14px;border-radius:6px;border:1px dashed #94a3b8;">
                            <span style="font-size:12px;color:#475569;font-weight:600;">Site Password:</span>
                            <code style="font-size:15px;font-weight:800;color:#0f172a;background:#e2e8f0;padding:2px 8px;border-radius:4px;margin-left:6px;font-family:monospace;">nc2026beta</code>
                        </div>
                    </div>
                </div>

                <!-- Key Stat Callout Cards -->
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">
                    <div style="background:#f0fdf4;border:1px solid #bbf7d0;padding:14px;border-radius:6px;">
                        <div style="font-size:11px;font-weight:700;color:#166534;text-transform:uppercase;">Total Early Ballots Cast</div>
                        <div style="font-size:20px;font-weight:800;color:#15803d;margin-top:2px;">{t['curr_tot']:,}</div>
                        <div style="font-size:12px;color:#166534;margin-top:4px;">Dem {t['pct_dem']}% | Rep {t['pct_rep']}% | Una {t['pct_una']}%</div>
                    </div>
                    <div style="background:#eff6ff;border:1px solid #bfdbfe;padding:14px;border-radius:6px;">
                        <div style="font-size:11px;font-weight:700;color:#1e40af;text-transform:uppercase;">2026 Forecast Dem Share</div>
                        <div style="font-size:20px;font-weight:800;color:#1d4ed8;margin-top:2px;">{sf['curr_dem']:.2f}% <span style="font-size:13px;color:{'#16a34a' if sf['dem_shift'] > 0 else ('#dc2626' if sf['dem_shift'] < 0 else '#6b7280')};">({sf['dem_shift']:+.2f}%)</span></div>
                        <div style="font-size:12px;color:#1e40af;margin-top:4px;">CI: {sf['curr_low']:.1f}% - {sf['curr_high']:.1f}% ({badge(sf['rating'])})</div>
                        <div style="font-size:11px;color:#475569;margin-top:4px;">Call: {conf_badge(sf['call_confidence'])} &bull; Margin: {conf_badge(sf['margin_confidence'])}</div>
                    </div>
                </div>

                <!-- Multi-Race Section -->
                {races_html}

                <!-- Amendments Section -->
                {amend_html}

                <!-- Legislative Benchmarks Section -->
                {leg_html}

                <!-- Footer Call to Action -->
                <div style="margin-top:32px;padding:16px;background:#f3f4f6;border-radius:6px;text-align:center;">
                    <div style="font-size:13px;color:#4b5563;margin-bottom:8px;">View live 2026 election prediction models, polling synthesis, and legislative watch:</div>
                    <a href="https://rannbar-on.com/prediction/" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;font-weight:700;padding:8px 18px;border-radius:4px;font-size:13px;">Open 2026 Prediction Model &rarr;</a>
                </div>
            </div>

            <!-- Email footer -->
            <div style="border-top:1px solid #e5e7eb;padding:20px 28px;background:#f9fafb;font-size:11px;color:#9ca3af;text-align:center;line-height:1.6;">
                <div style="font-weight:600;color:#64748b;">Autonomous Early Voting Update System &bull; North Carolina 2026 Analysis</div>
                <div style="margin-top:6px;color:#6b7280;">You received this dispatch because you subscribed to early voting updates.</div>
                <div style="margin-top:8px;">
                    <a href="{{{{UNSUBSCRIBE_URL}}}}" style="color:#2563eb;text-decoration:underline;font-weight:600;">Unsubscribe from updates</a>
                    <span style="color:#cbd5e1;margin:0 8px;">&bull;</span>
                    <a href="https://rannbar-on.com/prediction/" style="color:#64748b;text-decoration:underline;">View Prediction Model</a>
                    <span style="color:#cbd5e1;margin:0 8px;">&bull;</span>
                    <a href="https://rannbar-on.com/earlyvote/" style="color:#64748b;text-decoration:underline;">Early Vote Explorer</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def send_via_ms_graph(recipients, subject, html_body, plain_body=None, sender="rb6@duke.edu"):
    """Dispatches HTML emails via Microsoft Graph API using cached OAuth2 tokens."""
    import msal
    import requests

    cache_path = os.path.expanduser("~/.duke_token_cache.bin")
    if not os.path.exists(cache_path):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] MS Graph Warning: Token cache {cache_path} not found.")
        return False, []

    cache = msal.SerializableTokenCache()
    with open(cache_path, "r") as f:
        cache.deserialize(f.read())

    app = msal.PublicClientApplication(
        "14d82eec-204b-4c2f-b7e8-296a70dab67e",
        authority="https://login.microsoftonline.com/cb72c54e-4a31-4d9e-b14a-1ea36dfac94c",
        token_cache=cache
    )
    accounts = app.get_accounts(username=sender)
    if not accounts:
        accounts = app.get_accounts()
    if not accounts:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] MS Graph Warning: No account found for {sender}.")
        return False, []

    token_result = app.acquire_token_silent(["https://graph.microsoft.com/Mail.Send"], account=accounts[0])
    if not token_result or "access_token" not in token_result:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] MS Graph Warning: Failed to acquire silent access token.")
        return False, []

    access_token = token_result["access_token"]
    url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    DEFAULT_UNSUB_BASE = "https://script.google.com/macros/s/AKfycby4nUxaJpTz50X43tc79R3vEUSDOEj-TQskmZce3hw6Pm2yw6d-pdEq10dek-WWrsWRcw/exec?action=unsubscribe"
    unsub_base_url = os.getenv("UNSUBSCRIBE_ENDPOINT_URL") or DEFAULT_UNSUB_BASE
    import urllib.parse

    delivered = 0
    failed = []
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Dispatching via MS Graph ({sender}) to {len(recipients)} recipient(s)...")

    for rec in recipients:
        rec_unsub_url = f"{unsub_base_url}&email={urllib.parse.quote(rec)}"
        rec_html = html_body.replace("{{UNSUBSCRIBE_URL}}", rec_unsub_url)

        payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": rec_html
                },
                "toRecipients": [{"emailAddress": {"address": rec}}]
            },
            "saveToSentItems": "true"
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code == 202:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ MS Graph delivered to {rec}")
                delivered += 1
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ MS Graph failed for {rec}: HTTP {resp.status_code} {resp.text}")
                failed.append(rec)
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ MS Graph error for {rec}: {e}")
            failed.append(rec)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] MS Graph Batch complete: {delivered}/{len(recipients)} delivered successfully.")
    return delivered > 0, failed


def send_summary_email(data, recipient=None, send_to_subscribers=False, extra_recipients=None, custom_subject=None):
    """Dispatches the multi-part email to subscribers or designated recipient."""
    load_env_file()

    recipients_list = []
    if send_to_subscribers:
        recipients_list = subscriptions.get_active_subscribers()
        if not recipients_list:
            recipients_list = [DEFAULT_RECIPIENT]
    elif recipient:
        recipients_list = [recipient]
    else:
        recipients_list = [DEFAULT_RECIPIENT]

    if extra_recipients:
        if isinstance(extra_recipients, str):
            extra_recipients = [e.strip() for e in extra_recipients.split(',') if e.strip()]
        recipients_list.extend(extra_recipients)

    # Deduplicate and normalize
    seen = set()
    unique_recipients = []
    for r in recipients_list:
        r_clean = r.strip().lower()
        if r_clean and r_clean not in seen:
            seen.add(r_clean)
            unique_recipients.append(r_clean)
    recipients = unique_recipients

    rating_change_count = len(data['rating_changes'])
    conf_change_count = len(data['confidence_changes'])

    parts = []
    if rating_change_count > 0:
        parts.append(f"{rating_change_count} Rating Change{'s' if rating_change_count > 1 else ''}")
    if conf_change_count > 0:
        parts.append(f"{conf_change_count} Confidence Shift{'s' if conf_change_count > 1 else ''}")

    if parts:
        headline = f"({', '.join(parts)})"
    else:
        headline = "(Ratings Steady)"

    subject = custom_subject or f"NC Early Vote Day {data['curr_day']} Update {headline}"

    plain_body = format_plain_text(data)
    html_body = format_html(data)

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    if smtp_pass:
        smtp_pass = smtp_pass.replace(" ", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Preparing email notification for {len(recipients)} recipient(s)...")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Subject: {subject}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Recipients: {', '.join(recipients)}")

    # Check if SMTP is configured. If not, try MS Graph fallback directly!
    if not smtp_pass or not smtp_user:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Notice: SMTP credentials not present. Attempting MS Graph API dispatch...")
        success, failed = send_via_ms_graph(recipients, subject, html_body, plain_body)
        if success and send_to_subscribers:
            successful = [r for r in recipients if r not in failed]
            subscriptions.mark_sent(successful)
        return success

    # Policy Guard: Stop sending election prediction emails after Sunday morning (Nov 1, 2026 12:00 PM EDT)
    from zoneinfo import ZoneInfo
    ny_now = datetime.now(ZoneInfo("America/New_York"))
    cutoff = datetime(2026, 11, 1, 12, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    if ny_now > cutoff:
        print(f"[{ny_now.strftime('%H:%M:%S')}] Notice: Early voting prediction email dispatch concluded after Sunday morning (Nov 1, 2026). No emails will be sent.")
        return True

    delivered_count = 0
    failed_recipients = []

    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Connecting to SMTP server {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=20)
        server.ehlo()
        if smtp_port == 587 or "gmail" in smtp_server:
            server.starttls()
            server.ehlo()
        server.login(smtp_user, smtp_pass)

        DEFAULT_UNSUB_BASE = "https://script.google.com/macros/s/AKfycby4nUxaJpTz50X43tc79R3vEUSDOEj-TQskmZce3hw6Pm2yw6d-pdEq10dek-WWrsWRcw/exec?action=unsubscribe"
        unsub_base_url = os.getenv("UNSUBSCRIBE_ENDPOINT_URL") or DEFAULT_UNSUB_BASE
        import urllib.parse

        for rec in recipients:
            msg = MIMEMultipart("alternative")
            msg['From'] = formataddr(("NC Early Voting Updates", smtp_user))
            msg['Reply-To'] = smtp_user
            msg['To'] = rec
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid(domain="elections.map")

            rec_unsub_url = f"{unsub_base_url}&email={urllib.parse.quote(rec)}"
            rec_plain = plain_body.replace("{{UNSUBSCRIBE_URL}}", rec_unsub_url)
            rec_html = html_body.replace("{{UNSUBSCRIBE_URL}}", rec_unsub_url)

            part1 = MIMEText(rec_plain, 'plain', 'utf-8')
            part2 = MIMEText(rec_html, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)

            # Modern RFC 8058 One-Click List-Unsubscribe header for Gmail, Apple Mail, Outlook
            msg['List-Unsubscribe'] = f"<{rec_unsub_url}>"
            msg['List-Unsubscribe-Post'] = "List-Unsubscribe=One-Click"

            try:
                server.sendmail(smtp_user, [rec], msg.as_string())
                delivered_count += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully delivered to {rec}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed delivery to {rec}: {e}")
                failed_recipients.append(rec)

        server.quit()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Batch complete: {delivered_count}/{len(recipients)} emails delivered via {smtp_server}:{smtp_port}!")
        if send_to_subscribers and delivered_count > 0:
            successful = [r for r in recipients if r not in failed_recipients]
            subscriptions.mark_sent(successful)
        return delivered_count > 0
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] SMTP delivery error: {e}")
        return False

def save_latest_email_artifacts(data, json_path="latest_daily_email.json", html_path="latest_daily_email.html"):
    """
    Saves the latest daily summary email payload as JSON and HTML for web hosting.
    This enables immediate delivery to first-time subscribers via the Google Apps Script Web App.
    """
    import json
    from datetime import timezone

    subject = f"NC Early Vote Day {data['curr_day']} Update ({len(data['rating_changes'])} Rating Changes, {len(data['confidence_changes'])} Confidence Shifts)"
    html = format_html(data)
    text = format_plain_text(data)

    payload = {
        "day": data["curr_day"],
        "date": data["date_str"],
        "subject": subject,
        "html": html,
        "text": text,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    DEFAULT_UNSUB_BASE = "https://script.google.com/macros/s/AKfycby4nUxaJpTz50X43tc79R3vEUSDOEj-TQskmZce3hw6Pm2yw6d-pdEq10dek-WWrsWRcw/exec?action=unsubscribe"
    public_html = html.replace("{{UNSUBSCRIBE_URL}}", DEFAULT_UNSUB_BASE)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_json = os.path.join(script_dir, json_path)
    out_html = os.path.join(script_dir, html_path)

    try:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(public_html)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Saved latest email artifacts: {json_path} ({len(json.dumps(payload)):,} bytes) & {html_path}")
        return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: Failed to save email artifacts: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="NC Early Voting Daily Change Summary Emailer")
    parser.add_argument("--prev-day", type=int, default=None, help="Previous EV day (default: auto)")
    parser.add_argument("--curr-day", type=int, default=None, help="Current EV day (default: auto)")
    parser.add_argument("--recipient", default=None, help="Recipient email address")
    parser.add_argument("--extra-recipients", default=None, help="Comma-separated additional recipients")
    parser.add_argument("--subject", default=None, help="Custom email subject line")
    parser.add_argument("--subscribers", action="store_true", help="Send email to all active database subscribers")
    parser.add_argument("--force", action="store_true", help="Force sending even if already dispatched today")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without sending email")
    parser.add_argument("--save-artifacts-only", action="store_true", help="Save latest_daily_email.json/html without sending")
    parser.add_argument("--html-preview", help="Save HTML preview to specified file")
    args = parser.parse_args()

    data = compute_daily_changes(args.prev_day, args.curr_day)
    save_latest_email_artifacts(data)

    if args.save_artifacts_only:
        return

    if args.html_preview:
        with open(args.html_preview, 'w') as f:
            f.write(format_html(data))
        print(f"Saved HTML preview to {args.html_preview}")

    if args.dry_run:
        print(format_plain_text(data))
        return

    # Policy Guard: Only skip automatic routine subscriber dispatch if past cutoff and not forced
    from zoneinfo import ZoneInfo
    ny_now = datetime.now(ZoneInfo("America/New_York"))
    cutoff = datetime(2026, 11, 1, 12, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    if ny_now > cutoff and not args.force and not args.recipient and not args.subject:
        print(f"[{ny_now.strftime('%H:%M:%S')}] Notice: Early voting prediction email dispatch concluded after Sunday morning (Nov 1, 2026). Use --force or explicit --recipient to send.")
        return

    if args.subscribers:
        curr_day = data['curr_day']
        if not args.force and is_day_dispatched(curr_day):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Notice: EV Day {curr_day} update email was already dispatched today. Use --force to resend.")
            return

        success = send_summary_email(
            data,
            send_to_subscribers=True,
            extra_recipients=args.extra_recipients,
            custom_subject=args.subject
        )
        if success:
            record_day_dispatched(curr_day)
    else:
        success = send_summary_email(
            data,
            recipient=args.recipient or DEFAULT_RECIPIENT,
            extra_recipients=args.extra_recipients,
            custom_subject=args.subject
        )

    if not success and not (os.getenv("SMTP_PASSWORD") and os.getenv("SMTP_USER")):
        print("\nNote: To send emails locally, set SMTP_USER and SMTP_PASSWORD in .env or run via GitHub Actions.")

if __name__ == "__main__":
    main()

