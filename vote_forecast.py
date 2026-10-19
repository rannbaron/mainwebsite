import os
import json
import numpy as np

DEFAULT_BASELINES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "county_vote_baselines.json")

def load_baselines(path=None):
    if path is None:
        path = DEFAULT_BASELINES_PATH
    if not os.path.exists(path):
        # Fallback to local file in current working directory
        if os.path.exists("county_vote_baselines.json"):
            path = "county_vote_baselines.json"
        elif os.path.exists("remote_deployment/county_vote_baselines.json"):
            path = "remote_deployment/county_vote_baselines.json"
        else:
            raise FileNotFoundError(f"County baselines JSON not found at {path}")
    
    with open(path, 'r') as f:
        return json.load(f)

def predict_county(county_name, dem, rep, una, tot, baselines=None):
    """
    Computes vote prediction for a single county based on current early voting turnout,
    historical 2022 UNA voting factor, 2022 EV-to-Final dropoff, and dual-regime empirical bounds.
    """
    if baselines is None:
        baselines = load_baselines()

    c_key = county_name.upper().strip()
    if c_key not in baselines or tot <= 0:
        return None

    b = baselines[c_key]
    pct_d = (dem / tot) * 100.0
    pct_u = (una / tot) * 100.0

    # 1. Raw early vote estimate + 2022 historical shift
    est_ev_dem = pct_d + b['una_factor_2022'] * pct_u
    raw_final_dem = est_ev_dem + b['shift_2022']

    # 2. Dual-Regime bounds (2018 Dem momentum vs 2022 Rep E-Day surge)
    regime_18_dem = raw_final_dem - b['err_2018']
    regime_22_dem = raw_final_dem - b['err_2022']
    range_low = min(regime_18_dem, regime_22_dem)
    range_high = max(regime_18_dem, regime_22_dem)

    # 3. Empirical Bayes shrinkage point estimate toward statewide macro average (+0.17%)
    v = b['votes_2022']
    s = 30000.0 / (30000.0 + v)
    shrunk_bias = (1.0 - s) * ((b['err_2018'] + b['err_2022']) / 2.0) + s * 0.17
    eb_final_dem = raw_final_dem - shrunk_bias

    # Clamp to valid percentages
    eb_final_dem = max(0.0, min(100.0, eb_final_dem))
    range_low = max(0.0, min(100.0, range_low))
    range_high = max(0.0, min(100.0, range_high))

    eb_final_rep = 100.0 - eb_final_dem
    pred_margin = eb_final_dem - eb_final_rep
    margin_low = 2.0 * range_low - 100.0
    margin_high = 2.0 * range_high - 100.0
    swing = eb_final_dem - b['final_2022']

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
        'actual_2022': round(b['final_2022'], 2),
        'swing_vs_2022': round(swing, 2),
        'regime_2022_dem': round(regime_22_dem, 2),
        'regime_2018_dem': round(regime_18_dem, 2),
        'pred_dem_regime22': round(regime_22_dem, 2),
        'pred_dem_regime18': round(regime_18_dem, 2),
        'turnout_volume_weight': round(v, 1)
    }

def predict_all(county_returns, baselines=None):
    """
    Computes county-level predictions and a volume-weighted statewide rollup.
    county_returns can be a dict: { 'COUNTY_NAME': {'dem': int, 'rep': int, 'una': int, 'tot': int} }
    or a pandas DataFrame with columns ['County', 'Democrat (2026)', 'Republican (2026)', 'Unaffiliated (2026)', 'Total 2026'].
    """
    if baselines is None:
        baselines = load_baselines()

    county_dict = {}
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
    else:
        for cname, vals in county_returns.items():
            county_dict[cname.upper().strip()] = vals

    county_results = {}
    total_proj_votes = 0.0
    total_dem_votes = 0.0
    total_regime_18_votes = 0.0
    total_regime_22_votes = 0.0
    total_actual_2022_votes = 0.0

    counties_dem = 0
    counties_rep = 0
    flipped_to_dem = []
    flipped_to_rep = []

    for cname, vals in county_dict.items():
        res = predict_county(cname, vals['dem'], vals['rep'], vals['una'], vals['tot'], baselines)
        if res is not None:
            county_results[cname] = res
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

    if total_proj_votes > 0:
        st_dem = (total_dem_votes / total_proj_votes) * 100.0
        st_rep = 100.0 - st_dem
        st_r18 = (total_regime_18_votes / total_proj_votes) * 100.0
        st_r22 = (total_regime_22_votes / total_proj_votes) * 100.0
        st_act22 = (total_actual_2022_votes / total_proj_votes) * 100.0

        st_low = min(st_r18, st_r22)
        st_high = max(st_r18, st_r22)
        st_margin = st_dem - st_rep
        st_margin_low = 2.0 * st_low - 100.0
        st_margin_high = 2.0 * st_high - 100.0
        st_swing = st_dem - st_act22
    else:
        st_dem = st_rep = st_margin = st_low = st_high = st_margin_low = st_margin_high = st_swing = st_act22 = st_r18 = st_r22 = 0.0

    statewide = {
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
        'counties_dem': counties_dem,
        'counties_rep': counties_rep,
        'flipped_to_dem': sorted(flipped_to_dem),
        'flipped_to_rep': sorted(flipped_to_rep)
    }

    return {
        'counties': county_results,
        'statewide': statewide
    }

