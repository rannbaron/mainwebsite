"""
Durham, NC Local Government Official Rosters & ASR Entity Normalizer.
Covers:
  1. Durham Public Schools (DPS) Board of Education
  2. Durham City Council
  3. Durham Board of County Commissioners (BOCC)

Provides canonical names, titles, districts, tenures, and phonetic/ASR alias mappings
to ensure meeting transcripts and executive summaries never corrupt or misspell official names.
"""

import re
from typing import Dict, List, Optional, Tuple

# ==============================================================================
# OFFICIAL ROSTERS
# ==============================================================================

# Durham Public Schools Board of Education
DPS_BOARD_MEMBERS = {
    # Current (Sworn in July 2026 - Present)
    "joy_harrell_goff": {
        "canonical_name": "Joy Harrell-Goff",
        "title": "Chair",
        "body": "Durham Public Schools Board of Education",
        "district": "At-Large",
        "active_terms": ["2022-2026 (Vice Chair)", "2026-present (Chair)"],
        "aliases": ["joy harrell-goff", "joy harrell goff", "joy goff", "harrell goff", "herald goff", "miss herald goff", "mrs herald goff", "ms goff", "harrell-goff"]
    },
    "xavier_cason": {
        "canonical_name": "Xavier Cason",
        "title": "Vice Chair",
        "body": "Durham Public Schools Board of Education",
        "district": "District 4",
        "active_terms": ["2026-present"],
        "aliases": ["xavier cason", "mr cason", "cason", "zavier cason"]
    },
    "natalie_bent_kitaif": {
        "canonical_name": "Natalie Bent Kitaif",
        "title": "Board Member",
        "body": "Durham Public Schools Board of Education",
        "district": "District 1",
        "active_terms": ["2026-present"],
        "aliases": ["natalie bent kitaif", "natalie kitaif", "natalie bent", "bent kitaif", "ms kitaif"]
    },
    "nadeen_bir": {
        "canonical_name": "Nadeen Bir",
        "title": "Board Member",
        "body": "Durham Public Schools Board of Education",
        "district": "District 2",
        "active_terms": ["2026-present"],
        "aliases": ["nadeen bir", "nadine bir", "ms bir", "nadeen"]
    },
    "gabby_rivero": {
        "canonical_name": "Gabrielle (Gabby) Rivero",
        "title": "Board Member",
        "body": "Durham Public Schools Board of Education",
        "district": "District 3",
        "active_terms": ["2026-present"],
        "aliases": ["gabrielle rivero", "gabby rivero", "gabrielle gabby rivero", "ms rivero", "rivero"]
    },
    "wendell_tabb": {
        "canonical_name": "Wendell Tabb",
        "title": "Board Member",
        "body": "Durham Public Schools Board of Education",
        "district": "Consolidated District A",
        "active_terms": ["2024-present"],
        "aliases": ["wendell tabb", "mr tabb", "tabb"]
    },
    "millicent_rogers": {
        "canonical_name": "Millicent Rogers",
        "title": "Board Member",
        "body": "Durham Public Schools Board of Education",
        "district": "Consolidated District B",
        "active_terms": ["2022-present"],
        "aliases": ["millicent rogers", "ms rogers", "millicent", "mrs rogers"]
    },
    "anthony_lewis": {
        "canonical_name": "Dr. Anthony S. Lewis",
        "title": "Superintendent & Secretary ex-officio",
        "body": "Durham Public Schools",
        "district": "District-wide",
        "active_terms": ["2024-present"],
        "aliases": ["dr anthony lewis", "dr anthony s lewis", "anthony lewis", "superintendent lewis", "dr lewis"]
    },

    # Preceding Members (Active May 2026 and earlier)
    "bettina_umstead": {
        "canonical_name": "Bettina Umstead",
        "title": "Former Chair",
        "body": "Durham Public Schools Board of Education",
        "district": "District 2",
        "active_terms": ["2020-2026 (Chair)"],
        "aliases": ["bettina umstead", "chair umstead", "ms umstead", "bettina"]
    },
    "emily_chavez": {
        "canonical_name": "Emily Chávez",
        "title": "Former Board Member",
        "body": "Durham Public Schools Board of Education",
        "district": "District 1",
        "active_terms": ["2022-2026"],
        "aliases": ["emily chavez", "emily chávez", "ms chavez", "miss chavez", "mrs chavez", "chavez", "millicent chavez"]
    },
    "natalie_beyer": {
        "canonical_name": "Natalie Beyer",
        "title": "Former Board Member",
        "body": "Durham Public Schools Board of Education",
        "district": "District 4",
        "active_terms": ["2010-2026"],
        "aliases": ["natalie beyer", "ms beyer", "mrs beyer", "beyer"]
    },
    "alexandra_valladares": {
        "canonical_name": "Alexandra Valladares",
        "title": "Former Board Member",
        "body": "Durham Public Schools Board of Education",
        "district": "At-Large",
        "active_terms": ["2020-2024"],
        "aliases": ["alexandra valladares", "ms valladares", "valladares"]
    },
    "jovonia_lewis": {
        "canonical_name": "Jovonia Lewis",
        "title": "Former Board Member",
        "body": "Durham Public Schools Board of Education",
        "district": "Consolidated District A",
        "active_terms": ["2020-2024"],
        "aliases": ["jovonia lewis", "ms lewis", "mrs lewis"]
    }
}

