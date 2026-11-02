"""
North Carolina 2026 Early Vote & General Election Forecasting Model
===================================================================
Redesigned multi-factor voter transition, propensity, dual-regime prediction engine,
with statewide marquee races:
1. 2026 US Senate (Roy Cooper vs. Michael Whatley)
2. 2026 NC Supreme Court Seat 1 (Anita Earls vs. Sarah Stevens)
3. 2026 NC Court of Appeals Seat 1 (John S. Arrowood vs. Michael C. Byrne)
4. 2026 NC Court of Appeals Seat 2 (Tobias Hampson vs. George Cooper Bell)
5. 2026 NC Court of Appeals Seat 3 (Christine Marie Walczyk vs. Craig Collins)

Key Improvements:
1. Partisan Crossover Matrix:
   - Dynamic Dem Loyalty vs Defection (D -> R) accounting for rural ancestral Dem ticket splitting.
   - Dynamic Rep Loyalty vs Crossover (R -> D) accounting for suburban college-educated moderation.
   - Calibrated Unaffiliated (UNA) Democratic vote share by county urbanization/education tier.
2. Voter Propensity & Cannibalization Segmentation:
   - High-Propensity Cannibalization Discount: Discounts the historical Republican Election Day surge
     when Republicans bank high-propensity early votes.
   - Low-Propensity Expansion Premium: Rewards net electorate growth when young (<30) and newly
     registered Unaffiliated voters turn out in early voting.
3. Dual-Regime Empirical Bounds & Empirical Bayes Shrinkage:
   - Evaluates outcomes under 2018 (Dem momentum) and 2022 (Rep surge) macro environments.
   - Applies volume-weighted Empirical Bayes shrinkage toward statewide macro trends.
   - Provides day-decaying empirical uncertainty intervals and qualitative ratings.
4. Downballot Judicial Calibration:
   - Specific downballot roll-off attrition, judicial ticket-splitting, and incumbency adjustments
     for the Supreme Court and three Court of Appeals seats.
"""

import os
import json
import math
import numpy as np

DEFAULT_BASELINES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "county_vote_baselines.json")

def load_baselines(path=None):
    if path is None:
        path = DEFAULT_BASELINES_PATH
    if not os.path.exists(path):
        if os.path.exists("county_vote_baselines.json"):
            path = "county_vote_baselines.json"
        elif os.path.exists("remote_deployment/county_vote_baselines.json"):
            path = "remote_deployment/county_vote_baselines.json"
        elif os.path.exists("/home/rann/Documents/math/teaching/coursepack105L106L/county_vote_baselines.json"):
            path = "/home/rann/Documents/math/teaching/coursepack105L106L/county_vote_baselines.json"
        else:
            raise FileNotFoundError(f"County baselines JSON not found at {path}")
    
    with open(path, 'r') as f:
        return json.load(f)

HISTORICAL_SIGMA_BY_DAY = {
    1: 3.344, 2: 2.643, 3: 2.537, 4: 2.578, 5: 2.180,
    6: 1.856, 7: 1.636, 8: 1.535, 9: 1.401, 10: 1.395,
    11: 1.371, 12: 1.186, 13: 1.096, 14: 0.942, 15: 0.830,
    16: 0.683, 17: 0.658
}

def get_empirical_sigma(ev_day=None, default=2.578):
    if ev_day is None:
        return default
    try:
        d = int(ev_day)
        if d in HISTORICAL_SIGMA_BY_DAY:
            return HISTORICAL_SIGMA_BY_DAY[d]
        elif d > 17:
            return 0.658
        elif d < 1:
            return 3.344
    except (ValueError, TypeError):
        pass
    return default

# =============================================================================
# HISTORICAL EARLY VOTE VS. ELECTION DAY TURNOUT & PARTISAN DECOMPOSITION
# =============================================================================
HISTORICAL_EV_VS_EDAY = {
    # Midterms (Weighed heavily: 85% total weight)
    2022: {
        'type': 'midterm', 'weight': 0.40,
        'tot_votes': 3780000, 'ev_votes': 2150000, 'ev_share': 0.5688,
        'eday_votes': 1630000, 'eday_share': 0.4312,
        'dem_ev_share': 52.12, 'rep_ev_share': 47.88,
        'dem_eday_share': 41.82, 'rep_eday_share': 58.18,
        'dem_eday_penalty': 10.30
    },
    2018: {
        'type': 'midterm', 'weight': 0.30,
        'tot_votes': 3755000, 'ev_votes': 2020000, 'ev_share': 0.5380,
        'eday_votes': 1735000, 'eday_share': 0.4620,
        'dem_ev_share': 53.05, 'rep_ev_share': 46.95,
        'dem_eday_share': 43.55, 'rep_eday_share': 56.45,
        'dem_eday_penalty': 9.50
    },
    2014: {
        'type': 'midterm', 'weight': 0.15,
        'tot_votes': 2940000, 'ev_votes': 1165000, 'ev_share': 0.3963,
        'eday_votes': 1775000, 'eday_share': 0.6037,
        'dem_ev_share': 51.75, 'rep_ev_share': 48.25,
        'dem_eday_share': 42.75, 'rep_eday_share': 57.25,
        'dem_eday_penalty': 9.00
    },
    # Presidential cycles (Total 15% weight)
    2024: {
        'type': 'presidential', 'weight': 0.08,
        'tot_votes': 5700000, 'ev_votes': 4500000, 'ev_share': 0.7895,
        'eday_votes': 1200000, 'eday_share': 0.2105,
        'dem_ev_share': 50.20, 'rep_ev_share': 49.80,
        'dem_eday_share': 33.50, 'rep_eday_share': 66.50,
        'dem_eday_penalty': 16.70
    },
    2020: {
        'type': 'presidential', 'weight': 0.04,
        'tot_votes': 5545000, 'ev_votes': 4545000, 'ev_share': 0.8197,
        'eday_votes': 1000000, 'eday_share': 0.1803,
        'dem_ev_share': 53.25, 'rep_ev_share': 46.75,
        'dem_eday_share': 36.05, 'rep_eday_share': 63.95,
        'dem_eday_penalty': 17.20
    },
    2016: {
        'type': 'presidential', 'weight': 0.02,
        'tot_votes': 4740000, 'ev_votes': 3130000, 'ev_share': 0.6603,
        'eday_votes': 1610000, 'eday_share': 0.3397,
        'dem_ev_share': 52.80, 'rep_ev_share': 47.20,
        'dem_eday_share': 44.90, 'rep_eday_share': 55.10,
        'dem_eday_penalty': 7.90
    },
    2012: {
        'type': 'presidential', 'weight': 0.01,
        'tot_votes': 4505000, 'ev_votes': 2750000, 'ev_share': 0.6104,
        'eday_votes': 1755000, 'eday_share': 0.3896,
        'dem_ev_share': 52.40, 'rep_ev_share': 47.60,
        'dem_eday_share': 44.50, 'rep_eday_share': 55.50,
        'dem_eday_penalty': 7.90
    }
}

WEIGHTED_HISTORICAL_EDAY_PENALTY_ALL = sum(
    d['weight'] * d['dem_eday_penalty'] for d in HISTORICAL_EV_VS_EDAY.values()
) / sum(d['weight'] for d in HISTORICAL_EV_VS_EDAY.values()) # ~10.58 pp

WEIGHTED_HISTORICAL_EDAY_PENALTY_MIDTERM = sum(
    d['weight'] * d['dem_eday_penalty'] for d in HISTORICAL_EV_VS_EDAY.values() if d['type'] == 'midterm'
) / sum(d['weight'] for d in HISTORICAL_EV_VS_EDAY.values() if d['type'] == 'midterm') # ~9.79 pp

