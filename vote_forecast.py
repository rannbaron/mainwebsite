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

    # High-propensity Republican cannibalization discount
    cannibalization = max(0.75, min(1.0, 1.0 - 0.25 * max(0.0, delta_r / 5.0)))
    # Low-propensity Unaffiliated/young expansion premium
    expansion = max(-1.5, min(2.5, (delta_u / 100.0) * (trans['una_dem_share'] - 0.50) * 15.0))

    # Race-specific shift offset (e.g. -1.45 pp for Supreme Court, -1.85 pp for CoA 1)
    race_shift = rc.get('shift_offset', 0.0)
    adj_shift = b['shift_2022'] * cannibalization + expansion + race_shift
    raw_final_dem = est_ev_dem + adj_shift

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
        # Analytical Diagnostics
        'tier': trans['tier'],
        'crossover_r_to_d': round(trans['rep_crossover_to_dem'] * 100.0, 1),
        'defection_d_to_r': round(trans['dem_defection_to_rep'] * 100.0, 1),
        'una_dem_share': round(trans['una_dem_share'] * 100.0, 1),
        'propensity_cannibalization_factor': round(cannibalization, 3),
        'propensity_expansion_premium': round(expansion, 2)
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
            'flipped_to_rep': sorted(flipped_to_rep)
        }

    # Build composite county dictionaries with attached 'races'
    combined_counties = {}
    for cname in county_dict.keys():
        primary = races_county_results['us_senate'].get(cname)
        if primary is not None:
            c_copy = dict(primary)
            c_copy['races'] = {rk: races_county_results[rk].get(cname) for rk in RACES_CONFIG}
            combined_counties[cname] = c_copy

    primary_statewide = dict(races_statewide['us_senate'])
    primary_statewide['races'] = races_statewide

    return {
        'statewide': primary_statewide,
        'counties': combined_counties,
        'races': races_statewide
    }


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
    cannibalization = max(0.75, min(1.0, 1.0 - 0.25 * max(0.0, delta_r / 5.0)))
    expansion = max(-1.5, min(2.5, (delta_u / 100.0) * (trans['una_dem_share'] - 0.50) * 15.0))

    race_shift = rc.get('shift_offset', 0.0)
    adj_shift = b['shift_2022'] * cannibalization + expansion + race_shift
    raw_final_dem = est_ev_dem + adj_shift

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
