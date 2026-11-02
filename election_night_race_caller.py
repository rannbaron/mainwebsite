#!/usr/bin/env python3
"""
Election Night Race Caller & Decision Desk Engine (rannbar-on.com/needle)
------------------------------------------------------------------------
Monitors live returns across all North Carolina races (5 Statewide, 3 Amendments,
50 NC Senate, 120 NC House, 14 US Congressional districts).

Decision Desk Rule:
As soon as the Bayesian 3-mode decomposition needle model attains >= 95.0% confidence
in the outcome of any NC race (P(winner) >= 0.95), this engine immediately:
  1. Sends an alert email to Rann (rann@rannbar-on.com and rb6@duke.edu)
     Title: RACE CALL <name of race> <winner> <party>
  2. Updates needle/called_races.json and needle/needle_data.json
     so the website needle immediately pops up the winner notification modal
     with the winner's picture surrounded by their party color (Red for REP, Blue for DEM).

Usage:
  python3 election_night_race_caller.py --check
  python3 election_night_race_caller.py --simulate eday50
  python3 election_night_race_caller.py --test-email
  python3 election_night_race_caller.py --daemon --interval 30
"""

import os
import sys
import json
import math
import time
import re
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEEDLE_DIR = os.path.join(BASE_DIR, 'needle')
DATA_PATH = os.path.join(NEEDLE_DIR, 'needle_data.json')
CALLED_RACES_PATH = os.path.join(NEEDLE_DIR, 'called_races.json')
CANDIDATES_DIR = os.path.join(NEEDLE_DIR, 'candidates')

CONFIDENCE_THRESHOLD = 0.95  # 95% Bayesian posterior confidence threshold
NOTIFICATION_RECIPIENTS = ['rann@rannbar-on.com', 'rb6@duke.edu']

# Fallback normal CDF (Abramowitz & Stegun approximation)
def normal_cdf(x):
    a1 =  0.254829592
    a2 = -0.284496736
    a3 =  1.421413741
    a4 = -1.453152027
    a5 =  1.061405429
    p  =  0.3275911
    sign = -1 if x < 0 else 1
    abs_x = abs(x) / math.sqrt(2.0)
    t = 1.0 / (1.0 + p * abs_x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-abs_x * abs_x)
    return 0.5 * (1.0 + sign * y)

def to_slug(name):
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', str(name)).lower()
    return '_'.join(clean.split())

def get_candidate_photo_url(name, party):
    if not name:
        return None
    slug = to_slug(name)
    known_jpgs = {'roy_cooper', 'michael_whatley', 'sarah_stevens', 'anita_earls', 'john_arrowood', 'christine_walczyk', 'craig_collins'}
    if slug in known_jpgs:
        return f"https://rannbar-on.com/needle/candidates/{slug}.jpg"
    return f"https://rannbar-on.com/needle/candidates/{slug}.svg"