def load_precinct_historical_modes(path=None):
    if path is None:
        path = "nc_precinct_historical_modes.json"
    for cand in [
        path,
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "nc_precinct_historical_modes.json"),
        "/home/rann/Documents/math/teaching/coursepack105L106L/nc_precinct_historical_modes.json",
        "/home/rann/src/website/mainwebsite/nc_precinct_historical_modes.json",
        "/home/rann/src/elections/2026 analysis/nc_precinct_historical_modes.json"
    ]:
        if os.path.exists(cand):
            try:
                with open(cand, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
    return {}

def compute_eday_adjusted_forecast(c_key, ev_dem_share, ev_tot_votes, b, trans, rc, ev_day=None, pct_r26=26.2, pct_r22=31.5, delta_u=0.0):
    """
    Two-mode (Early Vote + Election Day) decomposition engine:
    1. Total Electorate Projection:
       - Projects total county turnout V_tot = max(V_ev * 1.05, b['votes_2022'] * 1.02 * (1 - roll_off)).
       - Derives expected Election Day volume V_eday = max(0, V_tot - V_ev) and fraction f_eday = V_eday / V_tot.
    2. Weighted Historical Democratic Penalty:
       - Synthesizes all past NC general elections, weighing midterms heavily (85% weight) -> ~10.58 pp statewide penalty.
    3. County-Specific Partisan Calibration:
       - Inverts b['shift_2022'] against 2022 E-day share (0.4312) to obtain county-specific historical penalty.
       - Calibrated by partisan geography: rural GOP strongholds higher (12-15 pp), urban centers lower (4-7 pp).
    4. GOP Reservoir / Cannibalization Dynamics:
       - If Republicans banked fewer EV votes than normal (GOP share 26.2% vs 31.5% in 2022), larger E-day reservoir strengthens surge.
       - If Republicans banked high EV share, cannibalizes E-day pool (down to 0.75 discount).
       - Unaffiliated low-propensity expansion premium.
    5. Two-Mode Blended Vote Share:
       - S_final = (1 - f_eday) * S_ev + f_eday * S_eday = S_ev - f_eday * Delta_eday_adj.
    """
    ev_dem_share = float(ev_dem_share)
    ev_tot_votes = float(ev_tot_votes)
    roll_off = rc.get('roll_off', 0.0) if rc else 0.0

    # 1. Total Electorate Projection
    v_base_2022 = float(b.get('votes_2022', 0.0)) * (1.0 - roll_off)
    # Registration growth in NC midterms: ~3.5% over 2022
    # At county level, account for early vote expansion while respecting historical base
    v_tot_proj = max(ev_tot_votes * 1.05, v_base_2022 * 1.02)
    v_eday_proj = max(0.0, v_tot_proj - ev_tot_votes)
    f_eday = (v_eday_proj / v_tot_proj) if v_tot_proj > 0 else 0.4312
    # Realistic bounds on Election Day turnout share
    f_eday = max(0.12, min(0.65, f_eday))

    # 2. Weighted Historical E-Day Penalty (85% midterm / 15% presidential)
    weighted_penalty = WEIGHTED_HISTORICAL_EDAY_PENALTY_ALL # ~10.58 pp

    # 3. County-Specific Partisan Calibration
    # In 2022, statewide E-Day share was 0.4312.
    # County implied 2022 penalty = -b['shift_2022'] / 0.4312
    shift_2022 = float(b.get('shift_2022', -5.0))
    implied_penalty_2022 = -shift_2022 / 0.4312

    # Tier-based calibration for geographic realism (urban 4-7 pp, rural 12-15 pp)
    tier = trans.get('tier', 'tier_2_suburban')
    if tier == 'tier_1_urban':
        tier_target = 6.2
    elif tier == 'tier_3_rural':
        tier_target = 13.8
    else: # tier_2_suburban
        tier_target = 9.8

    # Blend county empirical 2022 implied penalty with weighted historical and tier targets
    base_county_penalty = 0.55 * implied_penalty_2022 + 0.25 * weighted_penalty + 0.20 * tier_target
    base_county_penalty = max(3.5, min(17.5, base_county_penalty))

    # 4. GOP Reservoir / Cannibalization Adjustment
    delta_r = float(pct_r26) - float(pct_r22)
    delta_u = float(delta_u)

    if delta_r < 0.0:
        # Republicans banked fewer votes in early voting -> Election Day reservoir is larger, strengthening E-Day surge
        reservoir_factor = 1.0 + 0.25 * min(1.0, max(0.0, -delta_r / 6.0))
        cannibalization = 1.0
    else:
        # High-propensity Republican cannibalization discount
        cannibalization = max(0.75, min(1.0, 1.0 - 0.25 * max(0.0, delta_r / 5.0)))
        reservoir_factor = cannibalization

    # Low-propensity Unaffiliated/young expansion premium
    una_pref = trans.get('una_dem_share', 0.50)
    expansion = max(-1.5, min(2.5, (delta_u / 100.0) * (una_pref - 0.50) * 15.0))

    # Race-specific shift offset (e.g. -1.45 pp for Supreme Court, -1.85 pp for CoA 1)
    race_shift = rc.get('shift_offset', 0.0) if rc else 0.0

    # Adjusted Election Day penalty
    eday_penalty_adj = base_county_penalty * reservoir_factor - expansion

    # 5. Two-Mode Blended Vote Share
    # S_final = (1 - f_eday) * S_ev + f_eday * S_eday + race_shift
    # Where S_eday = S_ev - eday_penalty_adj
    est_eday_dem = max(0.0, min(100.0, ev_dem_share - eday_penalty_adj))
    raw_final_dem = (1.0 - f_eday) * ev_dem_share + f_eday * est_eday_dem + race_shift
    raw_final_dem = max(0.0, min(100.0, raw_final_dem))

    # Effective shift from EV Democratic share to final
    adj_shift = raw_final_dem - ev_dem_share

    return {
        'raw_final_dem': raw_final_dem,
        'est_ev_dem': ev_dem_share,
        'est_eday_dem': est_eday_dem,
        'f_eday': f_eday,
        'v_tot_proj': v_tot_proj,
        'v_eday_proj': v_eday_proj,
        'eday_penalty': eday_penalty_adj,
        'base_penalty': base_county_penalty,
        'reservoir_factor': reservoir_factor,
        'cannibalization': cannibalization,
        'expansion': expansion,
        'adj_shift': adj_shift
    }

# =============================================================================
# STATEWIDE RACES CONFIGURATION
# =============================================================================
RACES_CONFIG = {
    'us_senate': {
        'id': 'us_senate',
        'key': 'US-SENATE',
        'name': 'US Senate',
        'full_title': '2026 US Senate: Roy Cooper (D) vs. Michael Whatley (R)',
        'dem_candidate': 'Roy Cooper',
        'rep_candidate': 'Michael Whatley',
        'incumbent': 'D',
        'category': 'federal',
        'shift_offset': 0.0,
        'una_offset': 0.0,
        'roll_off': 0.0,
        'rural_defection_adj': 0.0,
        'suburban_crossover_adj': 0.0,
        'historical_diff_2022': 0.0,
    },
    'supreme_court': {
        'id': 'supreme_court',
        'key': 'NC-SC',
        'name': 'NC Supreme Court',
        'full_title': '2026 NC Supreme Court: Anita Earls (D - Incumbent) vs. Sarah Stevens (R)',
        'dem_candidate': 'Anita Earls',
        'rep_candidate': 'Sarah Stevens',
        'incumbent': 'D',
        'category': 'judicial',
        'shift_offset': -1.45,
        'una_offset': -0.025,
        'roll_off': 0.042,
        'rural_defection_adj': 0.035,
        'suburban_crossover_adj': 0.010,
        'historical_diff_2022': -1.82,
    },
    'coa_1': {
        'id': 'coa_1',
        'key': 'NC-COA-1',
        'name': 'Court of Appeals (Seat 1)',
        'full_title': '2026 NC Court of Appeals Seat 1: John S. Arrowood (D - Incumbent) vs. Michael C. Byrne (R)',
        'dem_candidate': 'John S. Arrowood',
        'rep_candidate': 'Michael C. Byrne',
        'incumbent': 'D',
        'category': 'judicial',
        'shift_offset': -1.85,
        'una_offset': -0.035,
        'roll_off': 0.055,
        'rural_defection_adj': 0.040,
        'suburban_crossover_adj': 0.005,
        'historical_diff_2022': -2.15,
    },
    'coa_2': {
        'id': 'coa_2',
        'key': 'NC-COA-2',
        'name': 'Court of Appeals (Seat 2)',
        'full_title': '2026 NC Court of Appeals Seat 2: Tobias Hampson (D - Incumbent) vs. George Cooper Bell (R)',
        'dem_candidate': 'Tobias (Toby) Hampson',
        'rep_candidate': 'George Cooper Bell',
        'incumbent': 'D',
        'category': 'judicial',
        'shift_offset': -1.80,
        'una_offset': -0.035,
        'roll_off': 0.058,
        'rural_defection_adj': 0.038,
        'suburban_crossover_adj': 0.005,
        'historical_diff_2022': -2.10,
    },
    'coa_3': {
        'id': 'coa_3',
        'key': 'NC-COA-3',
        'name': 'Court of Appeals (Seat 3)',
        'full_title': '2026 NC Court of Appeals Seat 3: Christine Marie Walczyk (D) vs. Craig Collins (R)',
        'dem_candidate': 'Christine Marie Walczyk',
        'rep_candidate': 'Craig Collins',
        'incumbent': 'None',
        'category': 'judicial',
        'shift_offset': -2.10,
        'una_offset': -0.040,
        'roll_off': 0.062,
        'rural_defection_adj': 0.045,
        'suburban_crossover_adj': 0.000,
        'historical_diff_2022': -2.35,
    }
}

# =============================================================================
# PUBLIC POLLING & CORRELATION INTEGRATION CONFIGURATION
# =============================================================================
POLLSTER_RATINGS = {
    'YouGov': 2.8,
    'East Carolina University': 2.5,
    'ECU': 2.5,
    'Elon University': 2.4,
    'High Point University': 2.3,
    'Quantus Insights': 1.8,
    'SurveyUSA': 2.6,
    'Emerson College': 2.6,
    'Meredith College': 2.1,
    'Generic/Other': 1.5
}

# Empirical 2026 North Carolina Final Polling Dataset
RECENT_POLLS = [
    # 1. US Senate (Roy Cooper [D] vs. Michael Whatley [R])
    {
        'race': 'us_senate',
        'pollster': 'East Carolina University',
        'partner': 'ECU Center for Survey Research',
        'date_end': '2026-11-01',
        'sample_size': 1050,
        'dem': 54.0,
        'rep': 45.0,
        'undecided': 1.0,
        'method': 'Likely Voters (Live Phone + Online Panel)'
    },
    {
        'race': 'us_senate',
        'pollster': 'YouGov',
        'partner': 'High Point University',
        'date_end': '2026-10-28',
        'sample_size': 1120,
        'dem': 55.0,
        'rep': 44.0,
        'undecided': 1.0,
        'method': 'Likely Voters (YouGov Online Matched Sample)'
    },
    {
        'race': 'us_senate',
        'pollster': 'Quantus Insights',
        'partner': 'Quantus Polling',
        'date_end': '2026-10-27',
        'sample_size': 830,
        'dem': 51.4,
        'rep': 42.8,
        'undecided': 5.8,
        'method': 'Likely Voters (IVR + Online)'
    },
    {
        'race': 'us_senate',
        'pollster': 'Elon University',
        'partner': 'Elon Poll',
        'date_end': '2026-10-15',
        'sample_size': 950,
        'dem': 52.0,
        'rep': 39.0,
        'undecided': 9.0,
        'method': 'Likely Voters (Live Interview / Dual Frame)'
    },
    # 2. NC Supreme Court Seat 1 (Anita Earls [D] vs. Sarah Stevens [R])
    {
        'race': 'supreme_court',
        'pollster': 'YouGov',
        'partner': 'High Point University',
        'date_end': '2026-10-28',
        'sample_size': 1080,
        'dem': 51.0,
        'rep': 43.0,
        'undecided': 6.0,
        'method': 'Likely Voters (Online Matched Panel)'
    }
]

# Cross-Race Correlation & Downballot Roll-off Structure
CROSS_RACE_CORRELATION = {
    'us_senate': {'direct_poll': True},
    'supreme_court': {'direct_poll': True},
    'coa_1': {
        'direct_poll': False,
        'correlations': {'supreme_court': 0.91, 'us_senate': 0.81},
        'offset_vs_sc': -2.80, # Downballot roll-off & generic Dem judicial drag vs Earls
        'offset_vs_senate': -4.50 # Offset vs Cooper top-of-ticket
    },
    'coa_2': {
        'direct_poll': False,
        'correlations': {'supreme_court': 0.91, 'us_senate': 0.81},
        'offset_vs_sc': -2.60, # Incumbent Hampson runs slightly ahead of generic downballot
        'offset_vs_senate': -4.30
    },
    'coa_3': {
        'direct_poll': False,
        'correlations': {'supreme_court': 0.90, 'us_senate': 0.80},
        'offset_vs_sc': -3.40, # Open seat, running slightly behind incumbents
        'offset_vs_senate': -5.10
    },
    'amendment_photo_id': {
        'direct_poll': True,
        'poll_dem': 41.80, # Against / No
        'poll_rep': 58.20, # For / Yes (Passes)
        'sigma': 2.30
    },
    'amendment_tax_cap': {
        'direct_poll': True,
        'poll_dem': 46.20, # Against / No
        'poll_rep': 53.80, # For / Yes (Passes)
        'sigma': 2.50
    },
    'amendment_property_tax': {
        'direct_poll': True,
        'poll_dem': 51.60, # Against / No (Dem-aligned rejection)
        'poll_rep': 48.40, # For / Yes (Fails)
        'sigma': 2.80
    }
}


def get_poll_estimate(race_key: str, election_day_str: str = '2026-11-03') -> dict:
    """
    Computes quality-weighted, recency-decayed polling estimates for a given contest.
    For contests without direct polling (e.g. Court of Appeals seats), applies
    a cross-race correlation matrix and roll-off offsets to top-of-ticket and Supreme Court polls.
    """
    from datetime import date
    cfg = CROSS_RACE_CORRELATION.get(race_key, {})
    ed = date.fromisoformat(election_day_str)

    if cfg.get('direct_poll'):
        if 'poll_dem' in cfg:
            return {
                'mean': cfg['poll_dem'],
                'sigma': cfg['sigma'],
                'n_polls': 1,
                'is_synthetic': False,
                'weight': 3.5,
                'polls': [{'pollster': 'Statewide Public Opinion Consensus', 'dem': cfg['poll_dem'], 'rep': cfg['poll_rep']}]
            }
        polls = [p for p in RECENT_POLLS if p['race'] == race_key]
        if not polls:
            return None
        tot_w = 0.0
        w_sum = 0.0
        poll_details = []
        for p in polls:
            dt = date.fromisoformat(p['date_end'])
            days_ago = max(0, (ed - dt).days)
            # 14-day exponential half-life for recency decay
            w_rec = math.exp(-0.0495 * days_ago)
            w_rat = POLLSTER_RATINGS.get(p['pollster'], 1.5)
            w_n = math.sqrt(p['sample_size'] / 600.0)
            w = w_rat * w_rec * w_n
            # Two-way vote share
            dem_2way = (p['dem'] / (p['dem'] + p['rep'])) * 100.0
            tot_w += w
            w_sum += w * dem_2way
            poll_details.append({
                'pollster': p['pollster'],
                'partner': p.get('partner', ''),
                'date_end': p['date_end'],
                'dem_raw': p['dem'],
                'rep_raw': p['rep'],
                'dem_twoway': round(dem_2way, 2),
                'weight': round(w, 2),
                'quality_grade': w_rat,
                'days_ago': days_ago
            })
        mean_p = w_sum / tot_w if tot_w > 0 else 50.0
        sigma_p = 2.4 / math.sqrt(max(1.0, tot_w / 3.0))
        return {
            'mean': round(mean_p, 2),
            'sigma': round(sigma_p, 2),
            'n_polls': len(polls),
            'is_synthetic': False,
            'weight': round(tot_w, 2),
            'polls': poll_details
        }
    else:
        # Cross-race correlation synthesis for unpolled judicial seats
        sc_est = get_poll_estimate('supreme_court', election_day_str)
        sen_est = get_poll_estimate('us_senate', election_day_str)
        corrs = cfg.get('correlations', {})
        w_sc = corrs.get('supreme_court', 0.91)
        w_sen = corrs.get('us_senate', 0.81)

        val_from_sc = sc_est['mean'] + cfg.get('offset_vs_sc', 0.0)
        val_from_sen = sen_est['mean'] + cfg.get('offset_vs_senate', 0.0)
        synth_mean = (w_sc * val_from_sc + w_sen * val_from_sen) / (w_sc + w_sen)
        synth_sigma = math.sqrt(((w_sc * sc_est['sigma'])**2 + (w_sen * sen_est['sigma'])**2) / (w_sc + w_sen)**2 + 0.65**2)

        return {
            'mean': round(synth_mean, 2),
            'sigma': round(synth_sigma, 2),
            'n_polls': 0,
            'is_synthetic': True,
            'weight': round((sc_est['weight'] + sen_est['weight']) * 0.45, 2),
            'correlations': corrs,
            'polls': []
        }

# =============================================================================
# CONSTITUTIONAL AMENDMENTS CONFIGURATION (2026 GENERAL ELECTION)
# =============================================================================
AMENDMENTS_CONFIG = {
    'amendment_photo_id': {
        'id': 'amendment_photo_id',
        'key': 'NC-CONST-AMEND-1',
        'name': 'Require Photo ID for All Voters Amendment',
        'short_name': 'Photo ID for All Voters',
        'full_title': 'Constitutional Amendment to Require Photographic Identification for All Voters',
        'ballot_question': 'Constitutional requirement for photo ID across all voting methods, including in-person and mail-in/absentee ballots.',
        'dem_stance': 'Against (No)',
        'rep_stance': 'For (Yes)',
        'dem_candidate': 'Against / No (Dem-aligned)',
        'rep_candidate': 'For / Yes (GOP-aligned)',
        'incumbent': '2018 Statutory Expansion',
        'category': 'amendment',
        'pred_final_dem': 43.15,
        'pred_final_rep': 56.85,
        'pred_dem_share': 43.15,
        'pred_rep_share': 56.85,
        'pred_margin': -13.70,
        'range_low': 40.80,
        'range_high': 45.50,
        'ci_95_low': 39.80,
        'ci_95_high': 46.50,
        'moe_95': 3.35,
        'margin_low': -18.40,
        'margin_high': -9.00,
        'actual_2022': 44.50,
        'swing_vs_2022': -1.35,
        'p_dem': 0.1,
        'p_rep': 99.9,
        'rating': 'Likely For (Passes)',
        'call_confidence': 'very high confidence',
        'margin_confidence': 'high confidence',
        'ci_margin_low': -20.40,
        'ci_margin_high': -7.00
    },
    'amendment_tax_cap': {
        'id': 'amendment_tax_cap',
        'key': 'NC-CONST-AMEND-2',
        'name': '3.5% Income Tax Cap Amendment',
        'short_name': '3.5% Income Tax Cap',
        'full_title': 'Constitutional Amendment to Lower Maximum Income Tax Rate to 3.5%',
        'ballot_question': 'Reduces the constitutional ceiling on maximum personal and corporate state income tax rate from 7.0% to 3.5%.',
        'dem_stance': 'Against (No)',
        'rep_stance': 'For (Yes)',
        'dem_candidate': 'Against / No (Dem-aligned)',
        'rep_candidate': 'For / Yes (GOP-aligned)',
        'incumbent': 'Replaces 7% 2018 Cap',
        'category': 'amendment',
        'pred_final_dem': 46.55,
        'pred_final_rep': 53.45,
        'pred_dem_share': 46.55,
        'pred_rep_share': 53.45,
        'pred_margin': -6.90,
        'range_low': 43.80,
        'range_high': 49.30,
        'ci_95_low': 43.05,
        'ci_95_high': 50.05,
        'moe_95': 3.50,
        'margin_low': -12.40,
        'margin_high': -1.40,
        'actual_2022': 42.60,
        'swing_vs_2022': 3.95,
        'p_dem': 5.2,
        'p_rep': 94.8,
        'rating': 'Lean For (Passes)',
        'call_confidence': 'high confidence',
        'margin_confidence': 'high confidence',
        'ci_margin_low': -13.90,
        'ci_margin_high': 0.10
    },
    'amendment_property_tax': {
        'id': 'amendment_property_tax',
        'key': 'NC-CONST-AMEND-3',
        'name': 'Property Tax Levy Limit Amendment',
        'short_name': 'Property Tax Levy Cap',
        'full_title': 'Constitutional Amendment Requiring Limits on Local Government Property Tax Increases',
        'ballot_question': 'Requires General Assembly to impose statutory restrictions and caps on local government property tax increases.',
        'dem_stance': 'Against (No)',
        'rep_stance': 'For (Yes)',
        'dem_candidate': 'Against / No (Dem-aligned)',
        'rep_candidate': 'For / Yes (GOP-aligned)',
        'incumbent': 'New Constitutional Restriction',
        'category': 'amendment',
        'pred_final_dem': 51.45,
        'pred_final_rep': 48.55,
        'pred_dem_share': 51.45,
        'pred_rep_share': 48.55,
        'pred_margin': 2.90,
        'range_low': 48.50,
        'range_high': 54.40,
        'ci_95_low': 47.95,
        'ci_95_high': 54.95,
        'moe_95': 3.50,
        'margin_low': -3.00,
        'margin_high': 8.80,
        'actual_2022': 48.00,
        'swing_vs_2022': 3.45,
        'p_dem': 68.4,
        'p_rep': 31.6,
        'rating': 'Toss Up / Lean Against',
        'call_confidence': 'moderate confidence',
        'margin_confidence': 'moderate confidence',
        'ci_margin_low': -4.10,
        'ci_margin_high': 9.90
    }
}

# =============================================================================
# COUNTY POLITICAL GEOGRAPHY CLASSIFICATION
# =============================================================================
URBAN_COUNTIES = {'WAKE', 'MECKLENBURG', 'DURHAM', 'ORANGE', 'BUNCOMBE', 'GUILFORD', 'FORSYTH'}

SUBURBAN_GROWTH_COUNTIES = {
    'CABARRUS', 'UNION', 'NEW HANOVER', 'CHATHAM', 'JOHNSTON', 'ALAMANCE',
    'IREDELL', 'MOORE', 'HENDERSON', 'PITT', 'WATAUGA', 'BRUNSWICK',
    'FRANKLIN', 'HARNETT', 'CATAWBA', 'ROWAN', 'GASTON', 'CLEVELAND',
    'CUMBERLAND', 'NASH', 'WILSON', 'LEE'
}

ANCESTRAL_RURAL_DEM_COUNTIES = {
    'ROBESON', 'SCOTLAND', 'COLUMBUS', 'BLADEN', 'RICHMOND', 'BERTIE',
    'MARTIN', 'HERTFORD', 'NORTHAMPTON', 'WASHINGTON', 'EDGECOMBE',
    'HALIFAX', 'VANCE', 'WARREN', 'ANSON', 'GATES', 'GREENE', 'LENOIR',
    'TYRRELL', 'HYDE', 'CHOWAN', 'PASQUOTANK', 'PERQUIMANS', 'BEAUFORT'
}

def get_voter_transition_matrix(county_name: str, race_key: str = 'us_senate') -> dict:
    """
    Returns demographic and political transition matrix parameters for a county:
    - dem_loyalty: P(Dem vote | Reg Dem)
    - dem_defection_to_rep: P(Rep vote | Reg Dem)
    - rep_crossover_to_dem: P(Dem vote | Reg Rep)
    - una_dem_share: P(Dem vote | Unaffiliated)
    Calibrated per county typology and downballot contest characteristics.
    """
    c = str(county_name).upper().strip()
    rc = RACES_CONFIG.get(race_key, RACES_CONFIG['us_senate'])

    if c in URBAN_COUNTIES:
        loyalty = 0.955
        defection = 0.045
        crossover = 0.125 + rc.get('suburban_crossover_adj', 0.0)
        una = 0.640 + rc.get('una_offset', 0.0)
        tier = 'Urban Core / High Education'
        prop_wt = 1.15
    elif c in SUBURBAN_GROWTH_COUNTIES:
        loyalty = 0.930
        defection = 0.070
        crossover = 0.095 + rc.get('suburban_crossover_adj', 0.0)
        una = 0.545 + rc.get('una_offset', 0.0)
        tier = 'Suburban Growth / Swing'
        prop_wt = 1.05
    elif c in ANCESTRAL_RURAL_DEM_COUNTIES:
        defection = min(0.35, 0.185 + rc.get('rural_defection_adj', 0.0))
        loyalty = 1.0 - defection
        crossover = 0.040
        una = 0.385 + rc.get('una_offset', 0.0)
        tier = 'Rural Ancestral Democratic'
        prop_wt = 0.90
    else:  # Rural Traditional Republican
        defection = 0.115 + (rc.get('rural_defection_adj', 0.0) * 0.5)
        loyalty = 1.0 - defection
        crossover = 0.050
        una = 0.405 + rc.get('una_offset', 0.0)
        tier = 'Rural Traditional Republican'
        prop_wt = 0.95

    return {
        'dem_loyalty': round(loyalty, 4),
        'dem_defection_to_rep': round(defection, 4),
        'rep_crossover_to_dem': round(crossover, 4),
        'una_dem_share': round(una, 4),
        'tier': tier,
        'propensity_weight': prop_wt,
        'race_key': race_key,
        'race_name': rc['name'],
        'race_full_title': rc['full_title'],
        'dem_candidate': rc['dem_candidate'],
        'rep_candidate': rc['rep_candidate']
    }


def compute_win_probability_and_rating(mu, range_low, range_high, actual_2022=None, sigma_floor=None, ev_day=None):
    """
    Computes win probability P(Dem), P(Rep), flip probability, 95% confidence intervals, and qualitative rating.
    """
    if sigma_floor is None:
        sigma_floor = get_empirical_sigma(ev_day, default=2.578)

    width = max(0.1, range_high - range_low)
    sigma = max(sigma_floor, width / 3.92)
    z = (mu - 50.0) / sigma
    p_dem = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    p_dem = max(0.0, min(1.0, p_dem))
    p_rep = 1.0 - p_dem

    ci_low = max(0.0, min(100.0, mu - 1.96 * sigma))
    ci_high = max(0.0, min(100.0, mu + 1.96 * sigma))
    moe = 1.96 * sigma
    moe_margin = 2.0 * moe
    margin_w = 2.0 * moe_margin

    if margin_w < 8.0:
        margin_conf = 'very high confidence'
    elif margin_w < 15.0:
        margin_conf = 'high confidence'
    elif margin_w < 20.0:
        margin_conf = 'moderate confidence'
    elif margin_w < 30.0:
        margin_conf = 'low confidence'
    else:
        margin_conf = 'very low confidence'

    ratio = abs(mu - 50.0) / sigma if sigma > 0 else 999.0
    if ratio >= 2.0:
        call_conf = 'very high confidence'
    elif ratio >= 1.0:
        call_conf = 'high confidence'
    elif ratio >= 0.5:
        call_conf = 'moderate confidence'
    elif ratio >= 0.2:
        call_conf = 'low confidence'
    else:
        call_conf = 'very low confidence'

    if p_dem >= 0.95:
        rating = 'Safe D'
    elif p_dem >= 0.85:
        rating = 'Very Likely D'
    elif p_dem >= 0.75:
        rating = 'Likely D'
    elif p_dem >= 0.60:
        rating = 'Lean D'
    elif p_dem >= 0.40:
        rating = 'Toss Up'
    elif p_dem >= 0.25:
        rating = 'Lean R'
    elif p_dem >= 0.15:
        rating = 'Likely R'
    elif p_dem >= 0.05:
        rating = 'Very Likely R'
    else:
        rating = 'Safe R'

    p_flip = None
    if actual_2022 is not None:
        winner_2022 = 'D' if actual_2022 > 50.0 else 'R'
        p_flip = p_rep if winner_2022 == 'D' else p_dem

    return {
        'p_dem': round(p_dem * 100.0, 1),
        'p_rep': round(p_rep * 100.0, 1),
        'p_flip': round(p_flip * 100.0, 1) if p_flip is not None else None,
        'rating': rating,
        'sigma': round(sigma, 2),
        'moe_95': round(moe, 2),
        'moe_margin': round(moe_margin, 2),
        'ci_95_low': round(ci_low, 2),
        'ci_95_high': round(ci_high, 2),
        'ci_margin_low': round(2.0 * ci_low - 100.0, 2),
        'ci_margin_high': round(2.0 * ci_high - 100.0, 2),
        'margin_width': round(margin_w, 2),
        'margin_confidence': margin_conf,
        'margin_precision': margin_conf,
        'call_confidence': call_conf,
        'call_ratio': round(ratio, 2)
    }


def predict_county(county_name, dem, rep, una, tot, baselines=None, ev_day=None, hist_2022=None, race_key='us_senate'):
    """
    Computes vote prediction for a single county incorporating:
    1. Partisan Crossover Matrix (D loyalty, R crossover, UNA preference).
    2. Propensity segmentation (cannibalization discount and low-propensity expansion).
    3. Dual-regime bounds (2018 Dem momentum vs 2022 Rep E-Day surge).
    4. Empirical Bayes shrinkage toward statewide macro distribution.
    5. Specific candidate and downballot race calibration (Supreme Court, CoA 1-3).
    """
    if baselines is None:
        baselines = load_baselines()

    c_key = str(county_name).upper().strip()
    if c_key not in baselines or tot <= 0:
        return None

    rc = RACES_CONFIG.get(race_key, RACES_CONFIG['us_senate'])
    b = baselines[c_key]
    trans = get_voter_transition_matrix(c_key, race_key=race_key)

    vd = float(dem)
    vr = float(rep)
    vu = float(una)
    tot_f = float(tot)

    # 1. Early Vote Estimate via Partisan Crossover Matrix
    ev_dem_v = (trans['dem_loyalty']) * vd + trans['rep_crossover_to_dem'] * vr + trans['una_dem_share'] * vu
    ev_rep_v = (trans['dem_defection_to_rep']) * vd + (1.0 - trans['rep_crossover_to_dem']) * vr + (1.0 - trans['una_dem_share']) * vu
    est_ev_dem = (ev_dem_v / (ev_dem_v + ev_rep_v)) * 100.0 if (ev_dem_v + ev_rep_v) > 0 else 50.0

    # 2. Propensity & Cannibalization Segmentation
    pct_u26 = (vu / tot_f) * 100.0
    pct_r26 = (vr / tot_f) * 100.0

    pct_u22 = 30.0
    pct_r22 = 31.5
    if hist_2022 and isinstance(hist_2022, dict):
        tot22 = float(hist_2022.get('tot', 0))
        if tot22 > 0:
            pct_u22 = (float(hist_2022.get('una', 0)) / tot22) * 100.0
            pct_r22 = (float(hist_2022.get('rep', 0)) / tot22) * 100.0

    delta_u = pct_u26 - pct_u22
    delta_r = pct_r26 - pct_r22

    # Two-Mode (Early Vote vs Election Day) Decomposition Engine
    eday_decomp = compute_eday_adjusted_forecast(
        c_key, est_ev_dem, tot_f, b, trans, rc, ev_day=ev_day,
        pct_r26=pct_r26, pct_r22=pct_r22, delta_u=delta_u
    )
    raw_final_dem = eday_decomp['raw_final_dem']
    cannibalization = eday_decomp['cannibalization']
    expansion = eday_decomp['expansion']
    adj_shift = eday_decomp['adj_shift']

    # Day-specific error terms
    err_18 = b['err_2018']
    err_22 = b['err_2022']
    sig_floor = None
    if ev_day is not None and 'by_day' in b:
        day_str = str(ev_day)
        if day_str in b['by_day']:
            err_18 = b['by_day'][day_str]['err_2018']
            err_22 = b['by_day'][day_str]['err_2022']
            rmse = math.sqrt((err_18**2 + err_22**2) / 2.0)
            spread = abs(err_18 - err_22)
            sig_floor = max(0.50, rmse, spread / 3.92)

    # 3. Dual-Regime Bounds (incorporating race shift)
    regime_18_dem = raw_final_dem - err_18
    regime_22_dem = raw_final_dem - err_22
    range_low = min(regime_18_dem, regime_22_dem)
    range_high = max(regime_18_dem, regime_22_dem)

    # 4. Empirical Bayes Shrinkage
    # Apply downballot roll-off to actual volume weight
    v_actual = b['votes_2022'] * (1.0 - rc.get('roll_off', 0.0))
    s = 30000.0 / (30000.0 + v_actual)
    shrunk_bias = (1.0 - s) * ((err_18 + err_22) / 2.0) + s * 0.17
    eb_final_dem = raw_final_dem - shrunk_bias

    # Clamp point estimate within dual-regime bounds
    eb_final_dem = max(range_low, min(range_high, eb_final_dem))
    eb_final_dem = max(0.0, min(100.0, eb_final_dem))
    range_low = max(0.0, min(100.0, range_low))
    range_high = max(0.0, min(100.0, range_high))

    eb_final_rep = 100.0 - eb_final_dem
    pred_margin = eb_final_dem - eb_final_rep
    margin_low = 2.0 * range_low - 100.0
    margin_high = 2.0 * range_high - 100.0

    actual_2022 = max(0.0, min(100.0, b['final_2022'] + rc.get('historical_diff_2022', 0.0)))
    swing = eb_final_dem - actual_2022

    prob_info = compute_win_probability_and_rating(
        eb_final_dem, range_low, range_high, actual_2022, sigma_floor=sig_floor, ev_day=ev_day
    )

    return {
        'pred_final_dem': round(eb_final_dem, 2),
        'pred_final_rep': round(eb_final_rep, 2),
        'pred_dem_share': round(eb_final_dem, 2),
        'pred_rep_share': round(eb_final_rep, 2),
        'pred_margin': round(pred_margin, 2),
        'range_low': round(range_low, 2),
        'range_high': round(range_high, 2),
        'margin_low': round(margin_low, 2),
        'margin_high': round(margin_high, 2),
        'raw_model_dem': round(raw_final_dem, 2),
        'actual_2022': round(actual_2022, 2),
        'swing_vs_2022': round(swing, 2),
        'regime_2022_dem': round(regime_22_dem, 2),
        'regime_2018_dem': round(regime_18_dem, 2),
        'pred_dem_regime22': round(regime_22_dem, 2),
        'pred_dem_regime18': round(regime_18_dem, 2),
        'p_dem': prob_info['p_dem'],
        'p_rep': prob_info['p_rep'],
        'p_flip': prob_info['p_flip'],
        'rating': prob_info['rating'],
        'sigma': prob_info['sigma'],
        'moe_95': prob_info['moe_95'],
        'moe_margin': prob_info['moe_margin'],
        'ci_95_low': prob_info['ci_95_low'],
        'ci_95_high': prob_info['ci_95_high'],
        'ci_margin_low': prob_info['ci_margin_low'],
        'ci_margin_high': prob_info['ci_margin_high'],
        'margin_width': prob_info['margin_width'],
        'margin_confidence': prob_info['margin_confidence'],
        'margin_precision': prob_info['margin_precision'],
        'call_confidence': prob_info['call_confidence'],
        'call_ratio': prob_info['call_ratio'],
        'turnout_volume_weight': round(v_actual, 1),
        # Race Metadata
        'race_key': race_key,
        'race_id': rc['id'],
        'race_name': rc['name'],
        'race_full_title': rc['full_title'],
        'dem_candidate': rc['dem_candidate'],
        'rep_candidate': rc['rep_candidate'],
        'incumbent': rc['incumbent'],
        'roll_off_rate': round(rc.get('roll_off', 0.0) * 100.0, 1),
        # Analytical Diagnostics & Two-Mode Decomposition
        'tier': trans['tier'],
        'crossover_r_to_d': round(trans['rep_crossover_to_dem'] * 100.0, 1),
        'defection_d_to_r': round(trans['dem_defection_to_rep'] * 100.0, 1),
        'una_dem_share': round(trans['una_dem_share'] * 100.0, 1),
        'propensity_cannibalization_factor': round(cannibalization, 3),
        'propensity_expansion_premium': round(expansion, 2),
        'est_ev_dem': round(eday_decomp['est_ev_dem'], 2),
        'est_eday_dem': round(eday_decomp['est_eday_dem'], 2),
        'f_eday': round(eday_decomp['f_eday'], 4),
        'eday_penalty': round(eday_decomp['eday_penalty'], 2),
        'v_tot_proj': round(eday_decomp['v_tot_proj'], 1),
        'v_eday_proj': round(eday_decomp['v_eday_proj'], 1),
        'gop_reservoir_factor': round(eday_decomp['reservoir_factor'], 3)
    }


def predict_county_all_races(county_name, dem, rep, una, tot, baselines=None, ev_day=None, hist_2022=None):
    """
    Computes forecasts for all configured statewide races for a single county.
    Top-level dict fields correspond to US Senate for backward compatibility,
    with an attached 'races' dictionary containing all 5 individual races.
    """
    primary = predict_county(county_name, dem, rep, una, tot, baselines=baselines, ev_day=ev_day, hist_2022=hist_2022, race_key='us_senate')
    if primary is None:
        return None

    races = {}
    for rk in RACES_CONFIG:
        if rk == 'us_senate':
            races[rk] = dict(primary)
        else:
            races[rk] = predict_county(county_name, dem, rep, una, tot, baselines=baselines, ev_day=ev_day, hist_2022=hist_2022, race_key=rk)

    res = dict(primary)
    res['races'] = races
    return res


def predict_all(county_returns, baselines=None, ev_day=None):
    """
    Computes county-level predictions and volume-weighted statewide rollups
    across all 5 statewide contests (US Senate, Supreme Court, CoA 1-3).
    Top-level fields remain backwards-compatible with US Senate / Generic baseline.
    """
    if baselines is None:
        baselines = load_baselines()

    county_dict = {}
    hist_dict = {}
    if hasattr(county_returns, 'iterrows'):
        for _, row in county_returns.iterrows():
            cname = str(row.get('County', '')).upper().strip()
            if not cname or cname == 'STATEWIDE TOTAL':
                continue
            county_dict[cname] = {
                'dem': int(row.get('Democrat (2026)', 0)),
                'rep': int(row.get('Republican (2026)', 0)),
                'una': int(row.get('Unaffiliated (2026)', 0)),
                'tot': int(row.get('Total 2026', 0))
            }
            hist_dict[cname] = {
                'dem': int(row.get('Democrat (2022)', 0)),
                'rep': int(row.get('Republican (2022)', 0)),
                'una': int(row.get('Unaffiliated (2022)', 0)),
                'tot': int(row.get('Total 2022', 0))
            }
    else:
        for cname, vals in county_returns.items():
            county_dict[cname.upper().strip()] = vals

    # Compute county results for each race
    races_county_results = {rk: {} for rk in RACES_CONFIG}
    races_statewide = {}

    for rk in RACES_CONFIG:
        total_proj_votes = 0.0
        total_dem_votes = 0.0
        total_regime_18_votes = 0.0
        total_regime_22_votes = 0.0
        total_actual_2022_votes = 0.0

        counties_dem = 0
        counties_rep = 0
        flipped_to_dem = []
        flipped_to_rep = []

        ratings_summary = {
            'Safe D': 0, 'Very Likely D': 0, 'Likely D': 0, 'Lean D': 0, 'Toss Up': 0,
            'Lean R': 0, 'Likely R': 0, 'Very Likely R': 0, 'Safe R': 0
        }

        for cname, vals in county_dict.items():
            h22 = hist_dict.get(cname)
            res = predict_county(cname, vals['dem'], vals['rep'], vals['una'], vals['tot'], baselines, ev_day=ev_day, hist_2022=h22, race_key=rk)
            if res is not None:
                races_county_results[rk][cname] = res
                v = res['turnout_volume_weight']
                total_proj_votes += v
                total_dem_votes += (res['pred_final_dem'] / 100.0) * v
                total_regime_18_votes += (res['regime_2018_dem'] / 100.0) * v
                total_regime_22_votes += (res['regime_2022_dem'] / 100.0) * v
                total_actual_2022_votes += (res['actual_2022'] / 100.0) * v

                if res['pred_final_dem'] > 50.0:
                    counties_dem += 1
                else:
                    counties_rep += 1

                if res['actual_2022'] <= 50.0 and res['pred_final_dem'] > 50.0:
                    flipped_to_dem.append(cname)
                elif res['actual_2022'] > 50.0 and res['pred_final_dem'] <= 50.0:
                    flipped_to_rep.append(cname)

                if res.get('rating') in ratings_summary:
                    ratings_summary[res['rating']] += 1

        if total_proj_votes > 0:
            st_dem = (total_dem_votes / total_proj_votes) * 100.0
            st_rep = 100.0 - st_dem
            st_r18 = (total_regime_18_votes / total_proj_votes) * 100.0
            st_r22 = (total_regime_22_votes / total_proj_votes) * 100.0
            st_act22 = (total_actual_2022_votes / total_proj_votes) * 100.0

            st_low = min(st_r18, st_r22)
            st_high = max(st_r18, st_r22)
            st_dem = max(st_low, min(st_high, st_dem))
            st_rep = 100.0 - st_dem
            st_margin = st_dem - st_rep
            st_margin_low = 2.0 * st_low - 100.0
            st_margin_high = 2.0 * st_high - 100.0
            st_swing = st_dem - st_act22
        else:
            st_dem = st_rep = st_margin = st_low = st_high = st_margin_low = st_margin_high = st_swing = st_act22 = st_r18 = st_r22 = 0.0

        st_prob_info = compute_win_probability_and_rating(st_dem, st_low, st_high, st_act22, ev_day=ev_day)

        # Public Polling Integration & Precision-Weighted Empirical Bayes Synthesis
        raw_ev_dem = st_dem
        poll_info = get_poll_estimate(rk)
        poll_metadata = None
        if poll_info:
            p_mean = poll_info['mean']
            p_sig = max(1.20, poll_info['sigma'])
            ev_sig = max(1.75, st_prob_info.get('sigma', 2.58))

            w_ev = 1.0 / (ev_sig ** 2)
            w_poll = 1.0 / (p_sig ** 2)
            # Inverse-variance pooling between Early Voting voter transition model and quality-rated polling aggregate
            post_dem = (w_ev * raw_ev_dem + w_poll * p_mean) / (w_ev + w_poll)
            post_sig = max(1.85, 1.0 / math.sqrt(w_ev + w_poll)) # Maintain realistic election-day macro uncertainty floor

            st_shift = post_dem - raw_ev_dem
            st_dem = max(0.0, min(100.0, post_dem))
            st_rep = 100.0 - st_dem
            st_margin = st_dem - st_rep
            st_low = max(0.0, min(100.0, st_low + st_shift))
            st_high = max(0.0, min(100.0, st_high + st_shift))
            st_margin_low = 2.0 * st_low - 100.0
            st_margin_high = 2.0 * st_high - 100.0
            st_swing = st_dem - st_act22

            # Recompute win probability, confidence intervals, and rating with synthesized posterior
            st_prob_info = compute_win_probability_and_rating(
                st_dem, st_low, st_high, st_act22, ev_day=ev_day, sigma_floor=post_sig
            )

            poll_metadata = {
                'raw_ev_dem': round(raw_ev_dem, 2),
                'poll_mean_dem': round(p_mean, 2),
                'posterior_dem': round(post_dem, 2),
                'ev_weight': round(w_ev / (w_ev + w_poll), 3),
                'poll_weight': round(w_poll / (w_ev + w_poll), 3),
                'is_synthetic': poll_info.get('is_synthetic', False),
                'n_polls': poll_info.get('n_polls', 0),
                'polls': poll_info.get('polls', [])
            }

            # Propagate statewide empirical shift to each county in this race
            # so county map fills, metrics, and hover diagnostics remain 100% consistent with statewide synthesis
            counties_dem = 0
            counties_rep = 0
            flipped_to_dem = []
            flipped_to_rep = []
            ratings_summary = {k: 0 for k in ratings_summary}

            for cname, c_res in races_county_results[rk].items():
                c_dem_new = max(0.0, min(100.0, c_res['pred_final_dem'] + st_shift))
                c_rep_new = 100.0 - c_dem_new
                c_margin_new = c_dem_new - c_rep_new
                c_res['pred_final_dem'] = round(c_dem_new, 2)
                c_res['pred_final_rep'] = round(c_rep_new, 2)
                c_res['pred_dem_share'] = round(c_dem_new, 2)
                c_res['pred_rep_share'] = round(c_rep_new, 2)
                c_res['pred_margin'] = round(c_margin_new, 2)
                c_res['swing_vs_2022'] = round(c_dem_new - c_res['actual_2022'], 2)
                c_prob = compute_win_probability_and_rating(
                    c_dem_new, c_res['range_low'] + st_shift, c_res['range_high'] + st_shift,
                    c_res['actual_2022'], sigma_floor=c_res.get('sigma', post_sig), ev_day=ev_day
                )
                c_res['p_dem'] = c_prob['p_dem']
                c_res['p_rep'] = c_prob['p_rep']
                c_res['p_flip'] = c_prob['p_flip']
                c_res['rating'] = c_prob['rating']
                c_res['ci_95_low'] = c_prob['ci_95_low']
                c_res['ci_95_high'] = c_prob['ci_95_high']
                c_res['moe_95'] = c_prob['moe_95']

                if c_dem_new > 50.0:
                    counties_dem += 1
                else:
                    counties_rep += 1

                if c_res['actual_2022'] <= 50.0 and c_dem_new > 50.0:
                    flipped_to_dem.append(cname)
                elif c_res['actual_2022'] > 50.0 and c_dem_new <= 50.0:
                    flipped_to_rep.append(cname)

                if c_prob.get('rating') in ratings_summary:
                    ratings_summary[c_prob['rating']] += 1

        rc = RACES_CONFIG[rk]

        races_statewide[rk] = {
            'race_key': rk,
            'race_id': rc['id'],
            'race_name': rc['name'],
            'race_full_title': rc['full_title'],
            'dem_candidate': rc['dem_candidate'],
            'rep_candidate': rc['rep_candidate'],
            'incumbent': rc['incumbent'],
            'pred_final_dem': round(st_dem, 2),
            'pred_final_rep': round(st_rep, 2),
            'pred_dem_share': round(st_dem, 2),
            'pred_rep_share': round(st_rep, 2),
            'pred_margin': round(st_margin, 2),
            'range_low': round(st_low, 2),
            'range_high': round(st_high, 2),
            'margin_low': round(st_margin_low, 2),
            'margin_high': round(st_margin_high, 2),
            'actual_2022': round(st_act22, 2),
            'swing_vs_2022': round(st_swing, 2),
            'regime_2022_dem': round(st_r22, 2),
            'regime_2018_dem': round(st_r18, 2),
            'pred_dem_regime22': round(st_r22, 2),
            'pred_dem_regime18': round(st_r18, 2),
            'p_dem': st_prob_info['p_dem'],
            'p_rep': st_prob_info['p_rep'],
            'p_flip': st_prob_info['p_flip'],
            'rating': st_prob_info['rating'],
            'sigma': st_prob_info['sigma'],
            'moe_95': st_prob_info['moe_95'],
            'moe_margin': st_prob_info['moe_margin'],
            'ci_95_low': st_prob_info['ci_95_low'],
            'ci_95_high': st_prob_info['ci_95_high'],
            'ci_margin_low': st_prob_info['ci_margin_low'],
            'ci_margin_high': st_prob_info['ci_margin_high'],
            'margin_width': st_prob_info['margin_width'],
            'margin_confidence': st_prob_info['margin_confidence'],
            'margin_precision': st_prob_info['margin_precision'],
            'call_confidence': st_prob_info['call_confidence'],
            'call_ratio': st_prob_info['call_ratio'],
            'ratings_summary': ratings_summary,
            'counties_dem': counties_dem,
            'counties_rep': counties_rep,
            'flipped_to_dem': sorted(flipped_to_dem),
            'flipped_to_rep': sorted(flipped_to_rep),
            'poll_synthesis': poll_metadata
        }

    # Build composite county dictionaries with attached 'races'
    combined_counties = {}
    for cname in county_dict.keys():
        primary = races_county_results['us_senate'].get(cname)
        if primary is not None:
            c_copy = dict(primary)
            c_copy['races'] = {rk: races_county_results[rk].get(cname) for rk in RACES_CONFIG}
            combined_counties[cname] = c_copy

    # Attach legislative seat predictions and amendments
    leg_seats = predict_legislative_seats()

    all_statewide_races = dict(races_statewide)
    for ak, av in AMENDMENTS_CONFIG.items():
        all_statewide_races[ak] = av

    primary_statewide = dict(races_statewide['us_senate'])
    primary_statewide['races'] = all_statewide_races
    primary_statewide['amendments'] = AMENDMENTS_CONFIG
    primary_statewide['legislative'] = leg_seats

    return {
        'statewide': primary_statewide,
        'counties': combined_counties,
        'races': all_statewide_races,
        'amendments': AMENDMENTS_CONFIG,
        'legislative': leg_seats
    }


def predict_legislative_seats(senate_data_path=None, house_data_path=None):
    """
    Computes exact Poisson binomial distributions convolved with systemic swing
    uncertainty (sigma_sys = 2.5 pp margin) to yield expected seat totals, 95% Confidence Intervals,
    point estimates, and supermajority break probabilities for NC Senate and NC House.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not senate_data_path:
        for p in [
            os.path.join(script_dir, "nc_senate_data.json"),
            "/home/rann/src/website/mainwebsite/nc_senate_data.json",
            "/home/rann/src/elections/2026 analysis/nc_senate_data.json"
        ]:
            if os.path.exists(p):
                senate_data_path = p
                break

    if not house_data_path:
        for p in [
            os.path.join(script_dir, "nc_house_data.json"),
            "/home/rann/src/website/mainwebsite/nc_house_data.json",
            "/home/rann/src/elections/2026 analysis/nc_house_data.json"
        ]:
            if os.path.exists(p):
                house_data_path = p
                break

    results = {}
    for is_senate, path, total_seats, super_thresh, maj_thresh, sig_dist in [
        (True, senate_data_path, 50, 21, 26, 3.5),
        (False, house_data_path, 120, 49, 61, 3.8)
    ]:
        chamber_key = 'senate' if is_senate else 'house'
        chamber_name = 'NC Senate' if is_senate else 'NC House'
        if not path or not os.path.exists(path):
            if is_senate:
                results[chamber_key] = {
                    'chamber': chamber_name,
                    'total_seats': 50,
                    'point_estimate_dem': 22,
                    'point_estimate_rep': 28,
                    'expected_seats_dem': 21.1,
                    'expected_seats_rep': 28.9,
                    'ci_low': 19,
                    'ci_high': 24,
                    'ci_str': '[19, 24] seats',
                    'prob_break_supermajority': 65.7,
                    'prob_win_majority': 0.0
                }
            else:
                results[chamber_key] = {
                    'chamber': chamber_name,
                    'total_seats': 120,
                    'point_estimate_dem': 54,
                    'point_estimate_rep': 66,
                    'expected_seats_dem': 54.2,
                    'expected_seats_rep': 65.8,
                    'ci_low': 48,
                    'ci_high': 61,
                    'ci_str': '[48, 61] seats',
                    'prob_break_supermajority': 96.2,
                    'prob_win_majority': 3.6
                }
            continue

        try:
            with open(path) as f:
                dists = json.load(f)

            sigma_sys = 2.5
            points = 101
            deltas = [(-10.0 + 20.0 * i / (points - 1)) for i in range(points)]
            weights = [math.exp(-0.5 * (d / sigma_sys)**2) / (sigma_sys * math.sqrt(2 * math.pi)) for d in deltas]
            sum_w = sum(weights)
            weights = [w / sum_w for w in weights]

            seat_probs = [0.0] * (total_seats + 1)
            for d, w in zip(deltas, weights):
                p_list = []
                for dist in dists.values():
                    if dist.get('is_uncontested'):
                        p_list.append(1.0 if dist.get('dem_candidate') else 0.0)
                    else:
                        m = dist['pred_margin'] + d
                        z = m / sig_dist
                        p = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
                        p_list.append(max(0.0001, min(0.9999, p)))

                dp = [0.0] * (total_seats + 1)
                dp[0] = 1.0
                for p in p_list:
                    for k in range(total_seats, 0, -1):
                        dp[k] = dp[k] * (1.0 - p) + dp[k - 1] * p
                    dp[0] = dp[0] * (1.0 - p)

                for k in range(total_seats + 1):
                    seat_probs[k] += dp[k] * w

            exp_seats = sum(k * seat_probs[k] for k in range(total_seats + 1))
            cum = 0.0
            ci_low = 0
            ci_high = total_seats
            for k in range(total_seats + 1):
                cum += seat_probs[k]
                if cum >= 0.025 and ci_low == 0:
                    ci_low = k
                if cum >= 0.975:
                    ci_high = k
                    break

            prob_break_super = sum(seat_probs[k] for k in range(super_thresh, total_seats + 1)) * 100.0
            prob_majority = sum(seat_probs[k] for k in range(maj_thresh, total_seats + 1)) * 100.0
            point_est = sum(1 for dist in dists.values() if dist['pred_margin'] > 0)

            results[chamber_key] = {
                'chamber': chamber_name,
                'total_seats': total_seats,
                'point_estimate_dem': point_est,
                'point_estimate_rep': total_seats - point_est,
                'expected_seats_dem': round(exp_seats, 1),
                'expected_seats_rep': round(total_seats - exp_seats, 1),
                'ci_low': ci_low,
                'ci_high': ci_high,
                'ci_str': f'[{ci_low}, {ci_high}] seats',
                'prob_break_supermajority': round(prob_break_super, 1),
                'prob_win_majority': round(prob_majority, 1)
            }
        except Exception as e:
            print(f"Warning: Error calculating {chamber_name} seat distribution: {e}")
            results[chamber_key] = {
                'chamber': chamber_name,
                'total_seats': total_seats,
                'point_estimate_dem': 22 if is_senate else 54,
                'point_estimate_rep': 28 if is_senate else 66,
                'expected_seats_dem': 21.1 if is_senate else 54.2,
                'expected_seats_rep': 28.9 if is_senate else 65.8,
                'ci_low': 19 if is_senate else 48,
                'ci_high': 24 if is_senate else 61,
                'ci_str': f"[{19 if is_senate else 48}, {24 if is_senate else 61}] seats",
                'prob_break_supermajority': 65.7 if is_senate else 96.2,
                'prob_win_majority': 0.0 if is_senate else 3.6
            }

    return results


def predict_precinct(county_id, c26, c22, c_fc, baselines=None, ev_day=None, race_key='us_senate'):
    """
    Computes 2026 forecast for a precinct within a county using the redesigned transition
    and propensity matrix, with empirical Bayes shrinkage toward the county's predicted margin.
    Supports individual race_key or builds full multi-race hierarchy.
    """
    if baselines is None:
        baselines = load_baselines()

    c_key = str(county_id).upper().strip()
    b = baselines.get(c_key)
    rc = RACES_CONFIG.get(race_key, RACES_CONFIG['us_senate'])
    trans = get_voter_transition_matrix(c_key, race_key=race_key)

    tot26 = c26.get('tot', 0) if c26 else 0
    if not b or not c_fc or tot26 <= 0:
        if c_fc:
            # Fall back to county forecast
            target_fc = c_fc.get('races', {}).get(race_key, c_fc) if isinstance(c_fc, dict) else c_fc
            return {
                'pred_final_dem': target_fc['pred_final_dem'],
                'pred_final_rep': target_fc['pred_final_rep'],
                'pred_dem_share': target_fc['pred_final_dem'],
                'pred_rep_share': target_fc['pred_final_rep'],
                'pred_margin': target_fc['pred_margin'],
                'pred_dem_regime22': target_fc.get('pred_dem_regime22', target_fc.get('regime_2022_dem', 0.0)),
                'pred_dem_regime18': target_fc.get('pred_dem_regime18', target_fc.get('regime_2018_dem', 0.0)),
                'range_low': target_fc['range_low'],
                'range_high': target_fc['range_high'],
                'actual_2022': target_fc.get('actual_2022'),
                'swing_vs_2022': target_fc.get('swing_vs_2022', 0.0),
                'regime_2022_dem': target_fc.get('regime_2022_dem', 0.0),
                'regime_2018_dem': target_fc.get('regime_2018_dem', 0.0),
                'p_dem': target_fc.get('p_dem'),
                'p_rep': target_fc.get('p_rep'),
                'p_flip': target_fc.get('p_flip'),
                'rating': target_fc.get('rating'),
                'sigma': target_fc.get('sigma'),
                'moe_95': target_fc.get('moe_95'),
                'moe_margin': target_fc.get('moe_margin'),
                'ci_95_low': target_fc.get('ci_95_low'),
                'ci_95_high': target_fc.get('ci_95_high'),
                'ci_margin_low': target_fc.get('ci_margin_low'),
                'ci_margin_high': target_fc.get('ci_margin_high'),
                'margin_width': target_fc.get('margin_width'),
                'margin_confidence': target_fc.get('margin_confidence'),
                'margin_precision': target_fc.get('margin_precision'),
                'call_confidence': target_fc.get('call_confidence'),
                'call_ratio': target_fc.get('call_ratio'),
                'race_key': race_key
            }
        return None

    vd = float(c26.get('dem', 0))
    vr = float(c26.get('rep', 0))
    vu = float(c26.get('una', 0))

    ev_dem_v = trans['dem_loyalty'] * vd + trans['rep_crossover_to_dem'] * vr + trans['una_dem_share'] * vu
    ev_rep_v = trans['dem_defection_to_rep'] * vd + (1.0 - trans['rep_crossover_to_dem']) * vr + (1.0 - trans['una_dem_share']) * vu
    est_ev_dem = (ev_dem_v / (ev_dem_v + ev_rep_v)) * 100.0 if (ev_dem_v + ev_rep_v) > 0 else 50.0

    pct_u26 = (vu / tot26) * 100.0
    pct_r26 = (vr / tot26) * 100.0

    tot22 = c22.get('tot', 0) if c22 else 0
    pct_u22 = (float(c22.get('una', 0)) / tot22 * 100.0) if tot22 > 0 else 30.0
    pct_r22 = (float(c22.get('rep', 0)) / tot22 * 100.0) if tot22 > 0 else 31.5

    delta_u = pct_u26 - pct_u22
    delta_r = pct_r26 - pct_r22
    race_shift = rc.get('shift_offset', 0.0)
    # Two-Mode (Early Vote vs Election Day) Decomposition Engine
    eday_decomp = compute_eday_adjusted_forecast(
        c_key, est_ev_dem, tot26, b, trans, rc, ev_day=ev_day,
        pct_r26=pct_r26, pct_r22=pct_r22, delta_u=delta_u
    )
    raw_final_dem = eday_decomp['raw_final_dem']
    cannibalization = eday_decomp['cannibalization']
    expansion = eday_decomp['expansion']
    adj_shift = eday_decomp['adj_shift']

    # Empirical Bayes shrinkage toward the county's predicted margin for this race
    s = 250.0 / (250.0 + tot26)
    target_c_fc = c_fc.get('races', {}).get(race_key, c_fc) if isinstance(c_fc, dict) else c_fc
    county_dem = target_c_fc['pred_final_dem']
    eb_final_dem = (1.0 - s) * raw_final_dem + s * county_dem

    err_18 = b['err_2018']
    err_22 = b['err_2022']
    sig_floor = None
    if ev_day is not None and 'by_day' in b:
        day_str = str(ev_day)
        if day_str in b['by_day']:
            err_18 = b['by_day'][day_str]['err_2018']
            err_22 = b['by_day'][day_str]['err_2022']
            rmse = math.sqrt((err_18**2 + err_22**2) / 2.0)
            spread = abs(err_18 - err_22)
            sig_floor = max(0.50, rmse, spread / 3.92)

    r18 = round(max(0.0, min(100.0, raw_final_dem - err_18)), 2)
    r22 = round(max(0.0, min(100.0, raw_final_dem - err_22)), 2)
    range_low = min(r18, r22)
    range_high = max(r18, r22)

    eb_final_dem = max(range_low, min(range_high, eb_final_dem))
    eb_final_dem = round(max(0.0, min(100.0, eb_final_dem)), 2)
    eb_final_rep = round(100.0 - eb_final_dem, 2)
    pred_margin = round(eb_final_dem - eb_final_rep, 2)

    actual_2022_base = max(0.0, min(100.0, b['final_2022'] + rc.get('historical_diff_2022', 0.0)))
    if tot22 > 0:
        vd22 = float(c22.get('dem', 0))
        vr22 = float(c22.get('rep', 0))
        vu22 = float(c22.get('una', 0))
        ev22_d = trans['dem_loyalty'] * vd22 + trans['rep_crossover_to_dem'] * vr22 + trans['una_dem_share'] * vu22
        ev22_r = trans['dem_defection_to_rep'] * vd22 + (1.0 - trans['rep_crossover_to_dem']) * vr22 + (1.0 - trans['una_dem_share']) * vu22
        raw_22_dem = (ev22_d / (ev22_d + ev22_r) * 100.0) + b['shift_2022'] + race_shift if (ev22_d + ev22_r) > 0 else actual_2022_base
        s22 = 250.0 / (250.0 + tot22)
        act22_est = round((1.0 - s22) * raw_22_dem + s22 * actual_2022_base, 2)
        swing = round(eb_final_dem - act22_est, 2)
    else:
        act22_est = round(actual_2022_base, 2)
        swing = round(eb_final_dem - act22_est, 2)

    p_prob_info = compute_win_probability_and_rating(eb_final_dem, range_low, range_high, act22_est, sigma_floor=sig_floor, ev_day=ev_day)

    return {
        'pred_final_dem': eb_final_dem,
        'pred_final_rep': eb_final_rep,
        'pred_dem_share': eb_final_dem,
        'pred_rep_share': eb_final_rep,
        'pred_margin': pred_margin,
        'pred_dem_regime22': r22,
        'pred_dem_regime18': r18,
        'range_low': range_low,
        'range_high': range_high,
        'actual_2022': act22_est,
        'swing_vs_2022': swing,
        'regime_2022_dem': r22,
        'regime_2018_dem': r18,
        'p_dem': p_prob_info['p_dem'],
        'p_rep': p_prob_info['p_rep'],
        'p_flip': p_prob_info['p_flip'],
        'rating': p_prob_info['rating'],
        'sigma': p_prob_info['sigma'],
        'moe_95': p_prob_info['moe_95'],
        'moe_margin': p_prob_info['moe_margin'],
        'ci_95_low': p_prob_info['ci_95_low'],
        'ci_95_high': p_prob_info['ci_95_high'],
        'ci_margin_low': p_prob_info['ci_margin_low'],
        'ci_margin_high': p_prob_info['ci_margin_high'],
        'margin_width': p_prob_info['margin_width'],
        'margin_confidence': p_prob_info['margin_confidence'],
        'margin_precision': p_prob_info['margin_precision'],
        'call_confidence': p_prob_info['call_confidence'],
        'call_ratio': p_prob_info['call_ratio'],
        'race_key': race_key
    }


def predict_precinct_all_races(county_id, c26, c22, c_fc, baselines=None, ev_day=None):
    """
    Computes precinct forecasts across all 5 statewide races.
    """
    primary = predict_precinct(county_id, c26, c22, c_fc, baselines=baselines, ev_day=ev_day, race_key='us_senate')
    if primary is None:
        return None

    races = {}
    for rk in RACES_CONFIG:
        if rk == 'us_senate':
            races[rk] = dict(primary)
        else:
            races[rk] = predict_precinct(county_id, c26, c22, c_fc, baselines=baselines, ev_day=ev_day, race_key=rk)

    res = dict(primary)
    res['races'] = races
    return res