def predict_precinct(county_id, c26, c22, c_fc, baselines=None):
    """
    Computes 2026 forecast for a precinct within a county.
    Uses county-level UNA calibration and historical shift,
    with empirical Bayes shrinkage toward the county's predicted margin.
    """
    if baselines is None:
        baselines = load_baselines()

    c_key = str(county_id).upper().strip()
    b = baselines.get(c_key)

    tot26 = c26.get('tot', 0) if c26 else 0
    if not b or not c_fc or tot26 <= 0:
        if c_fc:
            return {
                'pred_final_dem': c_fc['pred_final_dem'],
                'pred_final_rep': c_fc['pred_final_rep'],
                'pred_dem_share': c_fc['pred_final_dem'],
                'pred_rep_share': c_fc['pred_final_rep'],
                'pred_margin': c_fc['pred_margin'],
                'pred_dem_regime22': c_fc.get('pred_dem_regime22', c_fc.get('regime_2022_dem', 0.0)),
                'pred_dem_regime18': c_fc.get('pred_dem_regime18', c_fc.get('regime_2018_dem', 0.0)),
                'range_low': c_fc['range_low'],
                'range_high': c_fc['range_high'],
                'actual_2022': c_fc.get('actual_2022'),
                'swing_vs_2022': c_fc.get('swing_vs_2022', 0.0),
                'regime_2022_dem': c_fc.get('regime_2022_dem', 0.0),
                'regime_2018_dem': c_fc.get('regime_2018_dem', 0.0)
            }
        return None

    pct_d = (c26.get('dem', 0) / tot26) * 100.0
    pct_u = (c26.get('una', 0) / tot26) * 100.0
    est_ev_dem = pct_d + b['una_factor_2022'] * pct_u
    raw_final_dem = est_ev_dem + b['shift_2022']

    s = 250.0 / (250.0 + tot26)
    county_dem = c_fc['pred_final_dem']
    eb_final_dem = (1.0 - s) * raw_final_dem + s * county_dem
    eb_final_dem = round(max(0.0, min(100.0, eb_final_dem)), 2)
    eb_final_rep = round(100.0 - eb_final_dem, 2)
    pred_margin = round(eb_final_dem - eb_final_rep, 2)

    r18 = round(max(0.0, min(100.0, eb_final_dem - b['err_2018'])), 2)
    r22 = round(max(0.0, min(100.0, eb_final_dem - b['err_2022'])), 2)
    range_low = min(r18, r22)
    range_high = max(r18, r22)

    tot22 = c22.get('tot', 0) if c22 else 0
    if tot22 > 0:
        pct_d22 = (c22.get('dem', 0) / tot22) * 100.0
        pct_u22 = (c22.get('una', 0) / tot22) * 100.0
        raw_22_dem = pct_d22 + b['una_factor_2022'] * pct_u22 + b['shift_2022']
        s22 = 250.0 / (250.0 + tot22)
        act22_est = round((1.0 - s22) * raw_22_dem + s22 * b['final_2022'], 2)
        swing = round(eb_final_dem - act22_est, 2)
    else:
        act22_est = round(b['final_2022'], 2)
        swing = round(eb_final_dem - act22_est, 2)

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
        'regime_2018_dem': r18
    }

if __name__ == '__main__':
    import pandas as pd
    df = pd.read_csv('nc_early_voting_party_ev_day_3.csv')
    res = predict_all(df)
    print("Statewide Forecast:")
    print(json.dumps(res['statewide'], indent=2))
    print("\nSample County Forecast (Alamance):")
    print(json.dumps(res['counties'].get('ALAMANCE'), indent=2))

