# North Carolina Early Voting Partisan & Demographic Swing Explorer

Interactive map exploring shifts in North Carolina early voting turnout across 2026, 2022, and 2018 at both the county and precinct levels.

## Features
- **Precinct-Level Zoom**: Click any county on the statewide map to zoom directly into precinct polygons.
- **Dynamic Comparisons**: Compare any pair of elections (2026 vs 2022, 2026 vs 2018, or 2022 vs 2018).
- **Party & Demographic Swings**:
  - Partisan swings: Dem vs Rep, Dem vs Una, Rep vs Una
  - Demographic shifts: White vs Black share
- **High-Contrast Double-Cased Vector Arrows**: Luminous directional swing vectors with customizable arrow thickness.
- **Automated Daily Updates**: Runs daily at 6:00 AM EDT via GitHub Actions to ingest official NCSBE returns.

## Data Sources
- **North Carolina State Board of Elections (NCSBE)** official absentee/early voting voter data files.
- Baseline 2018 and 2022 election precinct shapes and statistics.

