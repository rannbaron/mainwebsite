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
import subscriptions

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
        f"  - Statewide Rating: {sf['rating']} [Call: {sf['call_confidence']} | Margin: {sf['margin_confidence']}]",
        f"  - Rating Changes Detected: {len(data['rating_changes'])} county change(s)",
        f"  - Confidence Shifts Detected: {len(data['confidence_changes'])} county shift(s) ({len(data['call_conf_changes'])} Call, {len(data['margin_conf_changes'])} Margin)",
        "",
        "UNDERSTANDING MODEL CONFIDENCE:",
        "  * Call confidence is how confident the model is about Democrats or Republicans winning that county.",
        "  * Margin confidence is how confident the model is about the numerical final outcome in that county, such as D+5, or R+3.",
        "  (Scale: very low confidence | low confidence | moderate confidence | high confidence | very high confidence)",
        "",
        "=" * 70,
        f"2. COUNTY RATING CHANGES (Day-over-Day) — {len(data['rating_changes'])} COUNTIES",
        "=" * 70,
    ]

    if data['rating_changes']:
        for c in data['rating_changes']:
            m_sign = '+' if c['margin_curr'] > 0 else ''
            lines.extend([
                f"  * {c['county'].upper()}: {c['rating_prev']} -> {c['rating_curr']}",
                f"    - Forecast Dem Share: {c['dem_prev']}% -> {c['dem_curr']}% ({c['shift']:+.2f}%) | Margin: {m_sign}{c['margin_curr']:.2f}%",
                f"    - Flip Probability P(Dem): {c['p_dem_prev']}% -> {c['p_dem_curr']}% ({c['p_shift']:+.1f}%)",
                f"    - Model Confidence: Call: {c['call_confidence']} | Margin: {c['margin_confidence']}",
                f"    - 95% Margin CI: [{c['ci_margin_low']:+.1f}%, {c['ci_margin_high']:+.1f}%]",
                ""
            ])
    else:
        lines.append("  No county rating changes detected today.\n")

    lines.extend([
        "=" * 70,
        f"3. COUNTY CONFIDENCE CHANGES (Day-over-Day) — {len(data['confidence_changes'])} COUNTIES",
        "=" * 70,
    ])

    if data['confidence_changes']:
        if data['call_conf_changes']:
            lines.append("  Call Confidence Shifts (Certainty of Winner):")
            for c in data['call_conf_changes']:
                m_sign = '+' if c['margin_curr'] > 0 else ''
                lines.append(f"    * {c['county'].upper()}: {c['call_conf_prev']} -> {c['call_conf_curr']}")
                lines.append(f"      - 2026 Margin: {m_sign}{c['margin_curr']:.2f}% | 95% Margin CI: [{c['ci_margin_low']:+.1f}%, {c['ci_margin_high']:+.1f}%] | Rating: {c['rating_curr']}")
            lines.append("")

        if data['margin_conf_changes']:
            lines.append("  Margin Confidence Shifts (Precision of Numerical Outcome):")
            for c in data['margin_conf_changes']:
                lines.append(f"    * {c['county'].upper()}: {c['margin_conf_prev']} -> {c['margin_conf_curr']}")
                lines.append(f"      - 95% Margin CI: [{c['ci_margin_low']:+.1f}%, {c['ci_margin_high']:+.1f}%]")
            lines.append("")
    else:
        lines.append("  No county confidence changes detected today.\n")

    lines.extend([
        "=" * 70,
        f"4. PROJECTED FLIPS (2022 R -> 2026 D) — {len(data['current_flips'])} COUNTIES",
        "=" * 70,
    ])
    for c in data['current_flips']:
        m_sign = '+' if c['margin_curr'] > 0 else ''
        lines.append(f"  * {c['county']:<14} | 2026: {c['dem_curr']:.1f}% ({m_sign}{c['margin_curr']:.1f}%) | 2022: {c['actual_2022']:.1f}% | Call: {c['call_confidence']} | Margin: {c['margin_confidence']} | {c['rating_curr']}")

    lines.extend([
        "",
        "=" * 70,
        f"5. TOSS-UP BATTLEGROUNDS (40% - 60% Flip Probability) — {len(data['toss_ups'])} COUNTIES",
        "=" * 70,
    ])
    for c in data['toss_ups']:
        p_rep = round(100.0 - c['p_dem_curr'], 1)
        m_sign = '+' if c['margin_curr'] > 0 else ''
        lines.append(f"  * {c['county']:<14} | 2026: {c['dem_curr']:.1f}% ({m_sign}{c['margin_curr']:.1f}%) | D: {c['p_dem_curr']:.1f}% / R: {p_rep:.1f}% | Call: {c['call_confidence']} | Margin: {c['margin_confidence']} | 95% Margin CI: [{c['ci_margin_low']:+.1f}%, {c['ci_margin_high']:+.1f}%]")

    lines.extend([
        "",
        "=" * 70,
        "6. TOP COUNTY SHIFTS",
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
        "7. STATEWIDE RATINGS DISTRIBUTION",
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
        "To manage your subscription or unsubscribe, reply with 'unsubscribe'.",
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

    confidence_guide = """
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px 16px;margin:16px 0;font-size:13px;color:#334155;line-height:1.5;">
        <div style="font-weight:700;margin-bottom:4px;color:#0f172a;">Understanding Model Confidence:</div>
        <ul style="margin:0;padding-left:18px;">
            <li><strong>Call confidence:</strong> How confident the model is about Democrats or Republicans winning that county.</li>
            <li><strong>Margin confidence:</strong> How confident the model is about the numerical final outcome in that county, such as D+5, or R+3.</li>
        </ul>
        <div style="margin-top:6px;font-size:11px;color:#64748b;">Scale: <em>Very Low</em> &bull; <em>Low</em> &bull; <em>Moderate</em> &bull; <em>High</em> &bull; <em>Very High</em></div>
    </div>
    """

    # Build rating changes HTML
    if data['rating_changes']:
        rc_rows = "".join([
            f"""<tr>
                <td style="padding:10px 12px;font-weight:600;border-bottom:1px solid #e5e7eb;">{c['county']}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{badge(c['rating_prev'])} &rarr; {badge(c['rating_curr'])}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;"><strong>{c['dem_curr']:.2f}%</strong> ({'+' if c['margin_curr']>0 else ''}{c['margin_curr']:.2f}%) <span style="color:{'#16a34a' if c['shift'] > 0 else ('#dc2626' if c['shift'] < 0 else '#6b7280')};font-size:11px;font-weight:600;">({c['shift']:+.2f}%)</span></td>
                <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{conf_badge(c['call_confidence'])}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{conf_badge(c['margin_confidence'])}</td>
                <td style="padding:10px 12px;color:#6b7280;font-size:12px;border-bottom:1px solid #e5e7eb;">[{'+' if c['ci_margin_low']>0 else ''}{c['ci_margin_low']:.1f}%, {'+' if c['ci_margin_high']>0 else ''}{c['ci_margin_high']:.1f}%]</td>
            </tr>"""
            for c in data['rating_changes']
        ])
        rc_html = f"""
        {confidence_guide}
        <table style="width:100%;border-collapse:collapse;margin:12px 0;background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;">
            <thead>
                <tr style="background:#f3f4f6;text-align:left;font-size:12px;color:#4b5563;text-transform:uppercase;">
                    <th style="padding:10px 12px;">County</th>
                    <th style="padding:10px 12px;">Rating Change</th>
                    <th style="padding:10px 12px;">2026 Pred (Margin)</th>
                    <th style="padding:10px 12px;">Call Conf.</th>
                    <th style="padding:10px 12px;">Margin Conf.</th>
                    <th style="padding:10px 12px;">95% Margin CI</th>
                </tr>
            </thead>
            <tbody>{rc_rows}</tbody>
        </table>
        """
    else:
        rc_html = f"""
        {confidence_guide}
        <p style='color:#6b7280;font-style:italic;'>No county rating changes detected today.</p>
        """

    # Build confidence changes HTML
    if data['confidence_changes']:
        conf_rows = "".join([
            f"""<tr>
                <td style="padding:10px 12px;font-weight:600;border-bottom:1px solid #e5e7eb;">{c['county']}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{badge(c['rating_curr'])}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">
                    {f'<span style="color:#64748b;font-size:11px;">{c["call_conf_prev"].title().replace(" Confidence","")}</span> &rarr; ' if c['call_conf_changed'] else ''}{conf_badge(c['call_conf_curr'])}
                </td>
                <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">
                    {f'<span style="color:#64748b;font-size:11px;">{c["margin_conf_prev"].title().replace(" Confidence","")}</span> &rarr; ' if c['margin_conf_changed'] else ''}{conf_badge(c['margin_conf_curr'])}
                </td>
                <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">
                    <strong>{'+' if c['margin_curr']>0 else ''}{c['margin_curr']:.2f}%</strong>
                </td>
                <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;color:#64748b;font-size:12px;">
                    [{'+' if c['ci_margin_low']>0 else ''}{c['ci_margin_low']:.1f}%, {'+' if c['ci_margin_high']>0 else ''}{c['ci_margin_high']:.1f}%]
                </td>
            </tr>"""
            for c in data['confidence_changes']
        ])
        conf_html = f"""
        <table style="width:100%;border-collapse:collapse;margin:12px 0;background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;font-size:13px;">
            <thead>
                <tr style="background:#f3f4f6;text-align:left;font-size:11px;color:#4b5563;text-transform:uppercase;">
                    <th style="padding:10px 12px;">County</th>
                    <th style="padding:10px 12px;">Rating</th>
                    <th style="padding:10px 12px;">Call Confidence</th>
                    <th style="padding:10px 12px;">Margin Confidence</th>
                    <th style="padding:10px 12px;">Margin</th>
                    <th style="padding:10px 12px;">95% Margin CI</th>
                </tr>
            </thead>
            <tbody>{conf_rows}</tbody>
        </table>
        """
    else:
        conf_html = "<p style='color:#6b7280;font-style:italic;'>No county confidence changes detected today.</p>"

    # Build projected flips HTML
    flips_rows = "".join([
        f"""<tr>
            <td style="padding:8px 12px;font-weight:600;border-bottom:1px solid #e5e7eb;">{c['county']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{badge(c['rating_curr'])}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#dc2626;">{c['actual_2022']:.2f}%</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#2563eb;font-weight:700;">{c['dem_curr']:.2f}% ({'+' if c['margin_curr']>0 else ''}{c['margin_curr']:.2f}%)</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{conf_badge(c['call_confidence'])}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{conf_badge(c['margin_confidence'])}</td>
        </tr>"""
        for c in data['current_flips']
    ])

    # Build Toss Ups HTML
    toss_rows = "".join([
        f"""<tr>
            <td style="padding:8px 12px;font-weight:600;border-bottom:1px solid #e5e7eb;">{c['county']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{badge(c['rating_curr'])}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;"><strong>{c['dem_curr']:.2f}%</strong> ({'+' if c['margin_curr']>0 else ''}{c['margin_curr']:.2f}%)</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{conf_badge(c['call_confidence'])}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{conf_badge(c['margin_confidence'])}</td>
            <td style="padding:8px 12px;color:#6b7280;font-size:12px;border-bottom:1px solid #e5e7eb;">[{'+' if c['ci_margin_low']>0 else ''}{c['ci_margin_low']:.1f}%, {'+' if c['ci_margin_high']>0 else ''}{c['ci_margin_high']:.1f}%]</td>
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
                        <div style="font-size:20px;font-weight:800;color:#1d4ed8;margin-top:2px;">{sf['curr_dem']:.2f}% <span style="font-size:13px;color:{'#16a34a' if sf['dem_shift'] > 0 else ('#dc2626' if sf['dem_shift'] < 0 else '#6b7280')};">({sf['dem_shift']:+.2f}%)</span></div>
                        <div style="font-size:12px;color:#1e40af;margin-top:4px;">CI: {sf['curr_low']:.1f}% - {sf['curr_high']:.1f}% ({badge(sf['rating'])})</div>
                        <div style="font-size:11px;color:#475569;margin-top:4px;">Call: {conf_badge(sf['call_confidence'])} &bull; Margin: {conf_badge(sf['margin_confidence'])}</div>
                    </div>
                </div>

                <!-- Section 1: Rating Changes -->
                <h2 style="font-size:16px;font-weight:700;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:6px;margin:24px 0 12px 0;">
                    ⭐ County Rating Changes ({len(data['rating_changes'])})
                </h2>
                {rc_html}

                <!-- Section 2: Confidence Changes -->
                <h2 style="font-size:16px;font-weight:700;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:6px;margin:28px 0 12px 0;">
                    📶 County Confidence Shifts ({len(data['confidence_changes'])})
                </h2>
                {conf_html}

                <!-- Section 3: Projected Flips -->
                <h2 style="font-size:16px;font-weight:700;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:6px;margin:28px 0 12px 0;">
                    🔄 Projected Flips (2022 R &rarr; 2026 D) — {len(data['current_flips'])} Counties
                </h2>
                <table style="width:100%;border-collapse:collapse;margin:12px 0;background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
                    <thead>
                        <tr style="background:#f3f4f6;text-align:left;font-size:11px;color:#4b5563;text-transform:uppercase;">
                            <th style="padding:8px 12px;">County</th>
                            <th style="padding:8px 12px;">Rating</th>
                            <th style="padding:8px 12px;">2022 Dem</th>
                            <th style="padding:8px 12px;">2026 Pred (Margin)</th>
                            <th style="padding:8px 12px;">Call Conf.</th>
                            <th style="padding:8px 12px;">Margin Conf.</th>
                        </tr>
                    </thead>
                    <tbody>{flips_rows}</tbody>
                </table>

                <!-- Section 4: Toss Ups -->
                <h2 style="font-size:16px;font-weight:700;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:6px;margin:28px 0 12px 0;">
                    ⚖️ Toss-Up Battlegrounds (40% - 60% Flip Prob) — {len(data['toss_ups'])} Counties
                </h2>
                <table style="width:100%;border-collapse:collapse;margin:12px 0;background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
                    <thead>
                        <tr style="background:#f3f4f6;text-align:left;font-size:11px;color:#4b5563;text-transform:uppercase;">
                            <th style="padding:8px 12px;">County</th>
                            <th style="padding:8px 12px;">Rating</th>
                            <th style="padding:8px 12px;">2026 Pred (Margin)</th>
                            <th style="padding:8px 12px;">Call Conf.</th>
                            <th style="padding:8px 12px;">Margin Conf.</th>
                            <th style="padding:8px 12px;">95% Margin CI</th>
                        </tr>
                    </thead>
                    <tbody>{toss_rows}</tbody>
                </table>

                <!-- Section 5: Rating Breakdown -->
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
            <div style="border-top:1px solid #e5e7eb;padding:16px 28px;background:#f9fafb;font-size:11px;color:#9ca3af;text-align:center;line-height:1.6;">
                <div>Autonomous Early Voting Update System &bull; North Carolina 2026 Analysis</div>
                <div style="margin-top:4px;color:#6b7280;">You received this daily update because you are subscribed to early voting reports. To unsubscribe, simply reply to this email with &ldquo;unsubscribe&rdquo;.</div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def send_summary_email(data, recipient=None, send_to_subscribers=False):
    """Dispatches the multi-part email to subscribers or designated recipient."""
    load_env_file()

    if send_to_subscribers:
        recipients = subscriptions.get_active_subscribers()
        if not recipients:
            recipients = [DEFAULT_RECIPIENT]
    elif recipient:
        recipients = [recipient]
    else:
        recipients = [DEFAULT_RECIPIENT]

    # Deduplicate and normalize
    seen = set()
    unique_recipients = []
    for r in recipients:
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

    subject = f"NC Early Vote Day {data['curr_day']} Update {headline}"

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

    if not smtp_pass or not smtp_user:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: SMTP_USER or SMTP_PASSWORD not set in environment or .env.")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Cannot authenticate to {smtp_server}:{smtp_port}.")
        return False

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

        for rec in recipients:
            msg = MIMEMultipart("alternative")
            msg['From'] = formataddr(("NC Early Voting Updates", smtp_user))
            msg['To'] = rec
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid(domain="elections.map")

            part1 = MIMEText(plain_body, 'plain', 'utf-8')
            part2 = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)

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

    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_json = os.path.join(script_dir, json_path)
    out_html = os.path.join(script_dir, html_path)

    try:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(html)
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
    parser.add_argument("--subscribers", action="store_true", help="Send email to all active database subscribers")
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

    if args.subscribers:
        success = send_summary_email(data, send_to_subscribers=True)
    else:
        success = send_summary_email(data, recipient=args.recipient or DEFAULT_RECIPIENT)

    if not success and not (os.getenv("SMTP_PASSWORD") and os.getenv("SMTP_USER")):
        print("\nNote: To send emails locally, set SMTP_USER and SMTP_PASSWORD in .env or run via GitHub Actions.")

if __name__ == "__main__":
    main()

