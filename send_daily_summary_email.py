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
import math
import argparse
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid, formataddr

import pandas as pd
import vote_forecast

DEFAULT_RECIPIENT = "baronrann@gmail.com"

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

def find_available_days():
    """Finds all available daily party CSV files and returns sorted day numbers."""
    files = glob.glob("nc_early_voting_party_ev_day_*.csv")
    days = []
    for f in files:
        m = re.search(r'ev_day_(\d+)\.csv', f)
        if m:
            days.append(int(m.group(1)))
    days.sort()
    return days

def compute_daily_changes(prev_day=None, curr_day=None):
    """
    Computes all day-over-day changes between prev_day and curr_day.
    Returns a dict with all structured statistics and county change records.
    """
    days = find_available_days()
    if not days:
        raise FileNotFoundError("No daily party CSV files found (nc_early_voting_party_ev_day_*.csv).")

    if curr_day is None:
        curr_day = days[-1]
    if prev_day is None:
        idx = days.index(curr_day) if curr_day in days else len(days) - 1
        prev_day = days[max(0, idx - 1)]

    prev_file = f"nc_early_voting_party_ev_day_{prev_day}.csv"
    curr_file = f"nc_early_voting_party_ev_day_{curr_day}.csv"

    if not os.path.exists(curr_file):
        raise FileNotFoundError(f"Current day CSV not found: {curr_file}")
    if not os.path.exists(prev_file):
        raise FileNotFoundError(f"Previous day CSV not found: {prev_file}")

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

        c_info = {
            'county': cname.title(),
            'rating_prev': r_prev,
            'rating_curr': r_curr,
            'rating_changed': (r_prev != r_curr),
            'dem_prev': d_prev,
            'dem_curr': d_curr,
            'shift': shift,
            'p_dem_prev': p_dem_prev,
            'p_dem_curr': p_dem_curr,
            'p_shift': p_shift,
            'range_low': c_curr['range_low'],
            'range_high': c_curr['range_high'],
            'actual_2022': c_curr['actual_2022'],
            'winner_2022': 'D' if c_curr['actual_2022'] > 50.0 else 'R'
        }
        all_county_shifts.append(c_info)

        if r_prev != r_curr:
            rating_changes.append(c_info)

    # Sort shifts
    top_dem_shifts = sorted([c for c in all_county_shifts if c['shift'] > 0], key=lambda x: x['shift'], reverse=True)[:5]
    top_rep_shifts = sorted([c for c in all_county_shifts if c['shift'] < 0], key=lambda x: x['shift'])[:5]

    # Current Projected Flips (2022 R -> 2026 D)
    current_flips = [c for c in all_county_shifts if c['winner_2022'] == 'R' and c['dem_curr'] > 50.0]
    current_flips.sort(key=lambda x: x['p_dem_curr'], reverse=True)

    # Toss Ups (40% - 60% flip probability)
    toss_ups = [c for c in all_county_shifts if c['rating_curr'] == 'Toss Up']

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
            'ratings_summary_prev': st_prev.get('ratings_summary', {}),
            'ratings_summary_curr': st_curr.get('ratings_summary', {})
        },
        'rating_changes': rating_changes,
        'current_flips': current_flips,
        'toss_ups': toss_ups,
        'top_dem_shifts': top_dem_shifts,
        'top_rep_shifts': top_rep_shifts,
        'all_county_shifts': all_county_shifts
    }