def load_needle_dataset():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Needle dataset not found at {DATA_PATH}")
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_called_races():
    if os.path.exists(CALLED_RACES_PATH):
        try:
            with open(CALLED_RACES_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed reading {CALLED_RACES_PATH}: {e}")
    return {}

def save_called_races(called_dict):
    os.makedirs(NEEDLE_DIR, exist_ok=True)
    with open(CALLED_RACES_PATH, 'w', encoding='utf-8') as f:
        json.dump(called_dict, f, indent=2)

    # Also sync into needle_data.json under 'called_races'
    try:
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['called_races'] = called_dict
            data['last_race_call_at'] = datetime.now().isoformat()
            with open(DATA_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, separators=(',', ':'))
    except Exception as e:
        print(f"Warning: Failed updating {DATA_PATH} with called races: {e}")

# ==============================================================================
# BAYESIAN 3-MODE PROJECTION CALCULATION
# ==============================================================================
def project_race(race_obj, live_returns_dict):
    """
    Computes Bayesian posterior projection for a contest with 3-mode decomposition:
    Absentee by Mail, One-Stop Early Voting, Election Day In-Person.
    """
    is_statewide = bool(race_obj.get('counties') and not race_obj.get('precincts'))
    units = race_obj.get('counties', []) if is_statewide else race_obj.get('precincts', [])
    r_returns = live_returns_dict.get(race_obj['id'], {})

    counted_dem = 0
    counted_rep = 0
    counted_tot = 0
    counted_units = 0

    mode_stats = {
        'mail': {'dem': 0, 'rep': 0, 'tot': 0, 'benchExp': 0},
        'early': {'dem': 0, 'rep': 0, 'tot': 0, 'benchExp': 0},
        'eday': {'dem': 0, 'rep': 0, 'tot': 0, 'benchExp': 0}
    }

    for u in units:
        u_id = u.get('id') or u.get('county')
        ret = r_returns.get(u_id)
        if ret and ret.get('reported') and ret.get('totVotes', 0) > 0:
            counted_dem += ret.get('demVotes', 0)
            counted_rep += ret.get('repVotes', 0)
            counted_tot += ret.get('totVotes', 0)
            counted_units += 1

            for m_key in ['mail', 'early', 'eday']:
                m_ret = ret.get(m_key)
                m_bench = u.get('modes', {}).get(m_key)
                if m_ret and m_ret.get('tot', 0) > 0:
                    mode_stats[m_key]['dem'] += m_ret.get('dem', 0)
                    mode_stats[m_key]['rep'] += m_ret.get('rep', 0)
                    mode_stats[m_key]['tot'] += m_ret.get('tot', 0)
                    if m_bench:
                        mode_stats[m_key]['benchExp'] += m_ret.get('tot', 0) * (m_bench.get('bench_m', 0) / 100.0)

    total_expected = race_obj.get('proj_turnout', 50000)
    frac_counted = min(1.0, counted_tot / total_expected) if total_expected > 0 else 0.0

    # Mode swings
    mode_swings = {}
    weighted_obs_swing = 0.0
    total_swing_weight = 0.0

    for m_key in ['mail', 'early', 'eday']:
        st = mode_stats[m_key]
        if st['tot'] > 0:
            obs_m = (st['dem'] - st['rep']) / st['tot'] * 100.0
            exp_m = (st['benchExp'] / st['tot']) * 100.0
            sw = obs_m - exp_m
            mode_swings[m_key] = sw
            weighted_obs_swing += sw * st['tot']
            total_swing_weight += st['tot']

    overall_swing = (weighted_obs_swing / total_swing_weight) if total_swing_weight > 0 else 0.0
    shrinkage = math.pow(frac_counted, 0.7)
    modeled_general_swing = overall_swing * shrinkage

    remaining_dem = 0
    remaining_rep = 0

    for u in units:
        u_id = u.get('id') or u.get('county')
        ret = r_returns.get(u_id)
        has_modes = bool(u.get('modes'))

        if has_modes:
            for m_key in ['mail', 'early', 'eday']:
                m_ret = ret.get(m_key) if (ret and ret.get('reported')) else None
                m_bench = u.get('modes', {}).get(m_key)

                if (not m_ret or m_ret.get('tot', 0) == 0) and m_bench and m_bench.get('proj', 0) > 0:
                    spec_swing = mode_swings[m_key] * shrinkage if m_key in mode_swings else modeled_general_swing
                    adj_m = max(-100.0, min(100.0, m_bench.get('bench_m', 0.0) + spec_swing))
                    p_dem = round(m_bench.get('proj', 0) * (100.0 + adj_m) / 200.0)
                    p_rep = max(0, m_bench.get('proj', 0) - p_dem)
                    remaining_dem += p_dem
                    remaining_rep += p_rep
        else:
            if not ret or not ret.get('reported'):
                adj_m = max(-100.0, min(100.0, u.get('bench_margin', 0.0) + modeled_general_swing))
                p_dem = round(u.get('proj_turnout', 0) * (100.0 + adj_m) / 200.0)
                p_rep = max(0, u.get('proj_turnout', 0) - p_dem)
                remaining_dem += p_dem
                remaining_rep += p_rep

    projected_dem = counted_dem + remaining_dem
    projected_rep = counted_rep + remaining_rep
    projected_tot = max(1, projected_dem + projected_rep)
    projected_margin = (projected_dem - projected_rep) / projected_tot * 100.0

    base_sigma = race_obj.get('sigma', 2.0)
    current_sigma = max(0.25, base_sigma * math.sqrt(max(0.01, 1.0 - frac_counted)))

    z = projected_margin / current_sigma
    win_prob_dem = normal_cdf(z)
    win_prob_rep = 1.0 - win_prob_dem

    return {
        'counted_dem': counted_dem,
        'counted_rep': counted_rep,
        'counted_tot': counted_tot,
        'counted_units': counted_units,
        'total_units': len(units),
        'frac_counted': frac_counted,
        'projected_dem': projected_dem,
        'projected_rep': projected_rep,
        'projected_tot': projected_tot,
        'projected_margin': projected_margin,
        'current_sigma': current_sigma,
        'ci_low': projected_margin - 1.96 * current_sigma,
        'ci_high': projected_margin + 1.96 * current_sigma,
        'win_prob_dem': win_prob_dem,
        'win_prob_rep': win_prob_rep,
        'mode_stats': mode_stats
    }

# ==============================================================================
# MS GRAPH EMAIL DISPATCH ENGINE
# ==============================================================================
def send_race_call_email(race_call):
    """
    Sends urgent RACE CALL notification email to Rann via MS Graph.
    Exact Subject Requirement:
      RACE CALL <name of race> <winner> <party>
    """
    import msal
    import requests

    race_name = race_call['race_name']
    winner = race_call['winner']
    party = race_call['party']
    subject = f"RACE CALL {race_name} {winner} {party}"

    sender = "rb6@duke.edu"
    cache_path = os.path.expanduser("~/.duke_token_cache.bin")
    if not os.path.exists(cache_path):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] MS Graph Warning: Token cache {cache_path} not found.")
        return False

    cache = msal.SerializableTokenCache()
    with open(cache_path, "r") as f:
        cache.deserialize(f.read())

    app = msal.PublicClientApplication(
        "14d82eec-204b-4c2f-b7e8-296a70dab67e",
        authority="https://login.microsoftonline.com/cb72c54e-4a31-4d9e-b14a-1ea36dfac94c",
        token_cache=cache
    )
    accounts = app.get_accounts(username=sender) or app.get_accounts()
    if not accounts:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] MS Graph Error: No account found for {sender}.")
        return False

    token_result = app.acquire_token_silent(["https://graph.microsoft.com/Mail.Send"], account=accounts[0])
    if not token_result or "access_token" not in token_result:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] MS Graph Error: Failed to acquire silent access token.")
        return False

    access_token = token_result["access_token"]
    url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Theme colors
    is_dem = (party.upper() == 'DEMOCRAT')
    primary_color = "#2563eb" if is_dem else "#dc2626"
    badge_bg = "rgba(37, 99, 235, 0.15)" if is_dem else "rgba(220, 38, 38, 0.15)"
    badge_border = "#3b82f6" if is_dem else "#ef4444"
    glow_shadow = "0 0 25px rgba(37, 99, 235, 0.6)" if is_dem else "0 0 25px rgba(220, 38, 38, 0.6)"

    cand_img_url = race_call.get('photo_url') or get_candidate_photo_url(winner, party)

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #020617; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #020617; padding: 24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 620px; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), {glow_shadow};">
          
          <!-- Top Urgency Banner -->
          <tr>
            <td style="background: linear-gradient(90deg, {primary_color}, #0f172a); padding: 14px 24px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td>
                    <span style="display: inline-block; background-color: #ffffff; color: #020617; font-size: 11px; font-weight: 900; letter-spacing: 1.5px; padding: 4px 10px; border-radius: 9999px; text-transform: uppercase;">
                      🚨 OFFICIAL RACE CALL
                    </span>
                  </td>
                  <td align="right">
                    <span style="color: #cbd5e1; font-size: 12px; font-weight: 600;">
                      {race_call.get('called_at', datetime.now().strftime('%b %d, %I:%M %p EST'))}
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Race Title Header -->
          <tr>
            <td style="padding: 24px 24px 12px 24px; text-align: center;">
              <div style="font-size: 13px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px;">
                {race_call.get('chamber_label', 'North Carolina Decision Desk')}
              </div>
              <h1 style="margin: 0; font-size: 26px; font-weight: 900; color: #ffffff; line-height: 1.2;">
                {race_name}
              </h1>
            </td>
          </tr>

          <!-- Winner Card with Party-Colored Glowing Portrait -->
          <tr>
            <td style="padding: 12px 24px 24px 24px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #1e293b; border: 2px solid {badge_border}; border-radius: 14px; padding: 20px; box-shadow: {glow_shadow};">
                <tr>
                  <td width="110" align="center" valign="middle">
                    <div style="width: 96px; height: 96px; border-radius: 50%; border: 4px solid {primary_color}; overflow: hidden; background-color: #020617; box-shadow: {glow_shadow};">
                      <img src="{cand_img_url}" alt="{winner}" width="96" height="96" style="width: 100%; height: 100%; object-fit: cover; display: block;" onerror="this.onerror=null; this.src='https://rannbar-on.com/needle/candidates/{to_slug(winner)}.svg';" />
                    </div>
                  </td>
                  <td style="padding-left: 20px;" valign="middle">
                    <div style="font-size: 12px; font-weight: 800; color: {primary_color}; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 4px;">
                      PROJECTED WINNER
                    </div>
                    <div style="font-size: 24px; font-weight: 900; color: #ffffff; line-height: 1.1; margin-bottom: 8px;">
                      {winner}
                    </div>
                    <div>
                      <span style="display: inline-block; background-color: {badge_bg}; color: {badge_border}; border: 1px solid {badge_border}; font-size: 12px; font-weight: 800; padding: 3px 12px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">
                        {party}
                      </span>
                      <span style="display: inline-block; margin-left: 8px; background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b981; font-size: 12px; font-weight: 800; padding: 3px 12px; border-radius: 9999px;">
                        ✓ {race_call.get('confidence_str', '≥95.0% Confidence')}
                      </span>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Key Metrics Grid -->
          <tr>
            <td style="padding: 0 24px 20px 24px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td width="32%" style="background-color: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 12px; text-align: center;">
                    <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px;">Projected Margin</div>
                    <div style="font-size: 18px; font-weight: 900; color: {primary_color};">{race_call.get('proj_margin_str', 'N/A')}</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 2px;">95% CI: {race_call.get('ci_str', '')}</div>
                  </td>
                  <td width="2%"></td>
                  <td width="32%" style="background-color: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 12px; text-align: center;">
                    <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px;">Win Confidence</div>
                    <div style="font-size: 18px; font-weight: 900; color: #10b981;">{race_call.get('win_prob_pct', '95.0')}%</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 2px;">Posterior Threshold</div>
                  </td>
                  <td width="2%"></td>
                  <td width="32%" style="background-color: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 12px; text-align: center;">
                    <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px;">Reported Turnout</div>
                    <div style="font-size: 18px; font-weight: 900; color: #f8fafc;">{race_call.get('reported_pct_str', '0.0%')}</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 2px;">{race_call.get('units_str', '')}</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Mode Decomposition Summary -->
          {race_call.get('modes_html', '')}

          <!-- View on Needle Button -->
          <tr>
            <td style="padding: 10px 24px 28px 24px; text-align: center;">
              <a href="https://rannbar-on.com/needle/?race={race_call['race_id']}" style="display: inline-block; background-color: {primary_color}; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 800; padding: 14px 28px; border-radius: 10px; box-shadow: {glow_shadow};">
                View Live Race Needle & Precinct Map &rarr;
              </a>
              <div style="margin-top: 10px; font-size: 11px; color: #64748b;">
                Simultaneous alert dispatched to needle website popup banner at rannbar-on.com/needle
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #090d16; border-top: 1px solid #1e293b; padding: 16px 24px; text-align: center; font-size: 11px; color: #64748b;">
              Antigravity Decision Desk &bull; 3-Mode Bayesian Probabilistic Needle &bull; North Carolina 2026
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    delivered = 0
    for rec in NOTIFICATION_RECIPIENTS:
        payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": html_body
                },
                "toRecipients": [{"emailAddress": {"address": rec}}]
            },
            "saveToSentItems": "true"
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code == 202:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ MS Graph RACE CALL sent to {rec}: '{subject}'")
                delivered += 1
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ MS Graph failed for {rec}: HTTP {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ MS Graph error for {rec}: {e}")

    return delivered > 0

# ==============================================================================
# RACE CALLING ENGINE CORE
# ==============================================================================
def evaluate_all_races(live_returns=None, simulate_stage=None, dry_run=False):
    """
    Evaluates all statewide and legislative contests.
    Calls any race attaining >= 95% confidence that hasn't been called yet.
    """
    data = load_needle_dataset()
    called_races = load_called_races()

    if live_returns is None:
        live_returns = data.get('live_returns', {})

    new_calls = []

    # Helper to evaluate an individual race
    def evaluate_contest(race_id, race_obj, chamber_label):
        proj = project_race(race_obj, live_returns)
        
        # Don't call race if 0 votes reported (unless simulate_stage is set or uncontested)
        if proj['counted_tot'] == 0 and not simulate_stage and not race_obj.get('is_uncontested'):
            return

        p_dem = proj['win_prob_dem']
        p_rep = proj['win_prob_rep']

        called_party = None
        winner_name = None
        win_prob = 0.0

        if p_dem >= CONFIDENCE_THRESHOLD:
            called_party = 'Democrat'
            winner_name = race_obj.get('dem_candidate', 'Democratic Candidate')
            win_prob = p_dem
        elif p_rep >= CONFIDENCE_THRESHOLD:
            called_party = 'Republican'
            winner_name = race_obj.get('rep_candidate', 'Republican Candidate')
            win_prob = p_rep

        if called_party and race_id not in called_races:
            now_iso = datetime.now().isoformat()
            now_str = datetime.now().strftime('%I:%M %p EST')
            
            m_sign = '+' if proj['projected_margin'] > 0 else ''
            m_str = f"DEM {m_sign}{proj['projected_margin']:.1f}%" if proj['projected_margin'] > 0 else f"REP +{abs(proj['projected_margin']):.1f}%"
            ci_str = f"[{proj['ci_low']:+.1f}%, {proj['ci_high']:+.1f}%]"

            race_name = race_obj.get('short_title') or race_obj.get('name') or race_obj.get('title')

            call_record = {
                'race_id': race_id,
                'race_name': race_name,
                'chamber_label': chamber_label,
                'winner': winner_name,
                'party': called_party,
                'win_prob': win_prob,
                'win_prob_pct': f"{win_prob * 100:.1f}",
                'confidence_str': f"{win_prob * 100:.1f}% Confidence",
                'projected_margin': proj['projected_margin'],
                'proj_margin_str': m_str,
                'ci_str': ci_str,
                'counted_tot': proj['counted_tot'],
                'reported_pct_str': f"{proj['frac_counted'] * 100:.1f}%",
                'units_str': f"{proj['counted_units']}/{proj['total_units']} Units",
                'photo_url': get_candidate_photo_url(winner_name, called_party),
                'called_at': now_str,
                'called_at_iso': now_iso,
                'call_title': f"RACE CALL {race_name} {winner_name} {called_party}"
            }

            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚨 NEW RACE CALL: {call_record['call_title']} ({win_prob*100:.1f}%)")
            new_calls.append(call_record)
            called_races[race_id] = call_record

            if not dry_run:
                # 1. Send urgent email to Rann
                send_race_call_email(call_record)

    # 1. Statewide Races
    for r_id, r_obj in data.get('statewide', {}).items():
        evaluate_contest(r_id, r_obj, 'North Carolina Statewide Marquee')

    # 2. NC Senate Districts
    for r_id, r_obj in data.get('chambers', {}).get('senate', {}).get('districts', {}).items():
        evaluate_contest(r_id, r_obj, 'NC State Senate')

    # 3. NC House Districts
    for r_id, r_obj in data.get('chambers', {}).get('house', {}).get('districts', {}).items():
        evaluate_contest(r_id, r_obj, 'NC House of Representatives')

    # 4. US House Districts
    for r_id, r_obj in data.get('chambers', {}).get('congress', {}).get('districts', {}).items():
        evaluate_contest(r_id, r_obj, 'US House of Representatives')

    if new_calls and not dry_run:
        save_called_races(called_races)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Saved {len(new_calls)} new call(s) to {CALLED_RACES_PATH}.")

    return new_calls, called_races

# ==============================================================================
# SIMULATION GENERATOR FOR TESTING
# ==============================================================================
def generate_simulation_returns(stage='eday50'):
    """Simulates returns matching needle/index.html applySimScenario."""
    data = load_needle_dataset()
    all_races = {}
    all_races.update(data.get('statewide', {}))
    all_races.update(data.get('chambers', {}).get('senate', {}).get('districts', {}))
    all_races.update(data.get('chambers', {}).get('house', {}).get('districts', {}))
    all_races.update(data.get('chambers', {}).get('congress', {}).get('districts', {}))

    sim_returns = {}

    for r_id, r in all_races.items():
        sim_returns[r_id] = {}
        units = r.get('counties', []) if (r.get('counties') and not r.get('precincts')) else r.get('precincts', [])

        for idx, u in enumerate(units):
            u_id = u.get('id') or u.get('county')
            if stage in ('0', 0):
                sim_returns[r_id][u_id] = {'reported': False}
                continue

            modes = u.get('modes', {})
            base_noise = math.sin((r.get('number', 3)) * 0.5 + idx * 0.2) * 1.8

            def make_mode(m_key):
                m = modes.get(m_key, {'proj': 100, 'bench_m': 0.0})
                m_noise = base_noise + math.sin(idx * 3 + (1 if m_key == 'mail' else 2 if m_key == 'early' else 3)) * 0.8
                actual_m = max(-100.0, min(100.0, m.get('bench_m', 0.0) + m_noise))
                tot = max(1, round(m.get('proj', 100) * (0.98 + math.cos(idx) * 0.04)))
                dem = round(tot * (100.0 + actual_m) / 200.0)
                rep = max(0, tot - dem)
                return {'dem': dem, 'rep': rep, 'tot': tot}

            mail = {'dem': 0, 'rep': 0, 'tot': 0}
            early = {'dem': 0, 'rep': 0, 'tot': 0}
            eday = {'dem': 0, 'rep': 0, 'tot': 0}

            if stage in ('25', 'mail'):
                mail = make_mode('mail')
            elif stage in ('50', 'early'):
                mail = make_mode('mail')
                early = make_mode('early')
            elif stage in ('75', 'eday50'):
                mail = make_mode('mail')
                early = make_mode('early')
                if ((idx * 37 + (r.get('number', 7)) * 19) % 100) < 50:
                    eday = make_mode('eday')
            elif stage in ('100', 'final'):
                mail = make_mode('mail')
                early = make_mode('early')
                eday = make_mode('eday')

            tot_votes = mail['tot'] + early['tot'] + eday['tot']
            dem_votes = mail['dem'] + early['dem'] + eday['dem']
            rep_votes = mail['rep'] + early['rep'] + eday['rep']

            sim_returns[r_id][u_id] = {
                'reported': tot_votes > 0,
                'demVotes': dem_votes,
                'repVotes': rep_votes,
                'totVotes': tot_votes,
                'mail': mail,
                'early': early,
                'eday': eday
            }

    return sim_returns

# ==============================================================================
# CLI COMMAND HANDLER
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Election Night Race Caller & Decision Desk")
    parser.add_argument('--check', action='store_true', help="Check current live returns for new calls")
    parser.add_argument('--simulate', choices=['0', 'mail', 'early', 'eday50', '100'], help="Run simulation stage and evaluate calls")
    parser.add_argument('--test-email', action='store_true', help="Send a test race call email to Rann")
    parser.add_argument('--reset', action='store_true', help="Reset called races ledger")
    parser.add_argument('--daemon', action='store_true', help="Run continuously in background")
    parser.add_argument('--interval', type=int, default=30, help="Daemon check interval in seconds (default: 30)")
    parser.add_argument('--dry-run', action='store_true', help="Evaluate without sending emails or updating files")

    args = parser.parse_args()

    if args.reset:
        if os.path.exists(CALLED_RACES_PATH):
            os.remove(CALLED_RACES_PATH)
            print(f"Removed {CALLED_RACES_PATH}")
        data = load_needle_dataset()
        data['called_races'] = {}
        with open(DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'))
        print("Reset called_races in needle_data.json.")
        return

    if args.test_email:
        test_call = {
            'race_id': 'US-SENATE',
            'race_name': 'US Senate',
            'chamber_label': 'North Carolina Statewide Marquee',
            'winner': 'Roy Cooper',
            'party': 'Democrat',
            'win_prob': 0.984,
            'win_prob_pct': '98.4',
            'confidence_str': '98.4% Confidence',
            'projected_margin': 3.42,
            'proj_margin_str': 'DEM +3.4%',
            'ci_str': '[+1.2%, +5.6%]',
            'reported_pct_str': '84.6%',
            'units_str': '100/100 Counties',
            'photo_url': 'https://rannbar-on.com/needle/candidates/roy_cooper.jpg',
            'called_at': datetime.now().strftime('%I:%M %p EST'),
            'called_at_iso': datetime.now().isoformat()
        }
        print("Dispatching test RACE CALL email to Rann...")
        success = send_race_call_email(test_call)
        if success:
            print("✓ Test RACE CALL email delivered successfully!")
        else:
            print("✗ Test email failed.")
        return

    if args.simulate:
        print(f"Generating simulated returns for stage '{args.simulate}'...")
        sim_returns = generate_simulation_returns(args.simulate)
        new_calls, all_calls = evaluate_all_races(live_returns=sim_returns, simulate_stage=args.simulate, dry_run=args.dry_run)
        print(f"Simulation completed. Total called races: {len(all_calls)} ({len(new_calls)} newly called).")
        return

    if args.daemon:
        print(f"Starting Decision Desk Daemon (interval: {args.interval}s)...")
        while True:
            try:
                new_calls, all_calls = evaluate_all_races(dry_run=args.dry_run)
                if new_calls:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(new_calls)} new race call(s) processed.")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Daemon error: {e}")
            time.sleep(args.interval)
        return

    # Default: single check pass
    new_calls, all_calls = evaluate_all_races(dry_run=args.dry_run)
    print(f"Check pass completed. Total called races: {len(all_calls)} ({len(new_calls)} new).")

if __name__ == '__main__':
    main()
