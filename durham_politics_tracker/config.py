"""
Configuration and settings for Durham Politics Tracker.
"""

import os
from pathlib import Path

# Paths (supports both local workspace and GitHub Actions runner)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "durham_politics.db"
_LOCAL_SITE_DIR = Path("/home/rann/src/website/mainwebsite/durhampolitics")
_REPO_SITE_DIR = BASE_DIR.parent / "durhampolitics"
OUTPUT_DIR = Path(
    os.environ.get(
        "DURHAM_OUTPUT_DIR",
        str(_REPO_SITE_DIR if (_REPO_SITE_DIR.exists() or (BASE_DIR.parent / ".github").exists()) else _LOCAL_SITE_DIR),
    )
)
HTML_OUTPUT_PATH = OUTPUT_DIR / "index.html"
DATA_EXPORT_PATH = OUTPUT_DIR / "durham_politics_data.json"
VIDEO_TOPICS_DIR = OUTPUT_DIR.parent / "video_topics"

# Password authentication
PAGE_PASSWORD = "durhampol"
MASTER_PASSWORD = "AS2cYGy9GD7qRt@XV&gf$yUX!pD@"

# Governing Bodies
BODIES = {
    "dps": {
        "id": "dps",
        "name": "Durham Public Schools Board of Education",
        "short_name": "DPS Board of Education",
        "acronym": "DPS",
        "badge_color": "#3b82f6",
        "text_color": "#93c5fd",
        "portal_url": "https://durhamnc.portal.civicclerk.com",
        "boarddocs_url": "https://go.boarddocs.com/nc/dpsnc/Board.nsf/Public",
        "youtube_channel": "https://www.youtube.com/@durhampublicschoolsboardof2290",
        "channel_id": "UC_dps_board_nc",
        "description": "Governs the public school system for Durham County, overseeing superintendent leadership, budget allocation, educational policy, and facilities.",
        "regular_schedule": "2nd & 4th Thursdays at 6:30 PM",
        "total_seats": 7
    },
    "city": {
        "id": "city",
        "name": "Durham City Council",
        "short_name": "City Council",
        "acronym": "City",
        "badge_color": "#10b981",
        "text_color": "#6ee7b7",
        "portal_url": "https://durhamnc.gov/1321/City-Council-Meetings",
        "granicus_url": "https://durhamnc.granicus.com",
        "legistar_url": "https://durhamnc.legistar.com",
        "youtube_channel": "https://www.youtube.com/@CityofDurhamNC",
        "channel_id": "UC_city_of_durham",
        "description": "The legislative body for the City of Durham, enacting city ordinances, setting tax rates, adopting the city budget, and directing urban development and municipal services.",
        "regular_schedule": "1st & 3rd Mondays at 7:00 PM (Work Sessions on Thursdays)",
        "total_seats": 7
    },
    "bocc": {
        "id": "bocc",
        "name": "Durham Board of County Commissioners",
        "short_name": "County Commissioners",
        "acronym": "BOCC",
        "badge_color": "#f59e0b",
        "text_color": "#fcd34d",
        "portal_url": "https://www.dconc.gov/county-departments/departments-a-e/board-of-commissioners/commissioners-meetings",
        "granicus_url": "https://durhamcounty.granicus.com",
        "legistar_url": "https://durhamcounty.legistar.com",
        "youtube_channel": "https://www.youtube.com/@DCoWebmaster",
        "channel_id": "UC_durham_county",
        "description": "The governing board of Durham County, managing county-wide services, public health, social services, property tax valuation, and local funding appropriations for DPS and Durham Tech.",
        "regular_schedule": "2nd & 4th Mondays at 7:00 PM",
        "total_seats": 5
    }
}

# Policy Issue Categories
ISSUE_CATEGORIES = [
    {"id": "budget_finance", "label": "Budget & Taxes", "color": "#10b981"},
    {"id": "staff_labor", "label": "Staff Compensation & Labor", "color": "#f59e0b"},
    {"id": "zoning_development", "label": "Zoning & Development (SCAD)", "color": "#8b5cf6"},
    {"id": "housing_equity", "label": "Affordable Housing", "color": "#ec4899"},
    {"id": "public_safety", "label": "Community Safety & HEART", "color": "#ef4444"},
    {"id": "school_facilities", "label": "School Facilities & Closures", "color": "#06b6d4"},
    {"id": "governance_transparency", "label": "Governance & Transparency", "color": "#3b82f6"},
    {"id": "transit_infrastructure", "label": "Transit & Public Works", "color": "#14b8a6"},
]