def format_plain_text(data):
    """Generates a clean plain text version of the summary email."""
    t = data['turnout']
    sf = data['statewide_forecast']
    lines = [
        f"NC EARLY VOTING DAILY UPDATE: DAY {data['curr_day']} VS DAY {data['prev_day']}",
        f"Date: {data['date_str']}",
        f"=" * 70,
        "",
        "1. EXECUTIVE SUMMARY",
        f"  - Total Ballots Added: +{t['new_tot']:,} ({t['pct_increase']:+.1f}% increase; {t['prev_tot']:,} -> {t['curr_tot']:,})",
        f"  - Sunday Additions Party Split: Dem {t['pct_dem']}% | Rep {t['pct_rep']}% | Una {t['pct_una']}%",
        f"  - Statewide 2026 Forecast: Dem {sf['curr_dem']}% (was {sf['prev_dem']}%, shift {sf['dem_shift']:+.2f}%)",
        f"  - 95% Confidence Interval: [{sf['curr_low']}% - {sf['curr_high']}%] (Rating: {sf['rating']})",
        f"  - Rating Changes Detected: {len(data['rating_changes'])} county change(s)",
        "",
        "=" * 70,
        "2. COUNTY RATING CHANGES (Day-over-Day)",
        "=" * 70,
    ]

    if data['rating_changes']:
        for c in data['rating_changes']:
            lines.extend([
                f"  * {c['county'].upper()}: {c['rating_prev']} -> {c['rating_curr']}",
                f"    - Forecast Dem Share: {c['dem_prev']}% -> {c['dem_curr']}% ({c['shift']:+.2f}%)",
                f"    - Flip Probability P(Dem): {c['p_dem_prev']}% -> {c['p_dem_curr']}% ({c['p_shift']:+.1f}%)",
                f"    - 95% Bounds: [{c['range_low']}% - {c['range_high']}%]",
                ""
            ])
    else:
        lines.append("  No county rating changes detected today.")
        lines.append("")

    lines.extend([
        "=" * 70,
        f"3. PROJECTED FLIPS (2022 R -> 2026 D) — {len(data['current_flips'])} COUNTIES",
        "=" * 70,
    ])
    for c in data['current_flips']:
        lines.append(f"  * {c['county']:<14} | 2026 Pred: {c['dem_curr']:.1f}% | 2022 Act: {c['actual_2022']:.1f}% | P(Flip): {c['p_dem_curr']:.1f}% | {c['rating_curr']}")

    lines.extend([
        "",
        "=" * 70,
        f"4. TOSS-UP BATTLEGROUNDS (40% - 60% Flip Probability) — {len(data['toss_ups'])} COUNTIES",
        "=" * 70,
    ])
    for c in data['toss_ups']:
        p_rep = round(100.0 - c['p_dem_curr'], 1)
        lines.append(f"  * {c['county']:<14} | 2026 Pred: {c['dem_curr']:.1f}% | Flip Chance (D): {c['p_dem_curr']:.1f}% | Hold Chance (R): {p_rep:.1f}% | [{c['range_low']}% - {c['range_high']}%]")

    lines.extend([
        "",
        "=" * 70,
        "5. TOP COUNTY SHIFTS",
        "=" * 70,
        "  Top Shifts Toward Democrats:",
    ])
    for c in data['top_dem_shifts']:
        lines.append(f"    - {c['county']:<14}: {c['dem_prev']:.2f}% -> {c['dem_curr']:.2f}% ({c['shift']:+.2f}%) [{c['rating_curr']}]")

    lines.append("\n  Top Shifts Toward Republicans:")
    for c in data['top_rep_shifts']:
        lines.append(f"    - {c['county']:<14}: {c['dem_prev']:.2f}% -> {c['dem_curr']:.2f}% ({c['shift']:+.2f}%) [{c['rating_curr']}]")

    lines.extend([
        "",
        "=" * 70,
        "6. STATEWIDE RATINGS DISTRIBUTION",
        "=" * 70,
    ])
    summary_curr = sf['ratings_summary_curr']
    summary_prev = sf['ratings_summary_prev']
    for cat in ['Safe D', 'Very Likely D', 'Likely D', 'Lean D', 'Toss Up', 'Lean R', 'Likely R', 'Very Likely R', 'Safe R']:
        c_now = summary_curr.get(cat, 0)
        c_was = summary_prev.get(cat, 0)
        diff = c_now - c_was
        diff_str = f" ({diff:+d})" if diff != 0 else ""
        lines.append(f"  {cat:<14}: {c_now:2d} counties{diff_str}")

    lines.extend([
        "",
        "=" * 70,
        "Interactive Map: https://rannbaron.github.io/mainwebsite/",
        "=" * 70,
    ])
    return "\n".join(lines)

