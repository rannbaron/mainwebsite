#!/usr/bin/env python3
"""
North Carolina State Board of Elections (NCSBE) Bi-Weekly Automation Engine
Checks NCSBE official endpoints every two weeks for upcoming elections (General, Primaries,
Runoffs, Municipal, and Special elections), downloads the latest early voting sites and county
BOE data across all 100 NC counties, includes local races (county commissioners, school boards,
judges, municipal councils) and all three voting guides (Democratic, Republican, Independent),
and rebuilds the entire NC student voting platform.

Designed to run completely hands-free on GitLab CI/CD or GitHub Actions without requiring
a local computer to be online.
"""

import os
import sys
import json
import re
import datetime
import urllib.request
import urllib.parse
import subprocess
import time

MAIN_DIR = os.environ.get('CI_PROJECT_DIR') or os.environ.get('GITHUB_WORKSPACE') or os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(MAIN_DIR, '.nc_voting_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def fetch_url(url, retries=3, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode('utf-8', errors='replace')
        except Exception as e:
            if attempt == retries - 1:
                log(f"Error fetching {url}: {e}")
                return None
            time.sleep(2)

def detect_ncsbe_election():
    """
    Detects the active/upcoming election date and metadata from NCSBE.
    Checks vt.ncsbe.gov/OSSite/ and ncsbe.gov/voting/upcoming-election.
    """
    log("Step 1: Polling NCSBE for active and upcoming election cycles...")

    election_date = None
    election_title = None

    # 1. Query OSSite configured election date
    ossite_html = fetch_url('https://vt.ncsbe.gov/OSSite/')
    if ossite_html:
        m = re.search(r'electionDate:\s*[\'\"]([^\'\"]+)[\'\"]', ossite_html)
        if m:
            election_date = m.group(1).strip()
            log(f"Detected NCSBE configured election date from OSSite: {election_date}")

    # 2. Query upcoming election page for title & context
    upcoming_html = fetch_url('https://www.ncsbe.gov/voting/upcoming-election')
    if upcoming_html:
        # Check for title
        m_title = re.search(r'<h[12][^>]*>(?:North Carolina\s+)?(20\d{2}\s+[^<]+Election[^<]*)</h[12]>', upcoming_html, re.IGNORECASE)
        if m_title:
            election_title = m_title.group(1).strip()
            log(f"Detected NCSBE election title: {election_title}")

    # Fallback to current year election if none detected
    if not election_date:
        election_date = '11/03/2026'
        log("Defaulting to scheduled General Election: 11/03/2026")

    # Parse date components
    try:
        parts = [int(p) for p in election_date.split('/')]
        month, day, year = parts[0], parts[1], parts[2]
        dt_election = datetime.date(year, month, day)
    except Exception as e:
        log(f"Failed to parse election date {election_date}: {e}")
        dt_election = datetime.date(2026, 11, 3)

    # Determine election category
    is_primary = False
    is_municipal = False
    is_general = False

    if dt_election.month in [3, 4, 5, 6]:
        is_primary = True
        default_title = f"{dt_election.year} North Carolina Primary Election"
    elif dt_election.year % 2 == 1:
        is_municipal = True
        default_title = f"{dt_election.year} North Carolina Municipal Elections"
    else:
        is_general = True
        default_title = f"{dt_election.year} North Carolina General Election"

    if not election_title:
        election_title = default_title

    # Compute Early Voting Window under NC General Statutes:
    # Early voting starts on the third Thursday before Election Day
    # Early voting ends at 3:00 PM on the last Saturday before Election Day
    days_to_saturday = (dt_election.weekday() - 5) % 7
    if days_to_saturday == 0:
        days_to_saturday = 7
    ev_end_date = dt_election - datetime.timedelta(days=days_to_saturday)
    ev_start_date = ev_end_date - datetime.timedelta(days=16) # Thursday 2.5 weeks prior

    # Regular voter registration deadline: 25 days before Election Day
    reg_deadline = dt_election - datetime.timedelta(days=25)

    election_info = {
        'election_date': election_date,
        'election_date_iso': dt_election.isoformat(),
        'election_date_display': dt_election.strftime('%A, %B %-d, %Y'),
        'election_title': election_title,
        'election_year': dt_election.year,
        'is_primary': is_primary,
        'is_municipal': is_municipal,
        'is_general': is_general,
        'early_voting_start_display': ev_start_date.strftime('%A, %B %-d, %Y'),
        'early_voting_end_display': ev_end_date.strftime('%A, %B %-d, %Y'),
        'early_voting_cutoff_iso': f"{ev_end_date.isoformat()}T15:00:00-04:00",
        'reg_deadline_display': reg_deadline.strftime('%A, %B %-d, %Y'),
        'last_checked_ncsbe': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    info_path = os.path.join(CACHE_DIR, 'current_election.json')
    with open(info_path, 'w', encoding='utf-8') as f:
        json.dump(election_info, f, indent=2)
    log(f"Saved election configuration: {election_title} on {election_info['election_date_display']}")

    return election_info

def fetch_and_update_county_boe():
    """
    Refreshes official County Board of Elections contact info from NCSBE for all 100 counties.
    """
    log("Step 2: Fetching official 100-County Board of Elections directory from NCSBE...")
    boe_html = fetch_url('https://vt.ncsbe.gov/BOEInfo/')
    if not boe_html:
        log("Warning: Could not fetch BOEInfo from NCSBE, preserving existing cache.")
        return

    m = re.search(r'window\.boeinfoCountyData\s*=\s*(\[.*?\]);', boe_html, re.DOTALL)
    if m:
        counties = json.loads(m.group(1))
        boe_path = os.path.join(CACHE_DIR, 'county_boe_info.json')
        with open(boe_path, 'w', encoding='utf-8') as f:
            json.dump(counties, f, indent=2)
        log(f"Updated {len(counties)} County Boards of Elections in cache.")
        return counties
    else:
        log("Warning: Could not extract window.boeinfoCountyData from BOEInfo page.")
        return None

def fetch_and_update_early_voting_sites(election_info):
    """
    Refreshes early voting sites from NCSBE for all 100 counties for the active election cycle.
    """
    log(f"Step 3: Fetching early voting sites from NCSBE for {election_info['election_date']}...")

    boe_path = os.path.join(CACHE_DIR, 'county_boe_info.json')
    if not os.path.exists(boe_path):
        counties = fetch_and_update_county_boe()
    else:
        with open(boe_path, 'r', encoding='utf-8') as f:
            counties = json.load(f)

    if not counties:
        log("No county list available; skipping site fetch.")
        return

    encoded_date = urllib.parse.quote(election_info['election_date'], safe='')
    county_sites = {}
    sites_found_count = 0

    # Load existing sites as fallback
    sites_path = os.path.join(CACHE_DIR, 'county_early_voting_sites.json')
    existing_sites = {}
    if os.path.exists(sites_path):
        try:
            with open(sites_path, 'r', encoding='utf-8') as f:
                existing_sites = json.load(f)
        except Exception:
            existing_sites = {}

    for c in counties:
        cid = c['ID']
        cname = c['Name'].upper()
        url = f'https://vt.ncsbe.gov/OSSite?handler=Sites&countyId={cid}&electionDate={encoded_date}'

        try:
            raw = fetch_url(url, retries=2, timeout=10)
            if raw:
                data = json.loads(raw)
                sites = data.get('SiteList', [])
                if sites:
                    county_sites[cname] = sites
                    sites_found_count += len(sites)
                elif cname in existing_sites and existing_sites[cname]:
                    county_sites[cname] = existing_sites[cname]
                else:
                    county_sites[cname] = []
            elif cname in existing_sites:
                county_sites[cname] = existing_sites[cname]
        except Exception as e:
            if cname in existing_sites:
                county_sites[cname] = existing_sites[cname]

    with open(sites_path, 'w', encoding='utf-8') as f:
        json.dump(county_sites, f, indent=2)

    log(f"Successfully cached early voting sites for {len(county_sites)} counties (total {sites_found_count} sites updated).")

def run_platform_build():
    """
    Executes the full NC Student Voting platform build scripts.
    """
    log("Step 4: Rebuilding student voting guides, master directory, and dynamic QR portal...")

    # Run main build
    cmd_build = [sys.executable, os.path.join(MAIN_DIR, 'build_entire_nc_voting_system.py')]
    log(f"Running: {' '.join(cmd_build)}")
    res = subprocess.run(cmd_build, cwd=MAIN_DIR, capture_output=True, text=True)
    if res.returncode != 0:
        log(f"Build failed: {res.stderr}")
    else:
        log("Main platform build completed successfully.")

    # Run static Election Day pre-generator
    cmd_ed = [sys.executable, os.path.join(MAIN_DIR, 'generate_election_day_pages.py')]
    log(f"Running: {' '.join(cmd_ed)}")
    res_ed = subprocess.run(cmd_ed, cwd=MAIN_DIR, capture_output=True, text=True)
    if res_ed.returncode != 0:
        log(f"Election Day pre-generator failed: {res_ed.stderr}")
    else:
        log("Election Day static pre-generator completed successfully.")

def git_commit_and_push_if_changed(election_info):
    """
    If running in a CI environment (GitLab CI or GitHub Actions) or invoked with --push,
    commits and pushes changes back to the repository.
    """
    is_gitlab = os.environ.get('GITLAB_CI') == 'true'
    is_github = os.environ.get('GITHUB_ACTIONS') == 'true'
    has_push_flag = '--push' in sys.argv

    if not (is_gitlab or is_github or has_push_flag):
        log("Not running in CI and --push not specified. Skipping git push.")
        return

    log("Step 5: Checking for git repository modifications...")
    status_res = subprocess.run(['git', 'status', '--porcelain'], cwd=MAIN_DIR, capture_output=True, text=True)
    changes = status_res.stdout.strip()

    if not changes:
        log("No changes detected in repository. Everything is up to date with NCSBE.")
        return

    log(f"Changes detected:\n{changes[:500]}...")

    # Configure git
    subprocess.run(['git', 'config', 'user.name', 'NCSBE Automation Bot'], cwd=MAIN_DIR)
    subprocess.run(['git', 'config', 'user.email', 'ncsbe-bot@rannbar-on.com'], cwd=MAIN_DIR)

    subprocess.run(['git', 'add', '-A'], cwd=MAIN_DIR)
    commit_msg = (
        f"Bi-weekly NCSBE update: Refreshed for {election_info['election_title']} "
        f"({election_info['election_date']}) with local races, voting sites, and 3-guide balance [skip ci]"
    )
    subprocess.run(['git', 'commit', '-m', commit_msg], cwd=MAIN_DIR)

    # Push to remote
    log("Pushing updates to remote...")
    if is_gitlab:
        # Push using GitLab project token or CI credentials
        token = os.environ.get('GITLAB_TOKEN') or os.environ.get('CI_JOB_TOKEN')
        host = os.environ.get('CI_SERVER_HOST', 'gitlab.com')
        project_path = os.environ.get('CI_PROJECT_PATH')
        branch = os.environ.get('CI_COMMIT_REF_NAME', 'main')

        if token and project_path:
            remote_url = f"https://oauth2:{token}@{host}/{project_path}.git"
            push_res = subprocess.run(['git', 'push', remote_url, f'HEAD:{branch}'], cwd=MAIN_DIR, capture_output=True, text=True)
            if push_res.returncode == 0:
                log("Successfully pushed changes to GitLab repository!")
            else:
                log(f"Git push failed: {push_res.stderr}")
        else:
            subprocess.run(['git', 'push'], cwd=MAIN_DIR)
    else:
        # Standard git push (GitHub Actions or local)
        push_res = subprocess.run(['git', 'push'], cwd=MAIN_DIR, capture_output=True, text=True)
        if push_res.returncode == 0:
            log("Successfully pushed changes to repository!")
        else:
            log(f"Git push output: {push_res.stderr or push_res.stdout}")

def main():
    log("==================================================================")
    log("Starting NCSBE Bi-Weekly Automated Election & Voting Guide Check")
    log("==================================================================")

    # 1. Detect election
    election_info = detect_ncsbe_election()

    # 2. Update County BOE Info
    fetch_and_update_county_boe()

    # 3. Update Early Voting Sites
    fetch_and_update_early_voting_sites(election_info)

    # 4. Rebuild Platform
    run_platform_build()

    # 5. Git Commit & Push
    git_commit_and_push_if_changed(election_info)

    log("==================================================================")
    log("NCSBE Bi-Weekly Automation Check Completed Successfully!")
    log("==================================================================")

if __name__ == '__main__':
    main()