# Durham City Council
DURHAM_CITY_COUNCIL = {
    "leonardo_williams": {
        "canonical_name": "Leonardo Williams",
        "title": "Mayor",
        "body": "Durham City Council",
        "district": "At-Large (Mayor)",
        "active_terms": ["2023-present"],
        "aliases": ["leonardo williams", "mayor williams", "mayor leo williams", "leo williams"]
    },
    "javiera_caballero": {
        "canonical_name": "Javiera Caballero",
        "title": "Mayor Pro Tempore",
        "body": "Durham City Council",
        "district": "At-Large",
        "active_terms": ["2018-present"],
        "aliases": ["javiera caballero", "mayor pro tem caballero", "ms caballero", "council member caballero"]
    },
    "nate_baker": {
        "canonical_name": "Nate Baker",
        "title": "Council Member",
        "body": "Durham City Council",
        "district": "At-Large",
        "active_terms": ["2023-present"],
        "aliases": ["nate baker", "nathaniel baker", "council member baker", "mr baker"]
    },
    "carl_rist": {
        "canonical_name": "Carl Rist",
        "title": "Council Member",
        "body": "Durham City Council",
        "district": "At-Large",
        "active_terms": ["2023-present"],
        "aliases": ["carl rist", "council member rist", "mr rist"]
    },
    "matt_kopac": {
        "canonical_name": "Matt Kopac",
        "title": "Council Member",
        "body": "Durham City Council",
        "district": "Ward 1",
        "active_terms": ["2025-present"],
        "aliases": ["matt kopac", "matthew kopac", "council member kopac", "mr kopac"]
    },
    "shanetta_burris": {
        "canonical_name": "Shanetta Burris",
        "title": "Council Member",
        "body": "Durham City Council",
        "district": "Ward 2",
        "active_terms": ["2025-present"],
        "aliases": ["shanetta burris", "council member burris", "ms burris"]
    },
    "chelsea_cook": {
        "canonical_name": "Chelsea Cook",
        "title": "Council Member",
        "body": "Durham City Council",
        "district": "Ward 3",
        "active_terms": ["2023-present"],
        "aliases": ["chelsea cook", "council member cook", "ms cook"]
    }
}