def format_html(data):
    """Generates an HTML version of the summary email."""
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
        elif "Lean R" in rating:
            bg, color = "#ffe4e6", "#be123c"
        elif "Likely R" in rating:
            bg, color = "#fee2e2", "#b91c1c"
        elif "Very Likely R" in rating:
            bg, color = "#fecdd3", "#9f1239"
        elif "Safe R" in rating:
            bg, color = "#ffd7d9", "#da1e28"
        return f'<span style="display:inline-block;padding:3px 8px;font-size:12px;font-weight:700;border-radius:4px;background:{bg};color:{color};">{rating}</span>'

    # Build rating changes HTML
    if data['rating_changes']:
        rc_rows = "".join([
            f"""<tr>
                <td style="padding:10px 12px;font-weight:600;border-bottom:1px solid #e5e7eb;">{c['county']}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{badge(c['rating_prev'])} &rarr; {badge(c['rating_curr'])}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{c['dem_prev']:.2f}% &rarr; <strong>{c['dem_curr']:.2f}%</strong> <span style="color:#16a34a;font-weight:600;">({c['shift']:+.2f}%)</span></td>
                <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{c['p_dem_prev']:.1f}% &rarr; <strong>{c['p_dem_curr']:.1f}%</strong></td>
                <td style="padding:10px 12px;color:#6b7280;font-size:12px;border-bottom:1px solid #e5e7eb;">{c['range_low']:.1f}% - {c['range_high']:.1f}%</td>
            </tr>"""
            for c in data['rating_changes']
        ])
        rc_html = f"""
        <table style="width:100%;border-collapse:collapse;margin:12px 0;background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;">
            <thead>
                <tr style="background:#f3f4f6;text-align:left;font-size:12px;color:#4b5563;text-transform:uppercase;">
                    <th style="padding:10px 12px;">County</th>
                    <th style="padding:10px 12px;">Rating Change</th>
                    <th style="padding:10px 12px;">Pred Dem %</th>
                    <th style="padding:10px 12px;">Flip Prob P(Dem)</th>
                    <th style="padding:10px 12px;">Dual-Regime CI</th>
                </tr>
            </thead>
            <tbody>{rc_rows}</tbody>
        </table>
        """
    else:
        rc_html = "<p style='color:#6b7280;font-style:italic;'>No county rating changes detected today.</p>"

    # Build projected flips HTML
    flips_rows = "".join([
        f"""<tr>
            <td style="padding:8px 12px;font-weight:600;border-bottom:1px solid #e5e7eb;">{c['county']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{badge(c['rating_curr'])}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#dc2626;">{c['actual_2022']:.2f}%</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#2563eb;font-weight:700;">{c['dem_curr']:.2f}%</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-weight:700;">{c['p_dem_curr']:.1f}%</td>
        </tr>"""
        for c in data['current_flips']
    ])

    # Build Toss Ups HTML
    toss_rows = "".join([
        f"""<tr>
            <td style="padding:8px 12px;font-weight:600;border-bottom:1px solid #e5e7eb;">{c['county']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{badge(c['rating_curr'])}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;"><strong>{c['dem_curr']:.2f}%</strong></td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#2563eb;font-weight:700;">{c['p_dem_curr']:.1f}%</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#dc2626;font-weight:700;">{100.0 - c['p_dem_curr']:.1f}%</td>
            <td style="padding:8px 12px;color:#6b7280;font-size:12px;border-bottom:1px solid #e5e7eb;">{c['range_low']:.1f}% - {c['range_high']:.1f}%</td>
        </tr>"""
        for c in data['toss_ups']
    ])

    # Summary table
    cats = ['Safe D', 'Very Likely D', 'Likely D', 'Lean D', 'Toss Up', 'Lean R', 'Likely R', 'Very Likely R', 'Safe R']
    summary_rows = "".join([
        f"""<tr>
            <td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;">{badge(cat)}</td>
            <td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-weight:700;text-align:right;">
                {sf['ratings_summary_curr'].get(cat, 0)}
                {' <span style="color:#16a34a;font-size:11px;">(+' + str(sf['ratings_summary_curr'].get(cat, 0) - sf['ratings_summary_prev'].get(cat, 0)) + ')</span>' if sf['ratings_summary_curr'].get(cat, 0) > sf['ratings_summary_prev'].get(cat, 0) else ''}
                {' <span style="color:#dc2626;font-size:11px;">(' + str(sf['ratings_summary_curr'].get(cat, 0) - sf['ratings_summary_prev'].get(cat, 0)) + ')</span>' if sf['ratings_summary_curr'].get(cat, 0) < sf['ratings_summary_prev'].get(cat, 0) else ''}
            </td>
        </tr>"""
        for cat in cats
    ])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NC Early Voting Daily Update</title>
    </head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.5;color:#1f2937;background-color:#f9fafb;margin:0;padding:24px;">
        <div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);border:1px solid #e5e7eb;overflow:hidden;">
            <!-- Header -->
            <div style="background:linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);color:#ffffff;padding:24px 28px;">
                <div style="font-size:12px;text-transform:uppercase;letter-spacing:1px;font-weight:700;color:#93c5fd;">Daily Intelligence Report</div>
                <h1 style="margin:6px 0 4px 0;font-size:22px;font-weight:800;color:#ffffff;">NC Early Voting: Day {data['curr_day']} vs Day {data['prev_day']}</h1>
                <div style="font-size:13px;color:#bfdbfe;">{data['date_str']} &bull; Option 1 Dual-Regime Model</div>
            </div>

            <div style="padding:24px 28px;">
                <!-- Key Stat Callout Cards -->
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">
                    <div style="background:#f0fdf4;border:1px solid #bbf7d0;padding:14px;border-radius:6px;">
                        <div style="font-size:11px;font-weight:700;color:#166534;text-transform:uppercase;">New Ballots Added</div>
                        <div style="font-size:20px;font-weight:800;color:#15803d;margin-top:2px;">+{t['new_tot']:,}</div>
                        <div style="font-size:12px;color:#166534;margin-top:4px;">Dem {t['pct_dem']}% | Rep {t['pct_rep']}% | Una {t['pct_una']}%</div>
                    </div>
                    <div style="background:#eff6ff;border:1px solid #bfdbfe;padding:14px;border-radius:6px;">
                        <div style="font-size:11px;font-weight:700;color:#1e40af;text-transform:uppercase;">2026 Forecast Dem Share</div>
                        <div style="font-size:20px;font-weight:800;color:#1d4ed8;margin-top:2px;">{sf['curr_dem']:.2f}% <span style="font-size:13px;color:#16a34a;">({sf['dem_shift']:+.2f}%)</span></div>
                        <div style="font-size:12px;color:#1e40af;margin-top:4px;">CI: {sf['curr_low']:.1f}% - {sf['curr_high']:.1f}% ({badge(sf['rating'])})</div>
                    </div>
                </div>

                <!-- Section 1: Rating Changes -->
                <h2 style="font-size:16px;font-weight:700;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:6px;margin:24px 0 12px 0;">
                    ⭐ County Rating Changes ({len(data['rating_changes'])})
                </h2>
                {rc_html}

                <!-- Section 2: Projected Flips -->
                <h2 style="font-size:16px;font-weight:700;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:6px;margin:28px 0 12px 0;">
                    🔄 Projected Flips (2022 R &rarr; 2026 D) — {len(data['current_flips'])} Counties
                </h2>
                <table style="width:100%;border-collapse:collapse;margin:12px 0;background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
                    <thead>
                        <tr style="background:#f3f4f6;text-align:left;font-size:11px;color:#4b5563;text-transform:uppercase;">
                            <th style="padding:8px 12px;">County</th>
                            <th style="padding:8px 12px;">Rating</th>
                            <th style="padding:8px 12px;">2022 Dem</th>
                            <th style="padding:8px 12px;">2026 Pred</th>
                            <th style="padding:8px 12px;">Flip Prob</th>
                        </tr>
                    </thead>
                    <tbody>{flips_rows}</tbody>
                </table>

                <!-- Section 3: Toss Ups -->
                <h2 style="font-size:16px;font-weight:700;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:6px;margin:28px 0 12px 0;">
                    ⚖️ Toss-Up Battlegrounds (40% - 60% Flip Prob) — {len(data['toss_ups'])} Counties
                </h2>
                <table style="width:100%;border-collapse:collapse;margin:12px 0;background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
                    <thead>
                        <tr style="background:#f3f4f6;text-align:left;font-size:11px;color:#4b5563;text-transform:uppercase;">
                            <th style="padding:8px 12px;">County</th>
                            <th style="padding:8px 12px;">Rating</th>
                            <th style="padding:8px 12px;">Pred Dem</th>
                            <th style="padding:8px 12px;">Flip (D)</th>
                            <th style="padding:8px 12px;">Hold (R)</th>
                            <th style="padding:8px 12px;">95% CI</th>
                        </tr>
                    </thead>
                    <tbody>{toss_rows}</tbody>
                </table>

                <!-- Section 4: Rating Breakdown -->
                <h2 style="font-size:16px;font-weight:700;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:6px;margin:28px 0 12px 0;">
                    📊 Statewide County Ratings Breakdown
                </h2>
                <table style="width:100%;max-width:380px;border-collapse:collapse;margin:12px 0;background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
                    <tbody>{summary_rows}</tbody>
                </table>

                <!-- Footer Call to Action -->
                <div style="margin-top:32px;padding:16px;background:#f3f4f6;border-radius:6px;text-align:center;">
                    <div style="font-size:13px;color:#4b5563;margin-bottom:8px;">View live precinct swings, turnout progression, and dual-regime map:</div>
                    <a href="https://rannbaron.github.io/mainwebsite/" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;font-weight:700;padding:8px 18px;border-radius:4px;font-size:13px;">Open Early Vote Swing Explorer &rarr;</a>
                </div>
            </div>

            <!-- Email footer -->
            <div style="border-top:1px solid #e5e7eb;padding:16px 28px;background:#f9fafb;font-size:11px;color:#9ca3af;text-align:center;">
                Autonomous Early Voting Update System &bull; North Carolina 2026 Analysis
            </div>
        </div>
    </body>
    </html>
    """
    return html

def send_summary_email(data, recipient=DEFAULT_RECIPIENT):
    """Dispatches the multi-part email to the designated recipient."""
    load_env_file()

    rating_change_count = len(data['rating_changes'])
    if rating_change_count > 0:
        headline = f"({rating_change_count} Rating Change: " + ", ".join([f"{c['county']} {c['rating_prev']}->{c['rating_curr']}" for c in data['rating_changes'][:2]]) + ")"
    else:
        headline = "(Ratings Steady)"

    subject = f"NC Early Vote Day {data['curr_day']} Update {headline}"

    plain_body = format_plain_text(data)
    html_body = format_html(data)

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    if smtp_pass:
        smtp_pass = smtp_pass.replace(" ", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Preparing email notification to {recipient}...")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Subject: {subject}")

    if not smtp_pass or not smtp_user:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: SMTP_USER or SMTP_PASSWORD not set in environment or .env.")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Cannot authenticate to {smtp_server}:{smtp_port}.")
        return False

    msg = MIMEMultipart("alternative")
    msg['From'] = formataddr(("NC Early Voting Updates", smtp_user))
    msg['To'] = recipient
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain="elections.map")

    part1 = MIMEText(plain_body, 'plain', 'utf-8')
    part2 = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(part1)
    msg.attach(part2)

    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Connecting to SMTP server {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.ehlo()
        if smtp_port == 587 or "gmail" in smtp_server:
            server.starttls()
            server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [recipient], msg.as_string())
        server.quit()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Email successfully delivered via {smtp_server}:{smtp_port} to {recipient}!")
        return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] SMTP delivery error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="NC Early Voting Daily Change Summary Emailer")
    parser.add_argument("--prev-day", type=int, default=None, help="Previous EV day (default: auto)")
    parser.add_argument("--curr-day", type=int, default=None, help="Current EV day (default: auto)")
    parser.add_argument("--recipient", default=DEFAULT_RECIPIENT, help="Recipient email address")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without sending email")
    parser.add_argument("--html-preview", help="Save HTML preview to specified file")
    args = parser.parse_args()

    data = compute_daily_changes(args.prev_day, args.curr_day)

    if args.html_preview:
        with open(args.html_preview, 'w') as f:
            f.write(format_html(data))
        print(f"Saved HTML preview to {args.html_preview}")

    if args.dry_run:
        print(format_plain_text(data))
        return

    success = send_summary_email(data, recipient=args.recipient)
    if not success and not (os.getenv("SMTP_PASSWORD") and os.getenv("SMTP_USER")):
        print("\nNote: To send emails locally, set SMTP_USER and SMTP_PASSWORD in .env or run via GitHub Actions.")

if __name__ == "__main__":
    main()

