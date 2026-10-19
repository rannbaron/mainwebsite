#!/usr/bin/env python3
"""
NC Early Voting Autonomous Server-Side Updater
----------------------------------------------
Runs daily on a remote Linux server via cron at 6:00 AM.
- Checks NCSBE S3 for updated 2026 voter files using HTTP If-Modified-Since / ETag.
- If changed, downloads the ~22 MB zip and aggregates accepted ballots directly in-memory.
- Merges 2026 returns into the pre-cached baseline (2018 & 2022).
- Automatically writes the updated public 'index.html'.

Requirements:
    pip install requests pandas
"""

import os
import re
import sys
import json
import time
import shutil
import zipfile
import argparse
import requests
import pandas as pd
from datetime import datetime

NCSBE_2026_URL = "https://s3.amazonaws.com/dl.ncsbe.gov/ENRS/2026_11_03/absentee_county_20261103.zip"
EV_START_DATE = pd.to_datetime("2026-10-15")

def norm(val):
    if val is None or pd.isna(val):
        return ''
    s = str(val).strip()
    try:
        f = float(s)
        if f.is_integer():
            s = str(int(f))
    except (ValueError, OverflowError):
        pass
    s = s.upper()
    s = re.sub(r'^(PRECINCT|PCT|PREC)\s*[\#\:\-]?\s*', '', s)
    s = re.sub(r'[^A-Z0-9]', '', s)
    return s