# Durham Board of County Commissioners (BOCC)
DURHAM_COUNTY_COMMISSIONERS = {
    "mike_lee": {
        "canonical_name": "Dr. Mike Lee",
        "title": "Chair",
        "body": "Durham Board of County Commissioners",
        "district": "County-wide",
        "active_terms": ["2024-present (Chair since Dec 2025)"],
        "aliases": ["dr mike lee", "mike lee", "commissioner lee", "chair lee", "michael lee"]
    },
    "nida_allam": {
        "canonical_name": "Nida Allam",
        "title": "Vice Chair",
        "body": "Durham Board of County Commissioners",
        "district": "County-wide",
        "active_terms": ["2020-present (Chair 2024-2025, Vice Chair 2025-present)"],
        "aliases": ["nida allam", "vice chair allam", "chair allam", "commissioner allam"]
    },
    "michelle_burton": {
        "canonical_name": "Michelle Burton",
        "title": "Commissioner",
        "body": "Durham Board of County Commissioners",
        "district": "County-wide",
        "active_terms": ["2024-present"],
        "aliases": ["michelle burton", "commissioner burton", "ms burton"]
    },
    "stephen_valentine": {
        "canonical_name": "Stephen Valentine",
        "title": "Commissioner",
        "body": "Durham Board of County Commissioners",
        "district": "County-wide",
        "active_terms": ["2024-present"],
        "aliases": ["stephen valentine", "commissioner valentine", "mr valentine", "steve valentine"]
    },
    "wendy_jacobs": {
        "canonical_name": "Wendy Jacobs",
        "title": "Commissioner",
        "body": "Durham Board of County Commissioners",
        "district": "County-wide",
        "active_terms": ["2012-present"],
        "aliases": ["wendy jacobs", "commissioner jacobs", "ms jacobs"]
    }
}

# Consolidated master dictionary
ALL_OFFICIALS = {**DPS_BOARD_MEMBERS, **DURHAM_CITY_COUNCIL, **DURHAM_COUNTY_COMMISSIONERS}


def normalize_official_name(text: str) -> Optional[Dict[str, str]]:
    """
    Given an ASR transcription string or query name, matches against known aliases
    and returns the canonical official metadata.
    """
    clean = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    
    # Exact and substring alias match
    for key, info in ALL_OFFICIALS.items():
        for alias in info["aliases"]:
            # word boundary match
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, clean):
                return info
    return None


def correct_transcript_names(text: str) -> str:
    """
    Scans a transcript text block and replaces known ASR corrupted names
    with their proper canonical titles and spellings.
    """
    corrections = [
        # Joy Harrell-Goff corrections (most common ASR corruption)
        (r"\b(?:Miss|Ms\.?|Mrs\.?)?\s*Herald\s+Goff\b", "Joy Harrell-Goff"),
        (r"\b(?:Miss|Ms\.?|Mrs\.?)?\s*Harrell\s+Goff\b", "Joy Harrell-Goff"),
        (r"\bMiss\s+Herald\s+Goff\b", "Vice Chair Joy Harrell-Goff"),
        
        # Emily Chávez corrections
        (r"\bMillicent\s+Chavez\b", "Emily Chávez"),
        (r"\bMiss\s+Chavez\b", "Emily Chávez"),
        (r"\bMs\.?\s+Chavez\b", "Emily Chávez"),
        (r"\bEmily\s+Chavez\b", "Emily Chávez"),

        # Bettina Umstead
        (r"\bChair\s+Umstead\b", "Chair Bettina Umstead"),
        (r"\bMiss\s+Umstead\b", "Bettina Umstead"),

        # Millicent Rogers
        (r"\bMiss\s+Rogers\b", "Millicent Rogers"),

        # Xavier Cason
        (r"\bZavier\s+Cason\b", "Xavier Cason"),

        # Mayor Leonardo Williams
        (r"\bMayor\s+Leo\s+Williams\b", "Mayor Leonardo Williams"),

        # Commissioner Dr. Mike Lee
        (r"\bCommissioner\s+Mike\s+Lee\b", "Chair Dr. Mike Lee"),
    ]

    corrected = text
    for pattern, replacement in corrections:
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    return corrected

