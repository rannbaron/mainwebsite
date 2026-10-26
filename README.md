# North Carolina Student Voting Platform

An open-source, lightweight, accessible statewide voting directory providing tailored early voting and Election Day guides for students across all 110 higher education institutions in North Carolina.

Public web portal: [rannbar-on.com/vote](https://rannbar-on.com/vote)  
Full campus directory: [rannbar-on.com/campuses](https://rannbar-on.com/campuses)  
Usage analytics: [rannbar-on.com/stats](https://rannbar-on.com/stats)  
Bug tracker & issues: [github.com/rannbaron/mainwebsite/issues](https://github.com/rannbaron/mainwebsite/issues)

---

## Overview

College students face unique voting requirements in North Carolina, from photo ID approval lists to residential proof for same-day registration and strict rules governing private-school housing rosters.

This platform provides fast, mobile-friendly guides tailored to each student's specific campus and county jurisdiction:
- **16 UNC System Universities**
- **36 Independent Colleges and Universities**
- **58 North Carolina Community Colleges**

The platform operates without heavy client-side frameworks or external CSS CDNs, ensuring sub-second load times on mobile devices.

---

## Key Features

1. **Dual-Mode Static Architecture**
   - **Early Voting Mode:** Displays comprehensive early voting hours, primary on-campus or nearest off-campus polling locations, Google Maps directions, same-day registration instructions, and county-wide early voting locations.
   - **Election Day Mode:** Automatically activated after early voting closes (or built via `python3 build.py --eday`). Opens with Election Day polling hours (6:30 a.m. to 7:30 p.m.), assigned precinct polling places, distance from campus, and provisional ballot information.

2. **Compliance with NC Election Law**
   - **Photo ID Verification (N.C.G.S. § 163-166.16):** Distinguishes between institutions with state-approved student IDs and those requiring alternative IDs. Highlights the mandatory physical plastic card requirement (digital wallet IDs are not accepted under state law).
   - **Private School Roster Rule (NCSBE Numbered Memo 2023-05):** For private institutions (e.g. Duke, Wake Forest, Elon, Davidson), explicitly states that students relying on the campus housing roster for proof of residence must present their approved physical student photo ID, which cannot be paired with an out-of-state driver's license or passport.
   - **Commuter vs Residential:** Commuter community colleges are freed of dorm roster text and clearly directed to standard proof of residence (NC driver's license, utility bill, bank statement, paycheck).

3. **Balanced Voter Resources**
   - Every guide provides three non-partisan and party voter guides:
     - **Non-partisan:** Vote411 (League of Women Voters)
     - **Democratic:** Blue Voter Guide (NC) & County Democratic Party
     - **Republican:** iVoterGuide (NC) & County Republican Party

4. **Interactive Civic Tools**
   - **Smart QR Code Portal (`/vote`):** Dynamic QR code that points to the visitor's campus. Visitors can select their campus from a dropdown, use on-click browser geolocation, or enter an NC ZIP code.
   - **On-Click Distance Calculation:** Students can click a single button to find the closest voting site or polling precinct based on device GPS.
   - **Privacy-Preserving Telemetry:** Usage is tracked via cookie-free, privacy-friendly GoatCounter analytics (`/stats`).

---

## Repository Structure

```
├── data/
│   ├── campuses.json           # Institution metadata, coords, ID approvals, transit/entrance details
│   ├── county_boe.json         # 100-County Board of Elections contacts and websites
│   ├── county_sites.json       # Early voting sites and official hours for all 100 NC counties
│   ├── county_precincts.json   # Election Day polling precincts across all 100 counties
│   ├── campus_precincts.json   # Nearest geolocated precincts for all 110 campuses
│   └── campus_geo.json         # Campus GPS coordinates
├── build.py                    # Static generator compiling all 110 campus pages, /campuses, /vote, /stats
├── check_and_update_ncsbe_elections.py # Bi-weekly automation polling NCSBE endpoints
├── style.css                   # Lightweight civic CSS (light background, system font, left-aligned)
├── voting.js                   # Vanilla interaction script (geolocation, search, QR portal, support modal)
├── tracker.js                  # Privacy-preserving analytics script
├── LICENSE                     # MIT License
└── .prettierrc                 # Formatting configuration
```

---

## Building the Site

Requirements: Python 3.8+ with standard library. No external package dependencies required.

### 1. Build Early Voting Guides
```bash
python3 build.py
```
This reads from `data/` and generates all 110 campus guides (`<campus>vote.html`), `campuses.html`, `vote.html`, `stats.html`, and `standrewsvote.html`.

### 2. Build Election Day Guides
```bash
python3 build.py --eday
```
Generates Election Day versions of all pages, prioritizing assigned polling places and precinct lookups.

### 3. Bi-Weekly NCSBE Automated Check
```bash
python3 check_and_update_ncsbe_elections.py
```
Polls official North Carolina State Board of Elections endpoints, refreshes county datasets in `data/`, detects upcoming election schedules, and rebuilds the platform.

---

## Contributing and Bug Reports

Suggestions, corrections to polling hours, transit routes, or campus details are welcome. Please open an issue on the public GitHub issue tracker:
[https://github.com/rannbaron/mainwebsite/issues](https://github.com/rannbaron/mainwebsite/issues)

---

## License

This project is licensed under the [MIT License](LICENSE). Maintained by Rann Bar-On as an open-source public service.