def check_for_updates(zip_cache_path, meta_path, force=False):
    headers = {}
    if not force and os.path.exists(meta_path):
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            if meta.get('etag'):
                headers['If-None-Match'] = f'"{meta["etag"].strip(chr(34))}"'
            if meta.get('last_modified'):
                headers['If-Modified-Since'] = meta['last_modified']
        except Exception:
            pass

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking NCSBE S3 server for 2026 updates...")
    try:
        resp = requests.get(NCSBE_2026_URL, headers=headers, stream=True, timeout=120)
        if resp.status_code == 304 and not force:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] No changes detected on NCSBE server (HTTP 304).")
            return False, None

        resp.raise_for_status()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] New data detected! Downloading 2026 voter file ({int(resp.headers.get('Content-Length', 0)):,} bytes)...")
        with open(zip_cache_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        meta = {
            'etag': resp.headers.get('ETag', '').strip('"'),
            'last_modified': resp.headers.get('Last-Modified', ''),
            'download_time': datetime.now().isoformat()
        }
        with open(meta_path, 'w') as f:
            json.dump(meta, f)

        return True, zip_cache_path
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error checking/downloading from NCSBE: {e}")
        if os.path.exists(zip_cache_path) and force:
            print("Using existing local zip cache due to --force flag.")
            return True, zip_cache_path
        raise

def process_2026_returns(zip_path, shp_lookup, target_ev_day=None):
    t0 = time.time()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Aggregating 2026 early voting returns from zip archive...")

    cols = ['county_desc', 'precinct_desc', 'ballot_rtn_status', 'ballot_rtn_dt', 'voter_party_code', 'race']
    durham_splits = {'30-3': '30-1', '30-4': '30-1', '33-1': '33', '33-2': '33', '35-4': '35.3', '35-5': '35.3', '56': '53-1', '57': '53-1'}

    if target_ev_day is not None:
        calculated_ev_day = target_ev_day
    else:
        today = pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))
        calendar_day = (today - EV_START_DATE).days + 1
        calculated_ev_day = max(1, calendar_day - 1)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Filtering 2026 returns up to EV Day {calculated_ev_day} (Morning of Calendar Day {calendar_day if target_ev_day is None else target_ev_day+1})...")

    records = []
    with zipfile.ZipFile(zip_path, 'r') as z:
        for fname in z.namelist():
            if fname.endswith('.csv'):
                with z.open(fname) as f:
                    try:
                        df = pd.read_csv(f, encoding='latin1', low_memory=False, usecols=lambda c: c.lower().strip() in cols)
                        df.columns = [c.lower().strip() for c in df.columns]
                        if 'ballot_rtn_status' in df.columns:
                            df = df[df['ballot_rtn_status'].fillna('').str.contains('ACCEPTED', case=False)]
                        if df.empty:
                            continue
                        df['rtn_date'] = pd.to_datetime(df['ballot_rtn_dt'], errors='coerce')
                        df = df.dropna(subset=['rtn_date'])
                        if df.empty:
                            continue

                        df['ev_day'] = (df['rtn_date'] - EV_START_DATE).dt.days + 1
                        df = df[df['ev_day'] <= calculated_ev_day]
                        if df.empty:
                            continue

                        county = df['county_desc'].iloc[0].upper().strip()
                        c_map = shp_lookup.get(county, {})

                        def match_pid(raw_p):
                            if county == 'WAYNE':
                                try:
                                    f = float(raw_p)
                                    i = int(f)
                                    w_str = str(i) if i in [1920, 2530] else f"{i:02d}"
                                    if w_str in c_map:
                                        return c_map[w_str]
                                except Exception:
                                    pass
                            p_norm = norm(raw_p)
                            if p_norm in c_map:
                                return c_map[p_norm]
                            if p_norm.lstrip('0') in c_map:
                                return c_map[p_norm.lstrip('0')]
                            if county == 'DURHAM' and raw_p in durham_splits:
                                return raw_p
                            return raw_p

                        df['matched_pid'] = df['precinct_desc'].apply(match_pid)
                        df['party'] = df['voter_party_code'].astype(str).str.upper().str.strip()
                        df['race_clean'] = df['race'].astype(str).str.upper()
                        df['is_white'] = df['race_clean'].str.contains('WHITE')
                        df['is_black'] = df['race_clean'].str.contains('BLACK')

                        gp = df.groupby('matched_pid').agg(
                            tot=('party', 'count'),
                            dem=('party', lambda s: (s == 'DEM').sum()),
                            rep=('party', lambda s: (s == 'REP').sum()),
                            una=('party', lambda s: (s == 'UNA').sum()),
                            white=('is_white', 'sum'),
                            black=('is_black', 'sum')
                        ).reset_index()
                        gp['county'] = county
                        records.append(gp)
                    except Exception:
                        pass

    if not records:
        print("No accepted ballots found in archive.")
        return None, 0

    p_df = pd.concat(records, ignore_index=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Processed {p_df['tot'].sum():,} ballots across {len(p_df)} precincts in {time.time()-t0:.1f}s (EV Day {calculated_ev_day})")
    return p_df, calculated_ev_day

def update_map_files(p_df, ev_day, base_json_path, output_html_path, dest_public_html=None):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Updating map dataset with 2026 Day {ev_day} returns...")

    with open(base_json_path, 'r') as f:
        data = json.load(f)

    # Index 2026 precinct records by (county, matched_pid)
    dict_26 = {(r['county'], r['matched_pid']): r for _, r in p_df.iterrows()}

    # County accumulators for 2026
    county_sums = {}
    st_tot = 0
    st_dem = 0
    st_rep = 0
    st_una = 0
    st_white = 0
    st_black = 0

    durham_splits = {'30-3': '30-1', '30-4': '30-1', '33-1': '33', '33-2': '33', '35-4': '35.3', '35-5': '35.3', '56': '53-1', '57': '53-1'}

    # 1. Update Precinct Data
    for cname, plist in data['precincts'].items():
        if cname not in county_sums:
            county_sums[cname] = {'tot': 0, 'dem': 0, 'rep': 0, 'una': 0, 'white': 0, 'black': 0}
        
        for pr in plist:
            pid = pr['id']
            key = (cname, pid)
            if key in dict_26:
                row = dict_26[key]
                c26 = {
                    'tot': int(row['tot']),
                    'dem': int(row['dem']),
                    'rep': int(row['rep']),
                    'una': int(row['una']),
                    'white': int(row['white']),
                    'black': int(row['black'])
                }
            elif cname == 'DURHAM' and pid in durham_splits and (cname, durham_splits[pid]) in dict_26:
                row = dict_26[(cname, durham_splits[pid])]
                c26 = {
                    'tot': int(row['tot']),
                    'dem': int(row['dem']),
                    'rep': int(row['rep']),
                    'una': int(row['una']),
                    'white': int(row['white']),
                    'black': int(row['black'])
                }
            else:
                c26 = {'tot': 0, 'dem': 0, 'rep': 0, 'una': 0, 'white': 0, 'black': 0}

            pr['data']['2026'] = c26
            
            # Accumulate county sums
            county_sums[cname]['tot'] += c26['tot']
            county_sums[cname]['dem'] += c26['dem']
            county_sums[cname]['rep'] += c26['rep']
            county_sums[cname]['una'] += c26['una']
            county_sums[cname]['white'] += c26['white']
            county_sums[cname]['black'] += c26['black']

    # 2. Update County Data
    county_direct = {}
    for cname, c_group in p_df.groupby('county'):
        county_direct[cname] = {
            'tot': int(c_group['tot'].sum()),
            'dem': int(c_group['dem'].sum()),
            'rep': int(c_group['rep'].sum()),
            'una': int(c_group['una'].sum()),
            'white': int(c_group['white'].sum()),
            'black': int(c_group['black'].sum())
        }

    for county in data['counties']:
        cid = county['id']
        c_stats = county_direct.get(cid) or county_sums.get(cid, {'tot': 0, 'dem': 0, 'rep': 0, 'una': 0, 'white': 0, 'black': 0})
        county['data']['2026'] = c_stats
        
        st_tot += c_stats['tot']
        st_dem += c_stats['dem']
        st_rep += c_stats['rep']
        st_una += c_stats['una']
        st_white += c_stats['white']
        st_black += c_stats['black']

    # 3. Update Statewide Summary
    data['state']['ev_day'] = ev_day
    data['state']['data']['2026'] = {
        'tot': st_tot,
        'dem': st_dem,
        'rep': st_rep,
        'una': st_una,
        'white': st_white,
        'black': st_black
    }

    # 3.5. Recompute 2026 Vote Forecasts (Dual-Regime & Empirical Bayes)
    try:
        import vote_forecast
        c_returns = {c['id']: c['data']['2026'] for c in data['counties']}
        forecast_res = vote_forecast.predict_all(c_returns)
        for county in data['counties']:
            cid = county['id']
            county['forecast'] = forecast_res['counties'].get(cid)
        data['state']['forecast'] = forecast_res['statewide']
        for cid, plist in data.get('precincts', {}).items():
            c_fc = forecast_res['counties'].get(cid)
            for p in plist:
                p['forecast'] = vote_forecast.predict_precinct(cid, p['data'].get('2026'), p['data'].get('2022'), c_fc)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Updated 2026 Vote Forecast: Statewide Dem {data['state']['forecast']['pred_final_dem']}% [{data['state']['forecast']['range_low']}% - {data['state']['forecast']['range_high']}%]")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: Error computing vote forecast: {e}")

    # Save updated base JSON
    with open(base_json_path, 'w') as f:
        json.dump(data, f)

    # 4. Inject into index.html
    compact_json = json.dumps(data, separators=(',', ':'))
    if os.path.exists(output_html_path):
        with open(output_html_path, 'r') as f:
            html = f.read()
        updated_html = re.sub(r'Cumulative Day \d+', f'Cumulative Day {ev_day}', html)
        updated_html = re.sub(r'State Summary \(Day \d+\)', f'State Summary (Day {ev_day})', updated_html)
        updated_html = re.sub(
            r'window\.NC_MAP_DATA\s*=\s*\{[\s\S]*?\};\s*</script>',
            f'window.NC_MAP_DATA = {compact_json};\n  </script>',
            updated_html
        )
        with open(output_html_path, 'w') as f:
            f.write(updated_html)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Injected updated data into {output_html_path} ({len(updated_html):,} bytes)")

        # Also inject into beta/index.html if it exists
        beta_html_path = os.path.join(os.path.dirname(output_html_path) or ".", "beta", "index.html")
        if os.path.exists(beta_html_path):
            with open(beta_html_path, 'r') as f:
                b_html = f.read()
            updated_b_html = re.sub(r'Cumulative Day \d+', f'Cumulative Day {ev_day}', b_html)
            updated_b_html = re.sub(r'State Summary \(Day \d+\)', f'State Summary (Day {ev_day})', updated_b_html)
            updated_b_html = re.sub(
                r'window\.NC_MAP_DATA\s*=\s*\{[\s\S]*?\};\s*</script>',
                f'window.NC_MAP_DATA = {compact_json};\n  </script>',
                updated_b_html
            )
            with open(beta_html_path, 'w') as f:
                f.write(updated_b_html)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Injected updated data into {beta_html_path} ({len(updated_b_html):,} bytes)")

        # Copy to destination public_html if specified
        dest_path = dest_public_html or os.getenv("DEST_HTML_PATH", "")
        if dest_path and dest_path.strip() and dest_path.lower() != "none":
            try:
                dest_dir = os.path.dirname(dest_path)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)
                    try:
                        os.chmod(dest_dir, 0o755)
                    except Exception:
                        pass
                shutil.copy2(output_html_path, dest_path)
                try:
                    os.chmod(dest_path, 0o644) # Ensure world-readable for Apache/Nginx
                except Exception:
                    pass
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully copied to public_html: {dest_path} (mode: 0644)")

                # Also copy beta to destination if present
                if os.path.exists(beta_html_path):
                    dest_beta = os.path.join(dest_dir, "beta", "index.html")
                    os.makedirs(os.path.dirname(dest_beta), exist_ok=True)
                    try:
                        os.chmod(os.path.dirname(dest_beta), 0o755)
                    except Exception:
                        pass
                    shutil.copy2(beta_html_path, dest_beta)
                    try:
                        os.chmod(dest_beta, 0o644)
                    except Exception:
                        pass
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully copied beta to public_html: {dest_beta}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Notice on copy to {dest_path}: {e}")
    else:
        print(f"Warning: {output_html_path} not found. Please provide an index.html template.")

    # 4.5. Export daily county party CSV for diffing and email notifications
    try:
        c_party = p_df.groupby('county').agg(
            dem=('dem', 'sum'),
            rep=('rep', 'sum'),
            una=('una', 'sum'),
            tot=('tot', 'sum')
        ).reset_index()
        c_party.columns = ['County', 'Democrat (2026)', 'Republican (2026)', 'Unaffiliated (2026)', 'Total 2026']
        st_row = pd.DataFrame([{
            'County': 'STATEWIDE TOTAL',
            'Democrat (2026)': int(c_party['Democrat (2026)'].sum()),
            'Republican (2026)': int(c_party['Republican (2026)'].sum()),
            'Unaffiliated (2026)': int(c_party['Unaffiliated (2026)'].sum()),
            'Total 2026': int(c_party['Total 2026'].sum())
        }])
        c_party = pd.concat([c_party, st_row], ignore_index=True)
        csv_name = f"nc_early_voting_party_ev_day_{ev_day}.csv"
        c_party.to_csv(csv_name, index=False)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Exported daily county party breakdown: {csv_name}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Notice: Could not export daily party CSV: {e}")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Statewide 2026 Total: {st_tot:,} votes (Dem: {st_dem:,}, Rep: {st_rep:,}, Una: {st_una:,})")

def main():
    parser = argparse.ArgumentParser(description="NC Early Voting Server-Side Updater")
    parser.add_argument("--force", action="store_true", help="Force update even if S3 file is unchanged")
    parser.add_argument("--ev-day", type=int, default=None, help="Target EV day override")
    parser.add_argument("--html-path", default="index.html", help="Path to local index.html")
    parser.add_argument("--dest-path", default=os.getenv("DEST_HTML_PATH", ""), help="Target path to publish interactive_map.html (optional)")
    parser.add_argument("--base-json", default="nc_map_base.json", help="Path to base map JSON")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(script_dir, "absentee_2026.zip")
    meta_path = os.path.join(script_dir, ".absentee_2026.meta.json")
    base_json_path = os.path.join(script_dir, args.base_json)
    html_path = os.path.join(script_dir, args.html_path)

    if not os.path.exists(base_json_path):
        print(f"Error: {base_json_path} not found.")
        sys.exit(1)

    try:
        has_update, downloaded_zip = check_for_updates(zip_path, meta_path, force=args.force)
    except Exception as e:
        print(f"Update check failed: {e}")
        sys.exit(1)

    if not has_update and not args.force:
        print("Everything is up to date.")
        sys.exit(0)

    # Load lookup from base JSON
    with open(base_json_path, 'r') as f:
        base_data = json.load(f)
    shp_lookup = base_data.get('precinct_lookup', {})

    p_df, ev_day = process_2026_returns(zip_path, shp_lookup, target_ev_day=args.ev_day)
    if p_df is not None:
        update_map_files(p_df, ev_day, base_json_path, html_path, dest_public_html=args.dest_path)
        print("Server update completed successfully!")

if __name__ == "__main__":
    main()
