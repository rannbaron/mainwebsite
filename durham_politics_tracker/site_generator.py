"""
Static Site Generator for Durham Politics Tracker.
Produces the interactive single-page application at:
/home/rann/src/website/mainwebsite/durhampolitics/index.html
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .config import (
    HTML_OUTPUT_PATH, DATA_EXPORT_PATH, PAGE_PASSWORD, MASTER_PASSWORD,
    BODIES, ISSUE_CATEGORIES
)
from .database import DurhamPoliticsDB


def _is_blanket_consent_vote(v: Dict[str, Any]) -> bool:
    title = (v.get("item_title") or "").lower()
    mtype = (v.get("motion_type") or "").lower()
    notes = (v.get("notes") or "").lower()
    combined = f"{title} {mtype} {notes}"
    is_pulled = bool(
        re.search(r"pulled\s+(consent\s+)?item", title, re.I)
        or re.search(r"pulled\s+and\s+approved", notes, re.I)
        or re.search(r"pulled\s+for\s+(separate|discussion)", notes, re.I)
        or re.search(r"^approval of pulled", title, re.I)
        or re.search(r"^approve pulled", title, re.I)
    )
    if is_pulled:
        return False
    return any(
        k in combined
        for k in (
            "consent agenda",
            "settle the agenda",
            "settle agenda",
            "settlement of the agenda",
            "settle and adopt meeting agenda",
        )
    )


def _real_vote_names(arr: Any) -> List[str]:
    out = []
    for x in (arr or []):
        s = str(x or "").strip()
        if s and not re.match(r"^(none|n/a|na|0|null|-)$", s, re.I):
            out.append(s)
    return out


def _is_generic_unanimous_ayes(v: Dict[str, Any]) -> bool:
    nays = _real_vote_names(v.get("nays"))
    abst = _real_vote_names(v.get("abstentions"))
    if nays or abst:
        return False
    ayes = _real_vote_names(v.get("ayes"))
    if not ayes:
        return True
    if re.search(r"unanimous|7-0|6-0-0|5-0-0|5-0", str(v.get("tally") or ""), re.I):
        return True
    return any(
        re.search(
            r"all\s+(present|members|commissioners|council|board)|board\s+members|unanimous|supporting|and\s+others|^\d+\s+commissioners|^council\s+members$",
            x.strip(),
            re.I,
        )
        for x in ayes
    )


def _member_matches_list(name_list: List[str], member: Dict[str, Any]) -> bool:
    clean_name = re.sub(r"\([^)]*\)", "", re.sub(r"^Dr\.?\s+", "", member.get("name", ""), flags=re.I))
    clean_name = re.sub(r"\s+", " ", clean_name).strip().lower()
    parts = [p for p in clean_name.split(" ") if p]
    last = parts[-1] if parts else ""
    aliases = [str(a).lower().strip() for a in (member.get("aliases") or []) if a]
    for raw in _real_vote_names(name_list):
        nl = raw.lower()
        if clean_name and clean_name in nl:
            return True
        if len(last) >= 4 and last in nl:
            return True
        for a in aliases:
            if len(a) >= 4:
                if a in nl:
                    return True
            elif len(a) >= 3 and re.search(r"\b" + re.escape(a) + r"\b", nl):
                return True
    return False


def _compute_scope_stats(
    meetings: List[Dict[str, Any]],
    scope_members: List[Dict[str, Any]],
    cohorts_by_id: Dict[str, Dict[str, Any]],
    include_consent: bool,
) -> Dict[str, Any]:
    total_votes = 0
    contested_votes = 0
    total_disagreements = 0

    mem_stats: Dict[str, Dict[str, Any]] = {}
    for m in scope_members:
        mem_stats[m["id"]] = {
            "votes_cast": 0, "ayes": 0, "nays": 0, "abstains": 0,
            "aye_pct": 0.0, "nay_pct": 0.0, "dissent_rate": 0.0, "dissents_count": 0,
        }

    pair_agree: Dict[str, Dict[str, int]] = {}
    pair_total: Dict[str, Dict[str, int]] = {}

    for mtg in meetings:
        total_disagreements += len(mtg.get("disagreements") or [])
        vis_votes = [
            v for v in (mtg.get("votes") or [])
            if include_consent or not _is_blanket_consent_vote(v)
        ]
        total_votes += len(vis_votes)
        contested_votes += sum(1 for v in vis_votes if v.get("is_contested"))

        # Determine exact seated member IDs for this meeting's cohort
        c_obj = cohorts_by_id.get(mtg.get("cohort_id") or "")
        seated_ids: Set[str] = set(c_obj.get("member_ids", [])) if c_obj else {m["id"] for m in scope_members if m.get("is_current")}
        cand_members = [m for m in scope_members if m["id"] in seated_ids] if seated_ids else scope_members

        for v in vis_votes:
            outcome_passed = "pass" in str(v.get("outcome") or "").lower()
            generic_ayes = outcome_passed and _is_generic_unanimous_ayes(v)
            cast_by_id: Dict[str, str] = {}
            for mem in cand_members:
                mid = mem["id"]
                if _member_matches_list(v.get("nays") or [], mem):
                    mem_stats[mid]["nays"] += 1
                    mem_stats[mid]["votes_cast"] += 1
                    if outcome_passed:
                        mem_stats[mid]["dissents_count"] += 1
                    cast_by_id[mid] = "NAY"
                elif _member_matches_list(v.get("abstentions") or [], mem):
                    mem_stats[mid]["abstains"] += 1
                    mem_stats[mid]["votes_cast"] += 1
                    cast_by_id[mid] = "ABSTAIN"
                elif _member_matches_list(v.get("ayes") or [], mem) or (generic_ayes and mid in seated_ids):
                    mem_stats[mid]["ayes"] += 1
                    mem_stats[mid]["votes_cast"] += 1
                    cast_by_id[mid] = "AYE"

            ids = list(cast_by_id.keys())
            for i in range(len(ids)):
                id1 = ids[i]
                for j in range(i + 1, len(ids)):
                    id2 = ids[j]
                    pair_total.setdefault(id1, {})[id2] = pair_total.get(id1, {}).get(id2, 0) + 1
                    pair_total.setdefault(id2, {})[id1] = pair_total.get(id2, {}).get(id1, 0) + 1
                    if cast_by_id[id1] == cast_by_id[id2]:
                        pair_agree.setdefault(id1, {})[id2] = pair_agree.get(id1, {}).get(id2, 0) + 1
                        pair_agree.setdefault(id2, {})[id1] = pair_agree.get(id2, {}).get(id1, 0) + 1

    for mid, st in mem_stats.items():
        vc = st["votes_cast"]
        if vc > 0:
            st["aye_pct"] = round((st["ayes"] / vc) * 100.0, 1)
            st["nay_pct"] = round((st["nays"] / vc) * 100.0, 1)
            st["dissent_rate"] = round((st["dissents_count"] / vc) * 100.0, 1)

    pairwise: Dict[str, Dict[str, Optional[float]]] = {}
    for m1 in scope_members:
        id1 = m1["id"]
        pairwise[id1] = {}
        for m2 in scope_members:
            id2 = m2["id"]
            if id1 == id2:
                pairwise[id1][id2] = 100.0
            else:
                tot = pair_total.get(id1, {}).get(id2, 0)
                if tot == 0:
                    pairwise[id1][id2] = None
                else:
                    agr = pair_agree.get(id1, {}).get(id2, 0)
                    pairwise[id1][id2] = round((agr / tot) * 100.0, 1)

    unanimous = total_votes - contested_votes
    return {
        "meetings_count": len(meetings),
        "votes_count": total_votes,
        "contested_votes": contested_votes,
        "unanimous_votes": unanimous,
        "unanimous_pct": round((unanimous / max(total_votes, 1)) * 100.0, 1) if total_votes > 0 else 100.0,
        "disagreements_count": total_disagreements,
        "members": mem_stats,
        "pairwise": pairwise,
    }


def _build_multi_cohort_payload(dataset: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    """
    Writes per-cohort lazy-loaded JSON files under <out_dir>/data/ and returns
    a fast, compact APP_DATA payload with the 3 current boards embedded inline
    and precomputed stats for every board + historical cohort.
    """
    data_dir = out_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    all_meetings: List[Dict[str, Any]] = dataset.get("meetings", [])
    all_members: List[Dict[str, Any]] = dataset.get("stats", {}).get("members", [])
    cohorts_by_body: Dict[str, List[Dict[str, Any]]] = dataset.get("cohorts") or {}

    # Fallback synthesis if DB has no cohorts yet
    for b in BODIES.keys():
        if not cohorts_by_body.get(b):
            cur_mems = [m for m in all_members if m["body_id"] == b and m.get("is_current")]
            cohorts_by_body[b] = [{
                "id": f"{b}_current",
                "body_id": b,
                "label": f"Current {BODIES[b]['short_name']}",
                "short_label": "Current Board",
                "start_date": "2024-01-01",
                "end_date": None,
                "is_current": True,
                "sort_order": 1,
                "transition_reason": "Current seated board",
                "meeting_count": sum(1 for m in all_meetings if m["body_id"] == b),
                "member_ids": [m["id"] for m in cur_mems],
                "members": [{"member_id": m["id"], "role": m["title"], "district": m["district"]} for m in cur_mems],
            }]

    cohorts_by_id: Dict[str, Dict[str, Any]] = {}
    current_cohort_ids: Dict[str, str] = {}
    for b, clist in cohorts_by_body.items():
        for c in clist:
            cohorts_by_id[c["id"]] = c
            if c.get("is_current") and b not in current_cohort_ids:
                current_cohort_ids[b] = c["id"]
        if b not in current_cohort_ids and clist:
            current_cohort_ids[b] = clist[0]["id"]

    # Group meetings by cohort_id
    meetings_by_cohort: Dict[str, List[Dict[str, Any]]] = {cid: [] for cid in cohorts_by_id.keys()}
    for m in all_meetings:
        cid = m.get("cohort_id")
        if not cid or cid not in cohorts_by_id:
            cid = current_cohort_ids.get(m["body_id"])
            m["cohort_id"] = cid
        if cid:
            meetings_by_cohort.setdefault(cid, []).append(m)

    # Update exact meeting counts on cohort metadata and write lazy JSON shard per cohort
    for cid, mlist in meetings_by_cohort.items():
        mlist.sort(key=lambda x: (x.get("date") or "", x.get("id") or ""), reverse=True)
        if cid in cohorts_by_id:
            cohorts_by_id[cid]["meeting_count"] = len(mlist)
        shard_path = data_dir / f"meetings_{cid}.json"
        shard_path.write_text(json.dumps(mlist, ensure_ascii=False), encoding="utf-8")

    # Write lightweight global search index across ALL meetings (2012-2026)
    search_index = []
    years_set: Set[str] = set()
    for m in all_meetings:
        yr = str(m.get("date") or "")[:4]
        if yr.isdigit():
            years_set.add(yr)
        search_index.append({
            "id": m["id"],
            "body_id": m["body_id"],
            "cohort_id": m.get("cohort_id"),
            "date": m.get("date", ""),
            "year": yr,
            "title": m.get("title", ""),
            "chair": m.get("presiding_chair", ""),
            "summary": (m.get("executive_summary") or "")[:320],
            "votes": [v.get("item_title", "") for v in (m.get("votes") or [])],
            "debates": [d.get("issue", "") for d in (m.get("disagreements") or [])],
            "has_contested": any(v.get("is_contested") for v in (m.get("votes") or [])),
        })
    (data_dir / "search_index.json").write_text(json.dumps(search_index, ensure_ascii=False), encoding="utf-8")

    # Precompute cohort_stats & overall_stats for BOTH excl_consent & incl_consent
    members_by_id = {m["id"]: m for m in all_members}
    cohort_stats: Dict[str, Dict[str, Any]] = {"excl": {}, "incl": {}}
    overall_stats: Dict[str, Dict[str, Any]] = {}

    for mode_key, incl_flag in (("excl", False), ("incl", True)):
        tot_m = len(all_meetings)
        tot_v = 0
        tot_c = 0
        tot_d = 0
        for b, clist in cohorts_by_body.items():
            b_meetings = [m for m in all_meetings if m["body_id"] == b]
            b_members = [m for m in all_members if m["body_id"] == b]
            all_b_st = _compute_scope_stats(b_meetings, b_members, cohorts_by_id, incl_flag)
            cohort_stats[mode_key][f"all_{b}"] = all_b_st
            tot_v += all_b_st["votes_count"]
            tot_c += all_b_st["contested_votes"]
            tot_d += all_b_st["disagreements_count"]

            for c in clist:
                cid = c["id"]
                c_mems = [members_by_id[mid] for mid in c.get("member_ids", []) if mid in members_by_id]
                cohort_stats[mode_key][cid] = _compute_scope_stats(
                    meetings_by_cohort.get(cid, []), c_mems, cohorts_by_id, incl_flag
                )

        unanim = tot_v - tot_c
        overall_stats[mode_key] = {
            "total_meetings": tot_m,
            "total_votes": tot_v,
            "contested_votes": tot_c,
            "unanimous_votes": unanim,
            "unanimous_pct": round((unanim / max(tot_v, 1)) * 100.0, 1) if tot_v > 0 else 100.0,
            "total_disagreements": tot_d,
            "last_updated": dataset.get("stats", {}).get("overall", {}).get("last_updated", ""),
        }

    # Embed the 3 CURRENT board cohorts directly for instant first paint!
    # Also embed all cohorts inline ONLY if total serialized meetings size is small (< 2.5 MB)
    embedded_meetings_by_cohort: Dict[str, List[Dict[str, Any]]] = {}
    for b, cid in current_cohort_ids.items():
        embedded_meetings_by_cohort[cid] = meetings_by_cohort.get(cid, [])

    full_size_est = len(json.dumps(all_meetings, ensure_ascii=False))
    all_embedded = False
    if full_size_est < 2_500_000:
        embedded_meetings_by_cohort = meetings_by_cohort
        all_embedded = True

    meta = dict(dataset.get("metadata") or {})
    meta["years"] = sorted(years_set, reverse=True)
    meta["current_cohorts"] = current_cohort_ids
    meta["all_embedded"] = all_embedded
    meta["total_cohorts"] = sum(len(v) for v in cohorts_by_body.values())

    return {
        "metadata": meta,
        "cohorts": cohorts_by_body,
        "members": all_members,
        "overall_stats": overall_stats,
        "cohort_stats": cohort_stats,
        "meetings_by_cohort": embedded_meetings_by_cohort,
    }


def generate_durhampolitics_page(db: Optional[DurhamPoliticsDB] = None) -> str:
    """
    Extracts the full database state and renders the standalone interactive
    password-protected HTML application with multi-cohort historical support
    (defaulting to Current Boards with lazy-loaded prior cohort archives).
    """
    if db is None:
        db = DurhamPoliticsDB(read_only=True)

    dataset = db.export_full_dataset()

    # Ensure output directory exists
    HTML_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    app_payload = _build_multi_cohort_payload(dataset, HTML_OUTPUT_PATH.parent)
    data_json = json.dumps(app_payload, ensure_ascii=False)

    # Save lightweight summary export JSON (always well under GitHub's 100 MB limit)
    with open(DATA_EXPORT_PATH, "w", encoding="utf-8") as f:
        f.write(data_json)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Durham Politics Tracker | Confidential Deliberation & Voting Intelligence</title>
  
  <!-- Strict Privacy & Anti-Search Indexing Control -->
  <meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
  <meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet">
  <meta name="bingbot" content="noindex, nofollow, noarchive, nosnippet">

  <style>
    :root {{
      --bg-dark: #090d16;
      --bg-sidebar: #0f172a;
      --card-bg: #111827;
      --card-inner: #1a2234;
      --card-border: #1f2937;
      --border-focus: #3b82f6;
      --text-main: #f9fafb;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --accent-blue: #3b82f6;
      --accent-green: #10b981;
      --accent-amber: #f59e0b;
      --accent-red: #ef4444;
      --accent-purple: #8b5cf6;
      --accent-cyan: #06b6d4;
      --dps-color: #3b82f6;
      --city-color: #10b981;
      --bocc-color: #f59e0b;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg-dark);
      color: var(--text-main);
      line-height: 1.5;
      min-height: 100vh;
      overflow-x: hidden;
    }}

    /* Password Protection Screen Overlay */
    #authOverlay {{
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: radial-gradient(circle at center, #1e1b4b 0%, #090d16 100%);
      z-index: 99999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}

    .auth-card {{
      background: var(--card-bg);
      border: 1px solid #312e81;
      border-radius: 12px;
      max-width: 440px;
      width: 100%;
      padding: 32px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
      text-align: center;
    }}

    .auth-badge {{
      display: inline-block;
      background: rgba(239, 68, 68, 0.2);
      border: 1px solid #ef4444;
      color: #fca5a5;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      padding: 4px 10px;
      border-radius: 9999px;
      margin-bottom: 16px;
    }}

    .auth-title {{
      font-size: 22px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 8px;
    }}

    .auth-desc {{
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 24px;
    }}

    .auth-form {{
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .auth-input {{
      background: var(--card-inner);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px 16px;
      color: #fff;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }}

    .auth-input:focus {{
      border-color: var(--accent-blue);
    }}

    .auth-btn {{
      background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
      color: #fff;
      font-weight: 600;
      border: none;
      border-radius: 8px;
      padding: 12px;
      cursor: pointer;
      transition: transform 0.1s, opacity 0.2s;
    }}

    .auth-btn:hover {{
      opacity: 0.95;
    }}

    .auth-btn:active {{
      transform: scale(0.98);
    }}

    .auth-error {{
      color: #f87171;
      font-size: 12px;
      margin-top: 6px;
      display: none;
    }}

    /* Main App Layout */
    #appWrapper {{
      display: none;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    /* Header */
    header {{
      background: rgba(15, 23, 42, 0.95);
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 100;
    }}

    .header-inner {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }}

    .brand-group {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}

    .brand-logo {{
      width: 38px;
      height: 38px;
      background: linear-gradient(135deg, #2563eb, #7c3aed);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 900;
      font-size: 18px;
      color: #fff;
    }}

    .brand-text h1 {{
      font-size: 17px;
      font-weight: 800;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .brand-text p {{
      font-size: 11px;
      color: var(--text-muted);
    }}

    .badge-confidential {{
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: #fca5a5;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .search-box {{
      position: relative;
      width: 280px;
    }}

    .search-input {{
      width: 100%;
      background: var(--card-inner);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 8px 12px 8px 32px;
      color: #fff;
      font-size: 13px;
      outline: none;
    }}

    .search-icon {{
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-dim);
      font-size: 14px;
    }}

    .btn-lock {{
      background: #1e293b;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: background 0.2s;
    }}

    .btn-lock:hover {{
      background: #334155;
      color: #fff;
    }}

    /* Navigation Bar */
    nav.nav-tabs {{
      background: #0b1120;
      border-bottom: 1px solid var(--card-border);
    }}

    .nav-inner {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 0 24px;
      display: flex;
      gap: 4px;
      overflow-x: auto;
      scrollbar-width: none;
    }}

    .tab-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 12px 16px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 2px solid transparent;
      white-space: nowrap;
      transition: color 0.2s, border-color 0.2s;
    }}

    .tab-btn:hover {{
      color: #fff;
    }}

    .tab-btn.active {{
      color: #fff;
      border-bottom-color: var(--accent-blue);
    }}

    .tab-pill {{
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 9999px;
      background: #1e293b;
      color: var(--text-muted);
    }}

    .tab-btn.active .tab-pill {{
      background: rgba(59, 130, 246, 0.2);
      color: #93c5fd;
    }}

    /* Main Container */
    main.container {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px;
      flex: 1;
      width: 100%;
    }}

    /* Tab Content Panes */
    .tab-pane {{
      display: none;
    }}

    .tab-pane.active {{
      display: block;
      animation: fadeIn 0.2s ease-in-out;
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(4px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* KPI Summary Cards */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 18px;
      position: relative;
      overflow: hidden;
    }}

    .kpi-card::before {{
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      background: var(--accent-blue);
    }}

    .kpi-card.kpi-dps::before {{ background: var(--dps-color); }}
    .kpi-card.kpi-city::before {{ background: var(--city-color); }}
    .kpi-card.kpi-bocc::before {{ background: var(--bocc-color); }}

    .kpi-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-dim);
      margin-bottom: 6px;
    }}

    .kpi-value {{
      font-size: 28px;
      font-weight: 800;
      color: #fff;
      line-height: 1;
      margin-bottom: 6px;
    }}

    .kpi-subtext {{
      font-size: 12px;
      color: var(--text-muted);
    }}

    /* Cards & Section Containers */
    .section-title {{
      font-size: 18px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
    }}

    /* Body Badge */
    .badge-body {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .badge-body.dps {{
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #93c5fd;
    }}

    .badge-body.city {{
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #6ee7b7;
    }}

    .badge-body.bocc {{
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.3);
      color: #fcd34d;
    }}

    /* Member Cards Grid */
    .members-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
      margin-top: 16px;
    }}

    .member-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.15s, border-color 0.15s;
    }}

    .member-card:hover {{
      transform: translateY(-2px);
      border-color: #334155;
    }}

    .member-header {{
      display: flex;
      align-items: flex-start;
      gap: 14px;
      margin-bottom: 12px;
    }}

    .member-avatar {{
      width: 48px;
      height: 48px;
      border-radius: 10px;
      background: #1e293b;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 16px;
      color: #fff;
      flex-shrink: 0;
    }}

    .member-info h3 {{
      font-size: 16px;
      font-weight: 700;
      color: #fff;
    }}

    .member-info p {{
      font-size: 12px;
      color: var(--text-muted);
    }}

    .member-stats {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 8px;
      background: var(--card-inner);
      border-radius: 8px;
      padding: 10px;
      margin: 12px 0;
      text-align: center;
    }}

    .stat-box-num {{
      font-size: 16px;
      font-weight: 800;
      color: #fff;
    }}

    .stat-box-lbl {{
      font-size: 10px;
      text-transform: uppercase;
      color: var(--text-dim);
    }}

    .tag-container {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }}

    .tag {{
      background: #1e293b;
      color: #cbd5e1;
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 4px;
    }}

    .tag-ideology {{
      background: rgba(139, 92, 246, 0.15);
      border: 1px solid rgba(139, 92, 246, 0.3);
      color: #c4b5fd;
    }}

    .btn-view-record {{
      background: #1e293b;
      border: 1px solid var(--card-border);
      color: #fff;
      font-size: 12px;
      font-weight: 600;
      border-radius: 6px;
      padding: 8px;
      width: 100%;
      margin-top: 14px;
      cursor: pointer;
      transition: background 0.2s;
    }}

    .btn-view-record:hover {{
      background: #334155;
    }}

    /* Meeting Timeline Feed */
    .timeline {{
      display: flex;
      flex-direction: column;
      gap: 16px;
      margin-top: 16px;
    }}

    .meeting-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      transition: border-color 0.2s;
    }}

    .meeting-card:hover {{
      border-color: #334155;
    }}

    .meeting-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 12px;
    }}

    .meeting-meta {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 12px;
      color: var(--text-dim);
    }}

    .meeting-title {{
      font-size: 16px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 6px;
    }}

    .meeting-summary {{
      font-size: 13px;
      color: var(--text-muted);
      line-height: 1.6;
      margin-bottom: 14px;
    }}

    /* Collapsible Sections inside Meeting */
    .meeting-details-toggle {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 10px;
      padding-top: 12px;
      border-top: 1px solid var(--card-inner);
    }}

    .btn-toggle-details {{
      background: #1e293b;
      border: 1px solid var(--card-border);
      color: #cbd5e1;
      font-size: 12px;
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}

    .btn-toggle-details:hover {{
      background: #334155;
      color: #fff;
    }}

    .details-pane {{
      display: none;
      margin-top: 14px;
      background: var(--card-inner);
      border-radius: 8px;
      padding: 16px;
      border: 1px solid #232d42;
    }}

    /* Votes list */
    .vote-item {{
      border-bottom: 1px solid #2a374f;
      padding-bottom: 12px;
      margin-bottom: 12px;
    }}

    .vote-item:last-child {{
      border-bottom: none;
      padding-bottom: 0;
      margin-bottom: 0;
    }}

    .vote-title {{
      font-size: 14px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 4px;
    }}

    .vote-badge-passed {{
      background: rgba(16, 185, 129, 0.2);
      color: #6ee7b7;
      border: 1px solid rgba(16, 185, 129, 0.4);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
    }}

    .vote-badge-failed {{
      background: rgba(239, 68, 68, 0.2);
      color: #fca5a5;
      border: 1px solid rgba(239, 68, 68, 0.4);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
    }}

    .vote-breakdown {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 6px;
    }}

    .disagreement-box {{
      background: #131b2e;
      border-left: 3px solid var(--accent-amber);
      border-radius: 0 8px 8px 0;
      padding: 14px;
      margin-bottom: 12px;
    }}

    .disagreement-box:last-child {{
      margin-bottom: 0;
    }}

    .dis-title {{
      font-size: 14px;
      font-weight: 700;
      color: #fcd34d;
      margin-bottom: 6px;
    }}

    .dis-side {{
      font-size: 12px;
      color: #e2e8f0;
      margin: 6px 0;
    }}

    /* Pairwise Heatmap Grid */
    .heatmap-wrapper {{
      overflow-x: auto;
      margin-top: 16px;
    }}

    .heatmap-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      text-align: center;
    }}

    .heatmap-table th, .heatmap-table td {{
      padding: 8px;
      border: 1px solid #1e293b;
    }}

    .heatmap-table th {{
      background: #0f172a;
      color: var(--text-muted);
      font-weight: 600;
      max-width: 110px;
      word-wrap: break-word;
    }}

    .heat-high {{ background: rgba(16, 185, 129, 0.25); color: #6ee7b7; font-weight: 700; }}
    .heat-med {{ background: rgba(245, 158, 11, 0.25); color: #fcd34d; }}
    .heat-low {{ background: rgba(239, 68, 68, 0.25); color: #fca5a5; font-weight: 700; }}
    .heat-self {{ background: #1e293b; color: var(--text-dim); }}

    /* Modal for Voting Record */
    #recordModal {{
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      z-index: 10000;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}

    .modal-content {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      max-width: 720px;
      width: 100%;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    .modal-header {{
      padding: 18px 24px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .modal-body {{
      padding: 24px;
      overflow-y: auto;
      flex: 1;
    }}

    .btn-close-modal {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 20px;
      cursor: pointer;
    }}

    /* Filter Controls Bar */
    .filter-bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 20px;
      align-items: center;
    }}

    .filter-select {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: #fff;
      font-size: 13px;
      border-radius: 8px;
      padding: 8px 12px;
      outline: none;
    }}

    .cohort-bar {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-top: 14px;
      padding: 12px 14px;
      background: var(--card-inner);
      border: 1px solid #23304c;
      border-radius: 10px;
    }}
    .cohort-bar-left {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .cohort-bar-label {{
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }}
    .cohort-meta-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      font-size: 12px;
      color: var(--text-muted);
    }}
    .cohort-pill {{
      background: rgba(59, 130, 246, 0.14);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #93c5fd;
      font-size: 11px;
      font-weight: 600;
      padding: 3px 9px;
      border-radius: 999px;
    }}
    .cohort-note {{
      margin-top: 8px;
      font-size: 12px;
      color: var(--text-dim);
    }}
    .btn-load-more {{
      display: block;
      margin: 18px auto 6px auto;
      background: #1e293b;
      border: 1px solid #334155;
      color: #e2e8f0;
      font-size: 13px;
      font-weight: 600;
      padding: 10px 22px;
      border-radius: 8px;
      cursor: pointer;
    }}
    .btn-load-more:hover {{
      background: #334155;
      color: #fff;
    }}

    /* Toast Notification */
    #toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #1e293b;
      border: 1px solid var(--accent-blue);
      color: #fff;
      font-size: 13px;
      padding: 12px 20px;
      border-radius: 8px;
      box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5);
      z-index: 999999;
      display: none;
    }}
  </style>
</head>
<body>

  <!-- ======================================================== -->
  <!-- PASSWORD PROTECTION GATEWAY                             -->
  <!-- ======================================================== -->
  <div id="authOverlay">
    <div class="auth-card">
      <div class="auth-badge">Confidential Document</div>
      <div class="auth-title">Durham Politics Tracker</div>
      <div class="auth-desc">Private research command center tracking DPS Board of Education, Durham City Council, and County Commissioners. Password protected.</div>
      
      <form class="auth-form" onsubmit="handleAuth(event)">
        <div style="text-align: left;">
          <label style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 4px;">Username</label>
          <input type="text" id="authUsernameInput" class="auth-input" placeholder="e.g. rann" autofocus required autocomplete="username" style="width: 100%;">
        </div>
        <div style="text-align: left;">
          <label style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 4px;">Password</label>
          <input type="password" id="authPasswordInput" class="auth-input" placeholder="Enter Password" required autocomplete="current-password" style="width: 100%;">
        </div>
        <label style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-muted); cursor: pointer; text-align: left;">
          <input type="checkbox" id="rememberAuthCheckbox" checked> Remember access on this browser
        </label>
        <button type="submit" class="auth-btn">Unlock Command Center &rarr;</button>
        <div id="authErrorMsg" class="auth-error">Invalid username or password. Please verify and retry.</div>
        <div style="margin-top: 12px; font-size: 12.5px; color: var(--text-muted); text-align: center;">
          Need an account? <a href="/durhampolitics/signup.html" style="color: #60a5fa; text-decoration: none; font-weight: 600;">Request Access &rarr;</a>
          &nbsp;&bull;&nbsp;
          <a href="/durhampolitics/docs.html" style="color: var(--text-muted); text-decoration: none;">Documentation</a>
        </div>
      </form>
    </div>
  </div>

  <!-- ======================================================== -->
  <!-- MAIN APPLICATION SHELL                                  -->
  <!-- ======================================================== -->
  <div id="appWrapper">
    <!-- Header -->
    <header>
      <div class="header-inner">
        <div class="brand-group">
          <div class="brand-logo">DP</div>
          <div class="brand-text">
            <h1>Durham Politics Tracker <span class="badge-confidential">Private Access</span></h1>
            <p id="headerCoverageSub">2012 – Nov 2026 Full Historical Archive &amp; Voting Intelligence | DPS, City Council &amp; BOCC</p>
          </div>
        </div>

        <div class="header-actions">
          <label style="display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--text-muted);cursor:pointer;background:rgba(15,23,42,0.65);border:1px solid var(--card-border);padding:6px 10px;border-radius:8px;white-space:nowrap;" title="Toggle blanket consent agenda votes in counts and lists (pulled items are always included)">
            <input type="checkbox" id="includeConsentAgendaToggle" onchange="toggleConsentAgenda(this.checked)" style="accent-color:#3b82f6;cursor:pointer;" />
            <span>Include Consent Agenda</span>
          </label>
          <div class="search-box">
            <span class="search-icon">&#128269;</span>
            <input type="text" id="globalSearchInput" class="search-input" placeholder="Search votes, topics, officials..." oninput="handleGlobalSearch(this.value)">
          </div>
          <a href="/durhampolitics/docs.html" style="display:inline-flex;align-items:center;gap:5px;padding:7px 12px;border-radius:8px;border:1px solid var(--card-border);background:rgba(15,23,42,0.65);color:var(--text-main);text-decoration:none;font-size:12px;font-weight:600;white-space:nowrap;" title="Site Documentation & Guide">
            <span>&#128214;</span> Docs
          </a>
        </div>
      </div>
    </header>

    <!-- Navigation Tabs -->
    <nav class="nav-tabs">
      <div class="nav-inner">
        <button class="tab-btn active" onclick="switchTab('overview')">
          <span>Overview & Macro Trends</span>
        </button>
        <button class="tab-btn" onclick="switchTab('dps')">
          <span>DPS School Board</span>
          <span class="tab-pill" id="pill_dps">7 Seats</span>
        </button>
        <button class="tab-btn" onclick="switchTab('city')">
          <span>City Council</span>
          <span class="tab-pill" id="pill_city">7 Seats</span>
        </button>
        <button class="tab-btn" onclick="switchTab('bocc')">
          <span>County Commissioners</span>
          <span class="tab-pill" id="pill_bocc">5 Seats</span>
        </button>
        <button class="tab-btn" onclick="switchTab('members')">
          <span>Member Directory</span>
          <span class="tab-pill" id="pill_members">22 Officials</span>
        </button>
        <button class="tab-btn" onclick="switchTab('alignments')">
          <span>Voting Alignments & Heatmaps</span>
        </button>
        <button class="tab-btn" onclick="switchTab('timeline')">
          <span>Meeting Archives & Video</span>
          <span class="tab-pill" id="pill_meetings">Timeline</span>
        </button>
        <button class="tab-btn" id="liveMeetingTabBtn" style="display:none; color:#fca5a5; border-bottom-color: transparent;" onclick="window.location.href='/durhampolitics/live.html'">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#ef4444;box-shadow:0 0 8px #ef4444;margin-right:4px;"></span>
          <span>Live Meeting in Progress</span>
          <span class="tab-pill" id="liveMeetingPill" style="background:rgba(239,68,68,0.25);color:#fca5a5;">LIVE</span>
        </button>
      </div>
    </nav>

    <!-- Main Content Container -->
    <main class="container">
      
      <!-- ================= TAB 1: OVERVIEW ================= -->
      <div id="tab_overview" class="tab-pane active">
        <!-- KPI Cards -->
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">Tracked Meetings</div>
            <div class="kpi-value" id="kpiTotalMeetings">0</div>
            <div class="kpi-subtext" id="kpiMeetingsSubtext">Full historical archive across 3 boards</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Recorded Formal Votes</div>
            <div class="kpi-value" id="kpiTotalVotes">0</div>
            <div class="kpi-subtext" id="kpiUnanimousPct">0% Unanimous Consensual</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Contested Roll Calls</div>
            <div class="kpi-value" id="kpiContestedVotes">0</div>
            <div class="kpi-subtext">Divided roll calls & dissents</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Deliberation Issues</div>
            <div class="kpi-value" id="kpiTotalDisagreements">0</div>
            <div class="kpi-subtext">Sources of substantive debate</div>
          </div>
        </div>

        <!-- Cross-Body Summary Cards -->
        <div class="section-title">Major Governance Fault Lines & Running Alignments</div>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px;">
          <!-- DPS Summary -->
          <div class="card" style="border-top: 3px solid var(--dps-color);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <span class="badge-body dps">Durham Public Schools</span>
              <span style="font-size: 12px; color: var(--text-dim);">Chaired by Joy Harrell-Goff</span>
            </div>
            <h3 style="font-size: 15px; margin-bottom: 8px;">Labor Stability, Fiscal Oversight & Facility Preservation</h3>
            <p style="font-size: 13px; color: var(--text-muted); line-height: 1.6; margin-bottom: 12px;">
              Key tensions center on classified staff salary schedules and meet-and-confer frameworks with the Durham Association of Educators (DAE). Under Policy 8600, strict quarterly budget reporting was instituted. Board resisted outside consultant recommendations to consolidate/close elementary schools.
            </p>
            <div style="font-size: 12px; background: var(--card-inner); padding: 10px; border-radius: 6px;">
              <strong>Key Faction Dynamic:</strong> Labor-allied progressives (Bir, Rogers, Rivero, Chávez) partnering with collaborative leadership (Harrell-Goff, Cason) to prioritize workforce retention.
            </div>
          </div>

          <!-- City Council Summary -->
          <div class="card" style="border-top: 3px solid var(--city-color);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <span class="badge-body city">Durham City Council</span>
              <span style="font-size: 12px; color: var(--text-dim);">Mayor Leonardo Williams</span>
            </div>
            <h3 style="font-size: 15px; margin-bottom: 8px;">Density Urbanism (SCAD) vs Neighborhood Preservation</h3>
            <p style="font-size: 13px; color: var(--text-muted); line-height: 1.6; margin-bottom: 12px;">
              Persistent 4-3 and 5-2 ideological split on development rezonings and the SCAD housing code. Williams, Caballero, and Kopac advocate market supply abundance; Baker and Cook dissent frequently demanding deep binding affordability and environmental buffers. Universal support for HEART non-police crisis expansion.
            </p>
            <div style="font-size: 12px; background: var(--card-inner); padding: 10px; border-radius: 6px;">
              <strong>Key Faction Dynamic:</strong> Pro-growth urbanists (Williams, Caballero, Kopac, Rist) vs Planning integrity/tenant defense progressives (Baker, Cook, Burris).
            </div>
          </div>

          <!-- BOCC Summary -->
          <div class="card" style="border-top: 3px solid var(--bocc-color);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <span class="badge-body bocc">County Commissioners</span>
              <span style="font-size: 12px; color: var(--text-dim);">Chaired by Dr. Mike Lee</span>
            </div>
            <h3 style="font-size: 15px; margin-bottom: 8px;">Education Funding, Property Revaluation & Regional Transit</h3>
            <p style="font-size: 13px; color: var(--text-muted); line-height: 1.6; margin-bottom: 12px;">
              Steered major supplemental funding ($27M) to stabilize DPS classified salaries. Unanimous on dedicating county-owned downtown parcels (300 E. Main) to 100% affordable housing. High cohesion with isolated dissents on suburban property tax rate adjustments. Smooth leadership rotation from Allam to Lee in Dec 2025.
            </p>
            <div style="font-size: 12px; background: var(--card-inner); padding: 10px; border-radius: 6px;">
              <strong>Key Faction Dynamic:</strong> High consensus body (Lee, Allam, Burton, Jacobs, Valentine) prioritizing countywide human services, public health, and transit right-of-way.
            </div>
          </div>
        </div>

        <!-- Latest High-Impact Motions -->
        <div class="section-title" style="margin-top: 24px;">Recent Landmark Votes</div>
        <div id="overviewLandmarkVotes" class="timeline"></div>
      </div>

      <!-- ================= TAB 2: DPS ================= -->
      <div id="tab_dps" class="tab-pane">
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
            <h2 style="font-size: 20px; font-weight: 800; color: #fff;">Durham Public Schools Board of Education</h2>
            <span class="badge-body dps">7 Total Seats</span>
          </div>
          <p style="font-size: 14px; color: var(--text-muted); line-height: 1.6;">
            Oversees Durham County's K-12 public school system, serving over 32,000 students across 56 schools. Defaults to the <strong>Current Board</strong> (seated July 6, 2026); select any prior seating cohort below to inspect historical rosters, voting records, and meeting archives back to 2016.
          </p>
          <div class="cohort-bar">
            <div class="cohort-bar-left">
              <span class="cohort-bar-label">Board Cohort:</span>
              <select id="cohortSelect_dps" class="filter-select" onchange="onBoardCohortChange('dps', this.value)"></select>
            </div>
            <div id="cohortMeta_dps" class="cohort-meta-pills"></div>
          </div>
          <div id="cohortNote_dps" class="cohort-note"></div>
        </div>
        <div class="section-title" id="dpsMembersTitle">DPS Board Members</div>
        <div id="dpsMembersGrid" class="members-grid"></div>

        <div class="section-title" style="margin-top: 32px;" id="dpsMeetingsTitle">DPS Meeting Chronology &amp; Roll Calls</div>
        <div id="dpsMeetingsTimeline" class="timeline"></div>
      </div>

      <!-- ================= TAB 3: CITY COUNCIL ================= -->
      <div id="tab_city" class="tab-pane">
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
            <h2 style="font-size: 20px; font-weight: 800; color: #fff;">Durham City Council</h2>
            <span class="badge-body city">7 Total Seats (Mayor + 6 Council Members)</span>
          </div>
          <p style="font-size: 14px; color: var(--text-muted); line-height: 1.6;">
            The legislative and policy-making body of the City of Durham. Defaults to the <strong>Current Council</strong> (seated Dec 1, 2025); select any prior council cohort below to inspect historical rosters, voting records, and meeting archives back to 2012.
          </p>
          <div class="cohort-bar">
            <div class="cohort-bar-left">
              <span class="cohort-bar-label">Board Cohort:</span>
              <select id="cohortSelect_city" class="filter-select" onchange="onBoardCohortChange('city', this.value)"></select>
            </div>
            <div id="cohortMeta_city" class="cohort-meta-pills"></div>
          </div>
          <div id="cohortNote_city" class="cohort-note"></div>
        </div>
        <div class="section-title" id="cityMembersTitle">City Council Members</div>
        <div id="cityMembersGrid" class="members-grid"></div>

        <div class="section-title" style="margin-top: 32px;" id="cityMeetingsTitle">City Council Meeting Chronology &amp; Roll Calls</div>
        <div id="cityMeetingsTimeline" class="timeline"></div>
      </div>

      <!-- ================= TAB 4: BOCC ================= -->
      <div id="tab_bocc" class="tab-pane">
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
            <h2 style="font-size: 20px; font-weight: 800; color: #fff;">Durham Board of County Commissioners (BOCC)</h2>
            <span class="badge-body bocc">5 County-wide Seats</span>
          </div>
          <p style="font-size: 14px; color: var(--text-muted); line-height: 1.6;">
            The governing body of Durham County. Defaults to the <strong>Current Board</strong> (seated Dec 2, 2024; chaired by Dr. Mike Lee since Dec 2025); select any prior BOCC cohort below to inspect historical rosters, voting records, and meeting archives back to 2012.
          </p>
          <div class="cohort-bar">
            <div class="cohort-bar-left">
              <span class="cohort-bar-label">Board Cohort:</span>
              <select id="cohortSelect_bocc" class="filter-select" onchange="onBoardCohortChange('bocc', this.value)"></select>
            </div>
            <div id="cohortMeta_bocc" class="cohort-meta-pills"></div>
          </div>
          <div id="cohortNote_bocc" class="cohort-note"></div>
        </div>
        <div class="section-title" id="boccMembersTitle">County Commissioners</div>
        <div id="boccMembersGrid" class="members-grid"></div>

        <div class="section-title" style="margin-top: 32px;" id="boccMeetingsTitle">BOCC Meeting Chronology &amp; Roll Calls</div>
        <div id="boccMeetingsTimeline" class="timeline"></div>
      </div>

      <!-- ================= TAB 5: MEMBERS ================= -->
      <div id="tab_members" class="tab-pane">
        <div class="filter-bar">
          <select id="memberFilterBody" class="filter-select" onchange="onMemberBodyFilterChange()">
            <option value="all">All Governing Bodies</option>
            <option value="dps">DPS School Board</option>
            <option value="city">Durham City Council</option>
            <option value="bocc">County Commissioners (BOCC)</option>
          </select>
          <select id="memberFilterCohort" class="filter-select" onchange="renderMembers()" style="display:none;">
            <option value="all">All Cohorts</option>
          </select>
          <select id="memberFilterStatus" class="filter-select" onchange="renderMembers()">
            <option value="current">Current Serving Officials</option>
            <option value="all">All Officials (2012–2026)</option>
            <option value="former">Former / Preceding Members Only</option>
          </select>
        </div>
        <div id="allMembersGrid" class="members-grid"></div>
      </div>

      <!-- ================= TAB 6: ALIGNMENTS ================= -->
      <div id="tab_alignments" class="tab-pane">
        <div class="card">
          <h2 style="font-size: 18px; font-weight: 800; color: #fff; margin-bottom: 8px;">Pairwise Voting Agreement Heatmap</h2>
          <p style="font-size: 13px; color: var(--text-muted); line-height: 1.5; margin-bottom: 16px;">
            Calculates the percentage of recorded votes where two seated members voted identically when both were present. Green cells indicate voting agreement &ge; 95%; yellow indicates 90&ndash;94.9%; red indicates &lt; 90%. Defaults to the Current Board; switch cohorts to analyze any prior board composition.
          </p>
          <div class="filter-bar">
            <select id="alignmentBodySelect" class="filter-select" onchange="onAlignmentBodyChange(this.value)">
              <option value="city">Durham City Council</option>
              <option value="dps">DPS Board of Education</option>
              <option value="bocc">Durham County Commissioners (BOCC)</option>
            </select>
            <select id="alignmentCohortSelect" class="filter-select" onchange="renderPairwiseHeatmap()"></select>
          </div>
          <div id="alignmentCohortNote" style="font-size: 12px; color: var(--text-dim); margin-bottom: 10px;"></div>
          <div id="heatmapContainer" class="heatmap-wrapper"></div>
        </div>

        <div class="card" style="margin-top: 20px;">
          <h3 id="dissentLeaderboardTitle" style="font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 8px;">Dissent Frequency Leaderboard</h3>
          <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 14px;">
            Officials in the selected board &amp; cohort who cast the highest proportion of dissenting votes (NAY against a carried majority motion) out of all recorded votes:
          </p>
          <div id="dissentLeaderboard"></div>
        </div>
      </div>

      <!-- ================= TAB 7: TIMELINE ================= -->
      <div id="tab_timeline" class="tab-pane">
        <div class="filter-bar">
          <select id="timelineFilterBody" class="filter-select" onchange="onTimelineBodyChange()">
            <option value="all">All Governing Bodies</option>
            <option value="dps">DPS School Board</option>
            <option value="city">City Council</option>
            <option value="bocc">County Commissioners</option>
          </select>
          <select id="timelineFilterCohort" class="filter-select" onchange="renderTimeline()">
            <option value="current">Current Boards (Default)</option>
            <option value="all">All Historical Boards (2012–2026)</option>
          </select>
          <select id="timelineFilterYear" class="filter-select" onchange="renderTimeline()">
            <option value="all">All Years</option>
          </select>
          <select id="timelineFilterContested" class="filter-select" onchange="renderTimeline()">
            <option value="all">All Recorded Sessions</option>
            <option value="contested">Contested Roll Calls Only</option>
          </select>
        </div>
        <div id="timelineStatusNote" style="font-size: 12px; color: var(--text-dim); margin-bottom: 10px;"></div>
        <div id="masterTimelineList" class="timeline"></div>
      </div>

    </main>
  </div>

  <!-- ======================================================== -->
  <!-- VOTING RECORD MODAL                                     -->
  <!-- ======================================================== -->
  <div id="recordModal">
    <div class="modal-content">
      <div class="modal-header">
        <div id="modalMemberTitle" style="font-weight: 800; font-size: 18px; color: #fff;"></div>
        <button class="btn-close-modal" onclick="closeRecordModal()">&times;</button>
      </div>
      <div id="modalMemberBody" class="modal-body"></div>
    </div>
  </div>

  <!-- Toast notification -->
  <div id="toast"></div>

  <!-- ======================================================== -->
  <!-- CLIENT DATA & APPLICATION LOGIC                          -->
  <!-- ======================================================== -->
  <script>
    const APP_DATA = {data_json};
    const VALID_PASSWORDS = ["{PAGE_PASSWORD}", "{MASTER_PASSWORD}"];

    // ----------------------------------------------------
    // Authentication & Privacy Control
    // ----------------------------------------------------
    const SHARED_ACTIVE_KEY = "rann_auth_last_active";
    const INACTIVITY_TIMEOUT_MS = 60 * 60 * 1000; // 1 hour idle timeout
    let lastActiveMem = Date.now();

    function touchActivity() {{
      lastActiveMem = Date.now();
      try {{ localStorage.setItem(SHARED_ACTIVE_KEY, lastActiveMem.toString()); }} catch(e) {{}}
    }}

    function getLastActive() {{
      try {{
        const stored = parseInt(localStorage.getItem(SHARED_ACTIVE_KEY) || "0", 10);
        return Math.max(stored || 0, lastActiveMem);
      }} catch(e) {{
        return lastActiveMem;
      }}
    }}

    let lastThrottle = 0;
    ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'].forEach(ev => {{
      window.addEventListener(ev, () => {{
        const now = Date.now();
        if (now - lastThrottle > 2000) {{
          lastThrottle = now;
          touchActivity();
        }}
      }}, {{ passive: true }});
    }});

    setInterval(() => {{
      const now = Date.now();
      const isAuthed = sessionStorage.getItem("rann_session_active") || sessionStorage.getItem("durham_pol_auth");
      if (isAuthed && (now - getLastActive() > INACTIVITY_TIMEOUT_MS)) {{
        lockApp("Session timed out after 1 hour of idle time.");
      }}
    }}, 5000);

    function checkAuth() {{
      const sessionAuth = sessionStorage.getItem("rann_session_active") || sessionStorage.getItem("durham_pol_auth");
      const lastActive = getLastActive();
      const now = Date.now();
      
      if (sessionAuth && (now - lastActive <= INACTIVITY_TIMEOUT_MS)) {{
        touchActivity();
        unlockApp();
      }} else {{
        sessionStorage.removeItem("rann_session_active");
        sessionStorage.removeItem("durham_pol_auth");
        document.getElementById("authOverlay").style.display = "flex";
        document.getElementById("appWrapper").style.display = "none";
      }}
    }}

    async function sha256Hex(str) {{
      const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
      return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
    }}

    async function verifyApprovedDurhamUser(identifier, password) {{
      try {{
        const res = await fetch("/durhampolitics/approved_users.json?t=" + Date.now(), {{ cache: "no-store" }});
        if (!res.ok) return null;
        const data = await res.json();
        const users = (data && data.users) || [];
        const idLow = identifier.toLowerCase();
        const match = users.find(u =>
          u.status === "APPROVED" &&
          (u.allowed_pages || []).includes("/durhampolitics") &&
          ((u.username || "").toLowerCase() === idLow || (u.email || "").toLowerCase() === idLow)
        );
        if (!match || !match.salt || !match.password_hash) return null;
        const computed = await sha256Hex(match.salt + ":" + password);
        return computed === match.password_hash ? match : null;
      }} catch (e) {{
        return null;
      }}
    }}

    async function handleAuth(e) {{
      e.preventDefault();
      const user = (document.getElementById("authUsernameInput") ? document.getElementById("authUsernameInput").value.trim().toLowerCase() : "");
      const pwd = document.getElementById("authPasswordInput").value.trim();

      if (user === "rann" && pwd === "{MASTER_PASSWORD}") {{
        sessionStorage.setItem("rann_session_active", "valid");
        sessionStorage.setItem("durham_pol_auth", "granted");
        touchActivity();
        unlockApp();
        return;
      }}
      if (user === "durhampol" && pwd === "{PAGE_PASSWORD}") {{
        sessionStorage.setItem("durham_pol_auth", "granted");
        try {{
          localStorage.setItem("rann_auth_user", JSON.stringify({{
            username: "durhampol", fullName: "Durham Politics Guest",
            privilegeLevel: 2, privilegeName: "Standard Member", allowedPages: ["/durhampolitics"]
          }}));
        }} catch(ex) {{}}
        touchActivity();
        unlockApp();
        return;
      }}

      const approved = await verifyApprovedDurhamUser(user, pwd);
      if (approved) {{
        // Strictly scope approved users to /durhampolitics/ ONLY (never grant master session)
        sessionStorage.removeItem("rann_session_active");
        sessionStorage.setItem("durham_pol_auth", "granted");
        try {{
          localStorage.setItem("rann_auth_user", JSON.stringify({{
            username: approved.username,
            fullName: approved.full_name || approved.username,
            email: approved.email || "",
            privilegeLevel: 2,
            privilegeName: "Standard Member",
            allowedPages: ["/durhampolitics"]
          }}));
        }} catch(ex) {{}}
        touchActivity();
        unlockApp();
      }} else {{
        const err = document.getElementById("authErrorMsg");
        err.style.display = "block";
        err.innerText = "Invalid username/password, or account is still pending approval.";
        document.getElementById("authPasswordInput").focus();
      }}
    }}

    function unlockApp() {{
      document.getElementById("authOverlay").style.display = "none";
      document.getElementById("appWrapper").style.display = "flex";
      initApplication();
    }}

    function lockApp(reason) {{
      sessionStorage.removeItem("rann_session_active");
      sessionStorage.removeItem("durham_pol_auth");
      try {{ localStorage.removeItem("durham_pol_auth"); }} catch(e) {{}}
      document.getElementById("appWrapper").style.display = "none";
      document.getElementById("authOverlay").style.display = "flex";
      document.getElementById("authPasswordInput").value = "";
      document.getElementById("authErrorMsg").style.display = "none";
      showToast(reason || "🔒 Session timed out after 1 hour of idle time.");
    }}

    function showToast(msg) {{
      const t = document.getElementById("toast");
      t.innerText = msg;
      t.style.display = "block";
      setTimeout(() => {{ t.style.display = "none"; }}, 3000);
    }}

    // ----------------------------------------------------
    // Tab Navigation
    // ----------------------------------------------------
    function switchTab(tabId) {{
      const panes = document.querySelectorAll(".tab-pane");
      panes.forEach(p => p.classList.remove("active"));

      const btns = document.querySelectorAll(".tab-btn");
      btns.forEach(b => b.classList.remove("active"));

      const targetPane = document.getElementById(`tab_${{tabId}}`);
      if (targetPane) targetPane.classList.add("active");

      if (typeof event !== "undefined" && event && event.currentTarget) {{
        event.currentTarget.classList.add("active");
      }}

      if (tabId === "alignments") {{
        renderPairwiseHeatmap();
      }} else if (tabId === "timeline") {{
        renderTimeline();
      }}
    }}

    // ----------------------------------------------------
    // Multi-Cohort State, Lazy Loading & Consent Filtering
    // ----------------------------------------------------
    let includeConsentAgenda = false;
    const LOADED_MEETINGS_BY_COHORT = Object.assign({{}}, APP_DATA.meetings_by_cohort || {{}});
    const COHORT_FETCH_PROMISES = {{}};
    let SEARCH_INDEX_CACHE = null;

    const SELECTED_COHORT = {{
      dps: (APP_DATA.metadata.current_cohorts && APP_DATA.metadata.current_cohorts.dps) || (APP_DATA.cohorts.dps[0] && APP_DATA.cohorts.dps[0].id),
      city: (APP_DATA.metadata.current_cohorts && APP_DATA.metadata.current_cohorts.city) || (APP_DATA.cohorts.city[0] && APP_DATA.cohorts.city[0].id),
      bocc: (APP_DATA.metadata.current_cohorts && APP_DATA.metadata.current_cohorts.bocc) || (APP_DATA.cohorts.bocc[0] && APP_DATA.cohorts.bocc[0].id),
    }};

    const BOARD_NAMES = {{
      dps: "DPS Board of Education",
      city: "Durham City Council",
      bocc: "Durham County Commissioners (BOCC)"
    }};

    const MEMBERS_BY_ID = {{}};
    (APP_DATA.members || []).forEach(m => {{ MEMBERS_BY_ID[m.id] = m; }});

    const COHORTS_BY_ID = {{}};
    Object.keys(APP_DATA.cohorts || {{}}).forEach(b => {{
      (APP_DATA.cohorts[b] || []).forEach(c => {{ COHORTS_BY_ID[c.id] = c; }});
    }});

    function statsModeKey() {{
      return includeConsentAgenda ? "incl" : "excl";
    }}

    function isBlanketConsentAgendaVote(v) {{
      const title = (v.item_title || "").toLowerCase();
      const mtype = (v.motion_type || "").toLowerCase();
      const notes = (v.notes || "").toLowerCase();
      const combined = title + " " + mtype + " " + notes;
      const isPulled = (
        /pulled\\s+(consent\\s+)?item/i.test(title) ||
        /pulled\\s+and\\s+approved/i.test(notes) ||
        /pulled\\s+for\\s+(separate|discussion)/i.test(notes) ||
        /^approval of pulled/i.test(title) ||
        /^approve pulled/i.test(title)
      );
      if (isPulled) return false;
      return (
        combined.includes("consent agenda") ||
        combined.includes("settle the agenda") ||
        combined.includes("settle agenda") ||
        combined.includes("settlement of the agenda") ||
        combined.includes("settle and adopt meeting agenda")
      );
    }}

    function getVisibleVotes(votes) {{
      const arr = votes || [];
      return includeConsentAgenda ? arr : arr.filter(v => !isBlanketConsentAgendaVote(v));
    }}

    function realVoteNames(arr) {{
      return (arr || []).filter(x => x && !/^(none|n\\/a|na|0|null|-)$/i.test(String(x).trim()));
    }}

    function isGenericUnanimousAyes(v) {{
      const nays = realVoteNames(v.nays);
      const abst = realVoteNames(v.abstentions);
      if (nays.length > 0 || abst.length > 0) return false;
      const ayes = realVoteNames(v.ayes);
      if (ayes.length === 0) return true;
      if (/unanimous|7-0|6-0-0|5-0-0|5-0/i.test(v.tally || "")) return true;
      return ayes.some(x => /all\\s+(present|members|commissioners|council|board)|board\\s+members|unanimous|supporting|and\\s+others|^\\d+\\s+commissioners|^council\\s+members$/i.test(x.trim()));
    }}

    function memberMatchesVoteList(nameList, member) {{
      const cleanName = (member.name || "").replace(/^Dr\\.?\\s+/i, "").replace(/\\([^)]*\\)/g, "").replace(/\\s+/g, " ").trim().toLowerCase();
      const parts = cleanName.split(" ").filter(Boolean);
      const last = parts[parts.length - 1] || "";
      const aliases = (member.aliases || []).map(a => String(a || "").toLowerCase().trim()).filter(Boolean);
      return realVoteNames(nameList).some(n => {{
        const nl = n.toLowerCase();
        if (cleanName && nl.includes(cleanName)) return true;
        if (last.length >= 4 && nl.includes(last)) return true;
        return aliases.some(a => {{
          if (a.length >= 4) return nl.includes(a);
          if (a.length >= 3) return new RegExp(`\\\\b${{a.replace(/[.*+?^${{}}()|[\\]\\\\]/g, "\\\\$&")}}\\\\b`, "i").test(nl);
          return false;
        }});
      }});
    }}

    async function ensureCohortMeetingsLoaded(cohortId) {{
      if (!cohortId) return [];
      if (LOADED_MEETINGS_BY_COHORT[cohortId]) {{
        return LOADED_MEETINGS_BY_COHORT[cohortId];
      }}
      if (!COHORT_FETCH_PROMISES[cohortId]) {{
        COHORT_FETCH_PROMISES[cohortId] = fetch(`/durhampolitics/data/meetings_${{encodeURIComponent(cohortId)}}.json`)
          .then(res => (res.ok ? res.json() : []))
          .then(data => {{
            LOADED_MEETINGS_BY_COHORT[cohortId] = Array.isArray(data) ? data : [];
            return LOADED_MEETINGS_BY_COHORT[cohortId];
          }})
          .catch(() => {{
            LOADED_MEETINGS_BY_COHORT[cohortId] = [];
            return [];
          }});
      }}
      return COHORT_FETCH_PROMISES[cohortId];
    }}

    async function ensureManyCohortsLoaded(cohortIds) {{
      const lists = await Promise.all(cohortIds.map(cid => ensureCohortMeetingsLoaded(cid)));
      const merged = [];
      lists.forEach(arr => merged.push(...arr));
      merged.sort((a, b) => (b.date || "").localeCompare(a.date || "") || (b.id || "").localeCompare(a.id || ""));
      return merged;
    }}

    async function ensureSearchIndexLoaded() {{
      if (SEARCH_INDEX_CACHE) return SEARCH_INDEX_CACHE;
      try {{
        const res = await fetch("/durhampolitics/data/search_index.json");
        if (res.ok) {{
          SEARCH_INDEX_CACHE = await res.json();
          return SEARCH_INDEX_CACHE;
        }}
      }} catch (e) {{}}
      // Fallback to already-loaded meetings
      const fallback = [];
      Object.values(LOADED_MEETINGS_BY_COHORT).forEach(arr => {{
        arr.forEach(m => fallback.push({{
          id: m.id, body_id: m.body_id, cohort_id: m.cohort_id, date: m.date,
          year: (m.date || "").slice(0, 4), title: m.title || "", chair: m.presiding_chair || "",
          summary: (m.executive_summary || "").slice(0, 320),
          votes: (m.votes || []).map(v => v.item_title || ""),
          debates: (m.disagreements || []).map(d => d.issue || ""),
          has_contested: (m.votes || []).some(v => v.is_contested)
        }}));
      }});
      SEARCH_INDEX_CACHE = fallback;
      return SEARCH_INDEX_CACHE;
    }}

    function getMemberWithScopeStats(member, scopeKey, roleOverride, districtOverride) {{
      const mode = statsModeKey();
      const scope = (APP_DATA.cohort_stats && APP_DATA.cohort_stats[mode] && APP_DATA.cohort_stats[mode][scopeKey]) || null;
      const st = (scope && scope.members && scope.members[member.id]) || {{
        votes_cast: 0, ayes: 0, nays: 0, abstains: 0, aye_pct: 0.0, nay_pct: 0.0, dissent_rate: 0.0, dissents_count: 0
      }};
      return Object.assign({{}}, member, st, {{
        title: roleOverride || member.title,
        district: districtOverride || member.district,
        _scopeKey: scopeKey
      }});
    }}

    function toggleConsentAgenda(checked) {{
      includeConsentAgenda = !!checked;
      applyStatsKPIs();
      renderOverviewLandmarks();
      renderMembers();
      ["dps", "city", "bocc"].forEach(b => renderSingleBodyTab(b));
      renderPairwiseHeatmap();
      renderTimeline();
    }}

    // ----------------------------------------------------
    // Cohort Dropdown Builders (Defaulting to Current Board)
    // ----------------------------------------------------
    function populateBoardCohortDropdown(bodyId) {{
      const sel = document.getElementById(`cohortSelect_${{bodyId}}`);
      if (!sel) return;
      const cohorts = (APP_DATA.cohorts && APP_DATA.cohorts[bodyId]) || [];
      let html = "";
      cohorts.forEach(c => {{
        const tag = c.is_current ? " ★ Current" : "";
        html += `<option value="${{c.id}}">${{c.short_label}}${{tag}} (${{c.meeting_count || 0}} mtgs)</option>`;
      }});
      const totalBodyMtgs = cohorts.reduce((acc, c) => acc + (c.meeting_count || 0), 0);
      html += `<option value="all_${{bodyId}}">All Historical Boards (${{totalBodyMtgs}} mtgs)</option>`;
      sel.innerHTML = html;
      sel.value = SELECTED_COHORT[bodyId] || (cohorts[0] && cohorts[0].id) || `all_${{bodyId}}`;
    }}

    function populateAlignmentCohorts(bodyId) {{
      const sel = document.getElementById("alignmentCohortSelect");
      if (!sel) return;
      const cohorts = (APP_DATA.cohorts && APP_DATA.cohorts[bodyId]) || [];
      let html = "";
      cohorts.forEach(c => {{
        const tag = c.is_current ? " ★ Current" : "";
        html += `<option value="${{c.id}}">${{c.short_label}}${{tag}} (${{c.meeting_count || 0}} mtgs)</option>`;
      }});
      sel.innerHTML = html;
      const curId = (APP_DATA.metadata.current_cohorts && APP_DATA.metadata.current_cohorts[bodyId]) || (cohorts[0] && cohorts[0].id);
      if (curId) sel.value = curId;
    }}

    function populateTimelineControls() {{
      const yrSel = document.getElementById("timelineFilterYear");
      if (yrSel) {{
        const yrs = (APP_DATA.metadata && APP_DATA.metadata.years) || [];
        let yhtml = `<option value="all">All Years (${{yrs.length ? yrs[yrs.length - 1] + "–" + yrs[0] : "All"}})</option>`;
        yrs.forEach(y => {{ yhtml += `<option value="${{y}}">${{y}} Meetings</option>`; }});
        yrSel.innerHTML = yhtml;
      }}
      onTimelineBodyChange(true);
    }}

    function onTimelineBodyChange(skipRender) {{
      const bodyFilter = document.getElementById("timelineFilterBody").value;
      const cohSel = document.getElementById("timelineFilterCohort");
      if (!cohSel) return;
      let html = `<option value="current">Current Board${{bodyFilter === "all" ? "s" : ""}} (Default)</option>`;
      html += `<option value="all">All Historical Boards</option>`;
      if (bodyFilter !== "all") {{
        const cohorts = (APP_DATA.cohorts && APP_DATA.cohorts[bodyFilter]) || [];
        cohorts.forEach(c => {{
          html += `<option value="${{c.id}}">${{c.short_label}}${{c.is_current ? " ★ Current" : ""}} (${{c.meeting_count || 0}})</option>`;
        }});
      }}
      cohSel.innerHTML = html;
      cohSel.value = "current";
      if (!skipRender) renderTimeline();
    }}

    function onMemberBodyFilterChange() {{
      const bodyFilter = document.getElementById("memberFilterBody").value;
      const cohSel = document.getElementById("memberFilterCohort");
      if (bodyFilter === "all") {{
        cohSel.style.display = "none";
        cohSel.innerHTML = `<option value="all">All Cohorts</option>`;
      }} else {{
        const cohorts = (APP_DATA.cohorts && APP_DATA.cohorts[bodyFilter]) || [];
        let html = `<option value="all">All ${{BOARD_NAMES[bodyFilter]}} Cohorts</option>`;
        cohorts.forEach(c => {{
          html += `<option value="${{c.id}}">${{c.short_label}}${{c.is_current ? " ★ Current" : ""}}</option>`;
        }});
        cohSel.innerHTML = html;
        cohSel.style.display = "inline-block";
      }}
      renderMembers();
    }}

    // ----------------------------------------------------
    // App Initialization
    // ----------------------------------------------------
    function initApplication() {{
      const cov = (APP_DATA.metadata && APP_DATA.metadata.coverage) || "2012 – Nov 2026 & Ongoing";
      const hdrSub = document.getElementById("headerCoverageSub");
      if (hdrSub) hdrSub.innerText = `${{cov}} | DPS, City Council & BOCC`;
      const memPill = document.getElementById("pill_members");
      if (memPill) memPill.innerText = `${{(APP_DATA.members || []).length}} Officials`;
      const mtgPill = document.getElementById("pill_meetings");
      if (mtgPill) mtgPill.innerText = `${{APP_DATA.overall_stats.excl.total_meetings}} Mtgs`;

      ["dps", "city", "bocc"].forEach(b => populateBoardCohortDropdown(b));
      populateAlignmentCohorts(document.getElementById("alignmentBodySelect").value || "city");
      populateTimelineControls();

      applyStatsKPIs();
      renderOverviewLandmarks();
      renderMembers();
      ["dps", "city", "bocc"].forEach(b => renderSingleBodyTab(b));
      renderPairwiseHeatmap();
      renderTimeline();
      pollLiveMeetingStatus();
      setInterval(pollLiveMeetingStatus, 15000);
    }}

    async function pollLiveMeetingStatus() {{
      const btn = document.getElementById("liveMeetingTabBtn");
      const pill = document.getElementById("liveMeetingPill");
      if (!btn) return;
      try {{
        const res = await fetch("/durhampolitics/live_status.json?t=" + Date.now(), {{ cache: "no-store" }});
        if (!res.ok) {{
          btn.style.display = "none";
          return;
        }}
        const data = await res.json();
        if (data && data.is_live) {{
          btn.style.display = "inline-flex";
          const bAcronym = data.body_id === "dps" ? "DPS" : data.body_id === "city" ? "CITY" : data.body_id === "bocc" ? "BOCC" : "LIVE";
          if (pill) pill.innerText = "LIVE • " + bAcronym;
          btn.title = data.title || "Live Meeting in Progress";
        }} else {{
          btn.style.display = "none";
        }}
      }} catch (e) {{
        btn.style.display = "none";
      }}
    }}

    function applyStatsKPIs() {{
      const s = APP_DATA.overall_stats[statsModeKey()];
      document.getElementById("kpiTotalMeetings").innerText = s.total_meetings;
      document.getElementById("kpiTotalVotes").innerText = s.total_votes;
      document.getElementById("kpiContestedVotes").innerText = s.contested_votes;
      document.getElementById("kpiUnanimousPct").innerText = `${{s.unanimous_pct}}% Unanimous Consensus`;
      document.getElementById("kpiTotalDisagreements").innerText = s.total_disagreements;
      const sub = document.getElementById("kpiMeetingsSubtext");
      if (sub) {{
        const cov = (APP_DATA.metadata && APP_DATA.metadata.coverage) || "Full archive";
        const tc = (APP_DATA.metadata && APP_DATA.metadata.total_cohorts) || 0;
        sub.innerText = `${{cov}} (${{tc}} historical boards)`;
      }}
    }}

    function renderOverviewLandmarks() {{
      const container = document.getElementById("overviewLandmarkVotes");
      container.innerHTML = "";
      const curIds = Object.values((APP_DATA.metadata && APP_DATA.metadata.current_cohorts) || {{}});
      const curMeetings = [];
      curIds.forEach(cid => {{
        (LOADED_MEETINGS_BY_COHORT[cid] || []).forEach(m => curMeetings.push(m));
      }});
      curMeetings.sort((a, b) => (b.date || "").localeCompare(a.date || ""));
      const landmarkMeetings = curMeetings.filter(m =>
        getVisibleVotes(m.votes).some(v => v.is_contested || (v.item_title || "").includes("Budget"))
      );
      landmarkMeetings.slice(0, 5).forEach(m => {{
        container.appendChild(createMeetingElement(m));
      }});
    }}

    // Paginated timeline renderer (prevents browser lag on 500+ historical meetings)
    function renderPaginatedMeetings(container, meetings, pageSize) {{
      const limit = pageSize || 30;
      container.innerHTML = "";
      if (!meetings.length) {{
        container.innerHTML = `<div class="card" style="color:var(--text-muted);font-size:13px;">No meetings recorded for this selection.</div>`;
        return;
      }}
      let shown = 0;
      function appendNext() {{
        const existingBtn = container.querySelector(".btn-load-more");
        if (existingBtn) existingBtn.remove();
        const slice = meetings.slice(shown, shown + limit);
        slice.forEach(m => container.appendChild(createMeetingElement(m)));
        shown += slice.length;
        if (shown < meetings.length) {{
          const btn = document.createElement("button");
          btn.className = "btn-load-more";
          btn.innerText = `Show More Meetings (${{shown}} of ${{meetings.length}} shown)`;
          btn.onclick = appendNext;
          container.appendChild(btn);
        }}
      }}
      appendNext();
    }}

    function onBoardCohortChange(bodyId, cohortId) {{
      SELECTED_COHORT[bodyId] = cohortId;
      renderSingleBodyTab(bodyId);
    }}

    async function renderSingleBodyTab(bodyId) {{
      const selectedKey = SELECTED_COHORT[bodyId] || (APP_DATA.cohorts[bodyId][0] && APP_DATA.cohorts[bodyId][0].id);
      const isAll = selectedKey === `all_${{bodyId}}`;
      const cohortObj = isAll ? null : COHORTS_BY_ID[selectedKey];
      const mode = statsModeKey();
      const scopeSt = (APP_DATA.cohort_stats[mode] && APP_DATA.cohort_stats[mode][selectedKey]) || {{}};

      // Meta pills & transition note
      const metaEl = document.getElementById(`cohortMeta_${{bodyId}}`);
      const noteEl = document.getElementById(`cohortNote_${{bodyId}}`);
      if (metaEl) {{
        const spanTxt = isAll
          ? "Full Historical Archive"
          : `${{cohortObj.start_date}} &rarr; ${{cohortObj.end_date || "Present"}}`;
        metaEl.innerHTML = `
          <span class="cohort-pill">${{spanTxt}}</span>
          <span class="cohort-pill">${{scopeSt.meetings_count || 0}} Meetings</span>
          <span class="cohort-pill">${{scopeSt.votes_count || 0}} Votes (${{scopeSt.contested_votes || 0}} Contested)</span>
        `;
      }}
      if (noteEl) {{
        noteEl.innerText = isAll
          ? `Showing all ${{(APP_DATA.cohorts[bodyId] || []).length}} historical board compositions for ${{BOARD_NAMES[bodyId]}}.`
          : (cohortObj && cohortObj.transition_reason ? `Cohort Notes: ${{cohortObj.transition_reason}}` : "");
      }}

      // Members Grid
      const gridEl = document.getElementById(`${{bodyId}}MembersGrid`);
      const mTitleEl = document.getElementById(`${{bodyId}}MembersTitle`);
      let cardsData = [];
      if (isAll) {{
        if (mTitleEl) mTitleEl.innerText = `${{BOARD_NAMES[bodyId]}} — All Historical Officials`;
        cardsData = (APP_DATA.members || [])
          .filter(m => m.body_id === bodyId)
          .sort((a, b) => (b.is_current - a.is_current) || (b.start_year || 0) - (a.start_year || 0) || a.name.localeCompare(b.name))
          .map(m => getMemberWithScopeStats(m, selectedKey));
      }} else if (cohortObj) {{
        if (mTitleEl) mTitleEl.innerText = `${{BOARD_NAMES[bodyId]}} — Seated Members (${{cohortObj.short_label}})`;
        cardsData = (cohortObj.members || [])
          .map(cm => {{
            const base = MEMBERS_BY_ID[cm.member_id];
            if (!base) return null;
            return getMemberWithScopeStats(base, selectedKey, cm.role, cm.district);
          }})
          .filter(Boolean);
      }}
      if (gridEl) {{
        gridEl.innerHTML = cardsData.map(m => createMemberCardHTML(m, selectedKey)).join("");
      }}

      // Meetings Timeline (lazy-load historical cohort if needed)
      const timelineEl = document.getElementById(`${{bodyId}}MeetingsTimeline`);
      const mtTitleEl = document.getElementById(`${{bodyId}}MeetingsTitle`);
      if (mtTitleEl) {{
        mtTitleEl.innerText = isAll
          ? `${{BOARD_NAMES[bodyId]}} — Complete Historical Chronology`
          : `${{BOARD_NAMES[bodyId]}} — Meeting Chronology (${{cohortObj ? cohortObj.short_label : ""}})`;
      }}
      if (!timelineEl) return;

      const neededIds = isAll
        ? (APP_DATA.cohorts[bodyId] || []).map(c => c.id)
        : [selectedKey];

      const needsFetch = neededIds.some(cid => !LOADED_MEETINGS_BY_COHORT[cid]);
      if (needsFetch) {{
        timelineEl.innerHTML = `<div class="card" style="color:var(--text-muted);font-size:13px;">Loading historical meetings for this board cohort...</div>`;
      }}
      const meetings = await ensureManyCohortsLoaded(neededIds);
      // Guard against rapid dropdown switches
      if (SELECTED_COHORT[bodyId] !== selectedKey) return;
      renderPaginatedMeetings(timelineEl, meetings, 30);
    }}

    function renderMembers() {{
      const bodyFilter = document.getElementById("memberFilterBody").value;
      const cohortFilter = document.getElementById("memberFilterCohort") ? document.getElementById("memberFilterCohort").value : "all";
      const statusFilter = document.getElementById("memberFilterStatus").value;

      let list = [];
      if (bodyFilter !== "all" && cohortFilter !== "all" && COHORTS_BY_ID[cohortFilter]) {{
        const coh = COHORTS_BY_ID[cohortFilter];
        list = (coh.members || [])
          .map(cm => {{
            const base = MEMBERS_BY_ID[cm.member_id];
            return base ? getMemberWithScopeStats(base, cohortFilter, cm.role, cm.district) : null;
          }})
          .filter(Boolean);
      }} else {{
        let raw = APP_DATA.members || [];
        if (bodyFilter !== "all") {{
          raw = raw.filter(m => m.body_id === bodyFilter);
        }}
        if (statusFilter === "current") {{
          raw = raw.filter(m => m.is_current);
        }} else if (statusFilter === "former") {{
          raw = raw.filter(m => !m.is_current);
        }}
        list = raw.map(m => {{
          const scopeKey = m.is_current && statusFilter === "current"
            ? (APP_DATA.metadata.current_cohorts[m.body_id] || `all_${{m.body_id}}`)
            : `all_${{m.body_id}}`;
          return getMemberWithScopeStats(m, scopeKey);
        }});
      }}

      document.getElementById("allMembersGrid").innerHTML = list.map(m => createMemberCardHTML(m, m._scopeKey)).join("");
    }}

    function createMemberCardHTML(m, scopeKey) {{
      const bColor = m.body_id === "dps" ? "var(--dps-color)" : m.body_id === "city" ? "var(--city-color)" : "var(--bocc-color)";
      const termStr = m.active_terms ? m.active_terms.join(", ") : "";
      const tagsHTML = (m.ideology_tags || []).map(t => `<span class="tag tag-ideology">${{t}}</span>`).join("");
      const priorityHTML = (m.key_priorities || []).map(p => `<span class="tag">${{p}}</span>`).join("");
      const sk = scopeKey || `all_${{m.body_id}}`;

      return `
        <div class="member-card">
          <div>
            <div class="member-header">
              <div class="member-avatar" style="border: 2px solid ${{bColor}};">${{m.avatar_initials}}</div>
              <div class="member-info">
                <h3>${{m.name}}</h3>
                <p style="color: ${{bColor}}; font-weight: 600;">${{m.title}} &bull; ${{m.district}}</p>
                <p style="font-size: 11px;">${{termStr}}</p>
              </div>
            </div>

            <div class="member-stats">
              <div>
                <div class="stat-box-num">${{m.votes_cast || 0}}</div>
                <div class="stat-box-lbl">Votes Cast</div>
              </div>
              <div>
                <div class="stat-box-num" style="color: #6ee7b7;">${{m.aye_pct || 0}}%</div>
                <div class="stat-box-lbl">Aye Rate</div>
              </div>
              <div>
                <div class="stat-box-num" style="color: #fca5a5;">${{m.dissent_rate || 0}}%</div>
                <div class="stat-box-lbl">Dissent Rate</div>
              </div>
            </div>

            <p style="font-size: 12px; color: var(--text-muted); line-height: 1.5; margin-bottom: 8px;">${{m.bio || ""}}</p>

            <div class="tag-container">${{tagsHTML}}</div>
            <div class="tag-container" style="margin-top: 4px;">${{priorityHTML}}</div>
          </div>

          <button class="btn-view-record" onclick="openMemberRecord('${{m.id}}', '${{sk}}')">
            Inspect Voting Record &rarr;
          </button>
        </div>
      `;
    }}

    async function openMemberRecord(memberId, scopeKey) {{
      const member = MEMBERS_BY_ID[memberId];
      if (!member) return;

      const sk = scopeKey || `all_${{member.body_id}}`;
      const isCohortScoped = !sk.startsWith("all_") && COHORTS_BY_ID[sk];
      const scopeLabel = isCohortScoped ? COHORTS_BY_ID[sk].short_label : "Full Career on Board";

      document.getElementById("modalMemberTitle").innerText = `${{member.name}} — Voting History (${{scopeLabel}})`;
      document.getElementById("modalMemberBody").innerHTML = `<div style="color:var(--text-muted);font-size:13px;">Loading voting history...</div>`;
      document.getElementById("recordModal").style.display = "flex";

      // Load all relevant cohorts where this member was seated
      const memberCohorts = (APP_DATA.cohorts[member.body_id] || []).filter(c =>
        (c.member_ids || []).includes(member.id)
      );
      const targetCohortIds = isCohortScoped
        ? [sk]
        : (memberCohorts.length ? memberCohorts.map(c => c.id) : (APP_DATA.cohorts[member.body_id] || []).map(c => c.id));

      const meetings = await ensureManyCohortsLoaded(targetCohortIds);

      let headerControls = "";
      if (memberCohorts.length > 1) {{
        headerControls = `<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid var(--card-border);">`;
        headerControls += `<button class="btn-toggle-details" style="${{!isCohortScoped ? 'background:#2563eb;color:#fff;' : ''}}" onclick="openMemberRecord('${{member.id}}', 'all_${{member.body_id}}')">All Terms (${{memberCohorts.length}} Cohorts)</button>`;
        memberCohorts.forEach(c => {{
          const active = sk === c.id;
          headerControls += `<button class="btn-toggle-details" style="${{active ? 'background:#2563eb;color:#fff;' : ''}}" onclick="openMemberRecord('${{member.id}}', '${{c.id}}')">${{c.short_label}}</button>`;
        }});
        headerControls += `</div>`;
      }}

      let votesHTML = "";
      let count = 0;
      meetings.forEach(m => {{
        const cObj = COHORTS_BY_ID[m.cohort_id];
        const seatedHere = cObj ? (cObj.member_ids || []).includes(member.id) : member.is_current;
        getVisibleVotes(m.votes).forEach(v => {{
          const outcomePassed = (v.outcome || "").toLowerCase().includes("pass");
          const genericAyes = m.body_id === member.body_id && seatedHere && outcomePassed && isGenericUnanimousAyes(v);
          const isNay = memberMatchesVoteList(v.nays, member);
          const isAbstain = !isNay && memberMatchesVoteList(v.abstentions, member);
          const isAye = !isNay && !isAbstain && (memberMatchesVoteList(v.ayes, member) || genericAyes);

          if (isAye || isNay || isAbstain) {{
            count += 1;
            const badgeClass = isAye ? "vote-badge-passed" : isNay ? "vote-badge-failed" : "tag";
            const castText = isAye ? "AYE (IN FAVOR)" : isNay ? "NAY (DISSENT)" : "ABSTAIN";
            const tsLink = v.video_timestamp_url && v.timestamp_label
              ? `<a href="${{v.video_timestamp_url}}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:none;font-size:11px;margin-left:8px;white-space:nowrap;">&#9658; ${{v.timestamp_label}}</a>`
              : (m.video_url ? `<a href="${{m.video_url}}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:none;font-size:11px;margin-left:8px;white-space:nowrap;">&#9658; Video</a>` : "");

            votesHTML += `
              <div class="vote-item">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; gap: 8px;">
                  <span style="font-size: 11px; color: var(--text-dim);">${{m.date}} &bull; ${{m.title}}${{tsLink}}</span>
                  <span class="${{badgeClass}}">${{castText}}</span>
                </div>
                <div class="vote-title">${{v.item_title}}</div>
                <div class="vote-breakdown">
                  Outcome: <strong>${{v.outcome}}</strong> (${{v.tally}}) | Mover: ${{v.mover || 'N/A'}} | Seconder: ${{v.seconder || 'N/A'}}
                </div>
                ${{v.notes ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">${{v.notes}}</div>` : ''}}
              </div>
            `;
          }}
        }});
      }});

      if (!votesHTML) {{
        votesHTML = `<div style="color: var(--text-muted); font-size: 13px;">No recorded roll call votes on file for this cohort window.</div>`;
      }} else {{
        votesHTML = `<div style="font-size:12px;color:var(--text-muted);margin-bottom:10px;">Showing <strong>${{count}}</strong> recorded votes${{includeConsentAgenda ? " (including consent agenda)" : " (excluding blanket consent agenda)"}}.</div>` + votesHTML;
      }}

      document.getElementById("modalMemberBody").innerHTML = headerControls + votesHTML;
    }}

    function closeRecordModal() {{
      document.getElementById("recordModal").style.display = "none";
    }}

    window.onclick = function(e) {{
      const m = document.getElementById("recordModal");
      if (e.target === m) {{
        m.style.display = "none";
      }}
    }};

    // ----------------------------------------------------
    // Meeting Elements & Timeline
    // ----------------------------------------------------
    function createMeetingElement(m) {{
      const el = document.createElement("div");
      el.className = "meeting-card";

      const bColor = m.body_id === "dps" ? "dps" : m.body_id === "city" ? "city" : "bocc";
      const bLabel = m.body_id === "dps" ? "DPS Board" : m.body_id === "city" ? "City Council" : "BOCC";

      const visibleVotes = getVisibleVotes(m.votes);
      const contestedCount = visibleVotes.filter(v => v.is_contested).length;

      const agendaItems = m.agenda_items || [];
      let agendaListHTML = agendaItems.map(ag => {{
        const tsUrl = ag.video_timestamp_url || m.video_url || "";
        const tsBadge = tsUrl
          ? `<a href="${{tsUrl}}" target="_blank" rel="noopener noreferrer" style="display:inline-flex;align-items:center;gap:4px;background:rgba(37,99,235,0.2);color:#93c5fd;border:1px solid rgba(96,165,250,0.35);padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;text-decoration:none;white-space:nowrap;">&#9658; ${{ag.timestamp_label || 'Watch'}}</a>`
          : "";
        const titleLink = tsUrl
          ? `<a href="${{tsUrl}}" target="_blank" rel="noopener noreferrer" style="color:#f8fafc;text-decoration:none;">${{ag.item_number ? ag.item_number + ': ' : ''}}${{ag.title}}</a>`
          : `${{ag.item_number ? ag.item_number + ': ' : ''}}${{ag.title}}`;
        return `
          <div class="vote-item">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 4px; flex-wrap: wrap;">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                ${{tsBadge}}
                <span style="font-size: 11px; color: var(--text-dim);">${{ag.category || 'General'}}</span>
              </div>
            </div>
            <div class="vote-title">${{titleLink}}</div>
            ${{ag.discussion_summary ? `<div class="vote-breakdown" style="margin-top:4px;color:var(--text-muted);">${{ag.discussion_summary}}</div>` : ''}}
            ${{ag.vote_summary ? `<div class="vote-breakdown" style="margin-top:4px;color:#a7f3d0;"><strong>Action / Vote:</strong> ${{ag.vote_summary}}</div>` : ''}}
          </div>
        `;
      }}).join("");

      let votesListHTML = visibleVotes.map(v => {{
        const vUrl = v.video_timestamp_url || m.video_url || "";
        const vTsLink = vUrl && v.timestamp_label
          ? `<a href="${{vUrl}}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:none;font-size:11px;font-weight:600;margin-left:8px;">&#9658; ${{v.timestamp_label}}</a>`
          : (vUrl ? `<a href="${{vUrl}}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:none;font-size:11px;font-weight:600;margin-left:8px;">&#9658; Video</a>` : "");
        return `
        <div class="vote-item">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; flex-wrap: wrap; gap: 6px;">
            <div>
              <span class="${{v.outcome.toLowerCase().includes('pass') ? 'vote-badge-passed' : 'vote-badge-failed'}}">
                ${{v.outcome}} (${{v.tally}})
              </span>
              ${{vTsLink}}
            </div>
            <span style="font-size: 11px; color: var(--text-dim);">${{v.category || 'General'}}</span>
          </div>
          <div class="vote-title">${{vUrl ? `<a href="${{vUrl}}" target="_blank" rel="noopener noreferrer" style="color:#f8fafc;text-decoration:none;">${{v.item_title}}</a>` : v.item_title}}</div>
          ${{v.discussion_detail ? `<div class="vote-breakdown" style="margin-top:6px;margin-bottom:6px;color:#cbd5e1;line-height:1.5;"><strong>Discussion:</strong> ${{v.discussion_detail}}</div>` : ''}}
          <div class="vote-breakdown">
            <strong>Mover:</strong> ${{v.mover || 'N/A'}} | <strong>Seconder:</strong> ${{v.seconder || 'N/A'}} | <strong>Format:</strong> ${{v.vote_format}}
          </div>
          <div class="vote-breakdown">
            <strong>Ayes:</strong> ${{v.ayes.join(', ') || 'None'}}
          </div>
          ${{v.nays && v.nays.length ? `<div class="vote-breakdown" style="color: #fca5a5;"><strong>Nays:</strong> ${{v.nays.join(', ')}}</div>` : ''}}
          ${{v.amendments && v.amendments.length ? `<div class="vote-breakdown" style="color: #93c5fd;"><strong>Amendments:</strong> ${{v.amendments.join('; ')}}</div>` : ''}}
          ${{v.notes ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">${{v.notes}}</div>` : ''}}
        </div>
      `;
      }}).join("");

      let disagreementsListHTML = (m.disagreements || []).map(d => {{
        const dUrl = d.video_timestamp_url || m.video_url || "";
        const dTsLink = dUrl && d.timestamp_label
          ? ` <a href="${{dUrl}}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:none;font-size:11px;font-weight:600;margin-left:8px;">&#9658; ${{d.timestamp_label}}</a>`
          : (dUrl ? ` <a href="${{dUrl}}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:none;font-size:11px;font-weight:600;margin-left:8px;">&#9658; Watch</a>` : "");
        return `
        <div class="disagreement-box">
          <div class="dis-title">&#9888; Deliberation Contention: ${{d.issue}}${{dTsLink}}</div>
          <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">${{d.summary}}</p>
          <div class="dis-side">
            <strong style="color: #93c5fd;">Side A (${{d.side_a.position}}):</strong>
            ${{(d.side_a.arguments || []).join(' &bull; ')}}
            <div style="font-size: 11px; color: var(--text-dim);">Members: ${{d.side_a.members.join(', ')}}</div>
          </div>
          <div class="dis-side" style="margin-top: 6px;">
            <strong style="color: #fca5a5;">Side B (${{d.side_b.position}}):</strong>
            ${{(d.side_b.arguments || []).join(' &bull; ')}}
            <div style="font-size: 11px; color: var(--text-dim);">Members: ${{d.side_b.members.join(', ')}}</div>
          </div>
          <div style="font-size: 11px; color: #a7f3d0; margin-top: 6px;">
            <strong>Resolution:</strong> ${{d.resolution}}
          </div>
        </div>
      `;
      }}).join("");

      const meetingTitleHTML = m.video_url
        ? `<a href="${{m.video_url}}" target="_blank" rel="noopener noreferrer" style="color:inherit;text-decoration:none;">${{m.title}}</a>`
        : m.title;

      el.innerHTML = `
        <div class="meeting-header">
          <div>
            <span class="badge-body ${{bColor}}">${{bLabel}}</span>
            <span style="font-size: 12px; color: var(--text-muted); margin-left: 8px;">${{m.date}}</span>
            <span style="font-size: 12px; color: var(--text-dim); margin-left: 8px;">&bull; Duration: ${{m.duration || '2h+'}}</span>
            ${{m.presiding_chair ? `<span style="font-size: 12px; color: var(--text-dim); margin-left: 8px;">&bull; Presided by ${{m.presiding_chair}}</span>` : ''}}
          </div>
          <div>
            ${{contestedCount > 0 ? `<span class="vote-badge-failed">${{contestedCount}} Contested Roll Calls</span>` : `<span class="vote-badge-passed">Consensual</span>`}}
          </div>
        </div>

        <div class="meeting-title">${{meetingTitleHTML}}</div>
        <div class="meeting-summary">${{m.executive_summary || ''}}</div>

        <div class="meeting-details-toggle">
          ${{agendaItems.length ? `
            <button class="btn-toggle-details" onclick="toggleDetailsPane('${{m.id}}_agenda', this)">
              <span>&#128203;</span> Agenda Topics &amp; Timestamps (${{agendaItems.length}})
            </button>
          ` : ''}}
          <button class="btn-toggle-details" onclick="toggleDetailsPane('${{m.id}}_votes', this)">
            <span>&#9745;</span> Roll Call Votes (${{visibleVotes.length}})
          </button>
          ${{m.disagreements && m.disagreements.length ? `
            <button class="btn-toggle-details" onclick="toggleDetailsPane('${{m.id}}_dis', this)">
              <span>&#9878;</span> Debates & Disagreements (${{m.disagreements.length}})
            </button>
          ` : ''}}
          ${{m.video_url ? `
            <a href="${{m.video_url}}" target="_blank" rel="noopener noreferrer" class="btn-toggle-details" style="text-decoration: none;">
              <span>&#9658;</span> Watch Video Recording
            </a>
          ` : ''}}
          ${{m.summary_pdf_url ? `
            <a href="${{m.summary_pdf_url}}" target="_blank" rel="noopener noreferrer" class="btn-toggle-details" style="text-decoration: none; border-color: rgba(16,185,129,0.45); color: #6ee7b7;">
              <span>&#128196;</span> Executive Summary PDF
            </a>
          ` : ''}}
        </div>

        <div id="${{m.id}}_agenda" class="details-pane">
          ${{agendaListHTML || '<div style="font-size: 12px; color: var(--text-muted);">No timestamped agenda breakdown available.</div>'}}
        </div>

        <div id="${{m.id}}_votes" class="details-pane">
          ${{votesListHTML || '<div style="font-size: 12px; color: var(--text-muted);">No formal roll-call votes recorded.</div>'}}
        </div>

        <div id="${{m.id}}_dis" class="details-pane">
          ${{disagreementsListHTML}}
        </div>
      `;

      return el;
    }}

    function toggleDetailsPane(paneId, btn) {{
      const pane = document.getElementById(paneId);
      if (!pane) return;
      if (pane.style.display === "block") {{
        pane.style.display = "none";
        btn.style.background = "#1e293b";
      }} else {{
        pane.style.display = "block";
        btn.style.background = "#334155";
      }}
    }}

    async function renderTimeline() {{
      const bodyFilter = document.getElementById("timelineFilterBody").value;
      const cohortFilter = document.getElementById("timelineFilterCohort") ? document.getElementById("timelineFilterCohort").value : "current";
      const yearFilter = document.getElementById("timelineFilterYear").value;
      const contestedFilter = document.getElementById("timelineFilterContested").value;
      const statusEl = document.getElementById("timelineStatusNote");
      const container = document.getElementById("masterTimelineList");

      // Determine which cohorts need to be loaded
      const bodies = bodyFilter === "all" ? ["dps", "city", "bocc"] : [bodyFilter];
      let targetCohortIds = [];
      if (cohortFilter === "current" && yearFilter === "all") {{
        bodies.forEach(b => {{
          const cid = APP_DATA.metadata.current_cohorts && APP_DATA.metadata.current_cohorts[b];
          if (cid) targetCohortIds.push(cid);
        }});
      }} else if (cohortFilter !== "current" && cohortFilter !== "all" && COHORTS_BY_ID[cohortFilter]) {{
        targetCohortIds = [cohortFilter];
      }} else {{
        // Either "all" selected or a specific historical year selected -> load overlapping cohorts
        bodies.forEach(b => {{
          (APP_DATA.cohorts[b] || []).forEach(c => {{
            if (yearFilter === "all") {{
              targetCohortIds.push(c.id);
            }} else {{
              const sd = (c.start_date || "0000").slice(0, 4);
              const ed = (c.end_date || "9999").slice(0, 4);
              if (sd <= yearFilter && yearFilter <= ed) {{
                targetCohortIds.push(c.id);
              }}
            }}
          }});
        }});
      }}

      const needsFetch = targetCohortIds.some(cid => !LOADED_MEETINGS_BY_COHORT[cid]);
      if (needsFetch) {{
        container.innerHTML = `<div class="card" style="color:var(--text-muted);font-size:13px;">Loading historical archive...</div>`;
      }}

      let list = await ensureManyCohortsLoaded(targetCohortIds);
      if (yearFilter !== "all") {{
        list = list.filter(m => (m.date || "").startsWith(yearFilter));
      }}
      if (contestedFilter === "contested") {{
        list = list.filter(m => getVisibleVotes(m.votes).some(v => v.is_contested));
      }}

      if (statusEl) {{
        statusEl.innerText = `Showing ${{list.length}} meeting${{list.length === 1 ? "" : "s"}} matching selected filters.`;
      }}
      renderPaginatedMeetings(container, list, 30);
    }}

    // ----------------------------------------------------
    // Heatmaps & Alignment Grids (Board + Cohort Scoped)
    // ----------------------------------------------------
    function onAlignmentBodyChange(bodyId) {{
      populateAlignmentCohorts(bodyId);
      renderPairwiseHeatmap();
    }}

    function renderPairwiseHeatmap() {{
      const bodyId = (document.getElementById("alignmentBodySelect") && document.getElementById("alignmentBodySelect").value) || "city";
      const cohortId = (document.getElementById("alignmentCohortSelect") && document.getElementById("alignmentCohortSelect").value)
        || (APP_DATA.metadata.current_cohorts && APP_DATA.metadata.current_cohorts[bodyId]);
      const coh = COHORTS_BY_ID[cohortId];
      const mode = statsModeKey();
      const scopeSt = (APP_DATA.cohort_stats[mode] && APP_DATA.cohort_stats[mode][cohortId]) || null;
      const matrix = (scopeSt && scopeSt.pairwise) || {{}};

      const noteEl = document.getElementById("alignmentCohortNote");
      if (noteEl && coh) {{
        noteEl.innerText = `${{BOARD_NAMES[bodyId]}} • ${{coh.short_label}} (${{scopeSt ? scopeSt.meetings_count : 0}} meetings, ${{scopeSt ? scopeSt.votes_count : 0}} votes, ${{scopeSt ? scopeSt.contested_votes : 0}} contested)`;
      }}

      const members = coh
        ? (coh.members || []).map(cm => {{
            const base = MEMBERS_BY_ID[cm.member_id];
            return base ? getMemberWithScopeStats(base, cohortId, cm.role, cm.district) : null;
          }}).filter(Boolean)
        : [];

      if (!members.length) {{
        document.getElementById("heatmapContainer").innerHTML = `<div style="color:var(--text-muted);font-size:13px;">No seated member records available for this cohort.</div>`;
        renderDissentLeaderboard(bodyId, cohortId, members);
        return;
      }}

      let html = `<table class="heatmap-table"><thead><tr><th>Official</th>`;
      members.forEach(m => {{
        const colLabel = /^Dr\\.?\\s+/i.test(m.name) ? m.name : m.name.split(" ")[0];
        html += `<th>${{colLabel}}</th>`;
      }});
      html += `</tr></thead><tbody>`;

      members.forEach((m1, i) => {{
        html += `<tr><th>${{m1.name}}</th>`;
        members.forEach((m2, j) => {{
          if (j < i) {{
            html += `<td class="heat-self" style="background: transparent; border-color: transparent;"></td>`;
          }} else if (i === j) {{
            html += `<td class="heat-self">100%</td>`;
          }} else {{
            const score = (matrix[m1.id] && matrix[m1.id][m2.id] !== undefined) ? matrix[m1.id][m2.id] : null;
            if (score === null) {{
              html += `<td class="heat-self">&mdash;</td>`;
            }} else {{
              const cls = score >= 95 ? "heat-high" : score >= 90 ? "heat-med" : "heat-low";
              html += `<td class="${{cls}}">${{score}}%</td>`;
            }}
          }}
        }});
        html += `</tr>`;
      }});

      html += `</tbody></table>`;
      document.getElementById("heatmapContainer").innerHTML = html;
      renderDissentLeaderboard(bodyId, cohortId, members);
    }}

    function renderDissentLeaderboard(bodyId, cohortId, scopedMembers) {{
      const selectedBody = bodyId || (document.getElementById("alignmentBodySelect") ? document.getElementById("alignmentBodySelect").value : "city");
      const selectedCohort = cohortId || (document.getElementById("alignmentCohortSelect") ? document.getElementById("alignmentCohortSelect").value : null);
      const coh = COHORTS_BY_ID[selectedCohort];

      const titleEl = document.getElementById("dissentLeaderboardTitle");
      if (titleEl) {{
        const cohLbl = coh ? ` (${{coh.short_label}})` : "";
        titleEl.innerText = `Dissent Frequency Leaderboard — ${{BOARD_NAMES[selectedBody] || selectedBody.toUpperCase()}}${{cohLbl}}`;
      }}

      const sorted = (scopedMembers || [])
        .filter(m => m.votes_cast > 0)
        .sort((a, b) => (b.dissent_rate - a.dissent_rate) || (b.dissents_count - a.dissents_count) || a.name.localeCompare(b.name));

      if (!sorted.length) {{
        document.getElementById("dissentLeaderboard").innerHTML = `<div style="color:var(--text-muted);font-size:13px;">No recorded roll-call votes for this board cohort${{includeConsentAgenda ? "" : " (excluding blanket consent agenda)"}}.</div>`;
        return;
      }}

      let html = `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px;">`;
      sorted.forEach(m => {{
        const bLabel = m.body_id === "dps" ? "DPS Board" : m.body_id === "city" ? "City Council" : "BOCC";
        html += `
          <div style="background: var(--card-inner); padding: 12px 16px; border-radius: 8px; border: 1px solid #232d42;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <strong style="color: #fff; font-size: 14px;">${{m.name}}</strong>
                <div style="font-size: 11px; color: var(--text-dim);">${{bLabel}} &bull; ${{m.title}}</div>
              </div>
              <div style="text-align: right;">
                <div style="font-size: 18px; font-weight: 800; color: #fca5a5;">${{m.dissent_rate}}%</div>
                <div style="font-size: 10px; color: var(--text-dim); text-transform: uppercase;">${{m.dissents_count}}/${{m.votes_cast}} Dissent</div>
              </div>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 8px;">
              Primary focus: ${{(m.key_priorities || []).slice(0, 2).join(', ') || m.district}}
            </div>
          </div>
        `;
      }});
      html += `</div>`;
      document.getElementById("dissentLeaderboard").innerHTML = html;
    }}

    // Global Search Function (searches full 2012–2026 index & lazy-loads matching cohorts)
    let _searchDebounce = null;
    function handleGlobalSearch(query) {{
      clearTimeout(_searchDebounce);
      _searchDebounce = setTimeout(() => _runGlobalSearch(query), 220);
    }}

    async function _runGlobalSearch(query) {{
      const q = (query || "").toLowerCase().trim();
      if (!q) {{
        renderTimeline();
        return;
      }}

      // Switch to timeline tab
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
      document.getElementById("tab_timeline").classList.add("active");

      const container = document.getElementById("masterTimelineList");
      const statusEl = document.getElementById("timelineStatusNote");
      container.innerHTML = `<div class="card" style="color:var(--text-muted);font-size:13px;">Searching full historical archive for "${{query}}"...</div>`;

      const idx = await ensureSearchIndexLoaded();
      const hits = idx.filter(item =>
        (item.title || "").toLowerCase().includes(q) ||
        (item.summary || "").toLowerCase().includes(q) ||
        (item.chair || "").toLowerCase().includes(q) ||
        (item.date || "").includes(q) ||
        (item.votes || []).some(t => t.toLowerCase().includes(q)) ||
        (item.debates || []).some(d => d.toLowerCase().includes(q))
      );

      if (!hits.length) {{
        if (statusEl) statusEl.innerText = `Found 0 matching meetings across the full archive for "${{query}}".`;
        container.innerHTML = `<div class="card" style="color:var(--text-muted);font-size:13px;">No matching meetings found for "${{query}}".</div>`;
        return;
      }}

      const hitIds = new Set(hits.map(h => h.id));
      const cohortIdsNeeded = Array.from(new Set(hits.map(h => h.cohort_id).filter(Boolean)));
      const loaded = await ensureManyCohortsLoaded(cohortIdsNeeded);
      const matchingMeetings = loaded.filter(m => hitIds.has(m.id));

      if (statusEl) statusEl.innerText = `Found ${{matchingMeetings.length}} matching meeting records across 2012–2026 for "${{query}}":`;
      renderPaginatedMeetings(container, matchingMeetings, 30);
    }}

    // Check auth on load
    window.addEventListener("DOMContentLoaded", checkAuth);
  </script>
</body>
</html>
"""

    with open(HTML_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    # Also keep /durhampolitics.html in sync for extensionless URLs without trailing slash
    flat_html_path = HTML_OUTPUT_PATH.parent.parent / "durhampolitics.html"
    if flat_html_path.parent.exists():
        with open(flat_html_path, "w", encoding="utf-8") as f:
            f.write(html)

    # Generate dedicated Live Meeting split-pane page & default status JSON
    generate_live_meeting_page()

    print(f"✓ Standalone private web app generated at: {HTML_OUTPUT_PATH}")
    print(f"  - Password protected with 'durhampol' & master password")
    print(f"  - Anti-crawler robots meta tags included")
    print(f"  - Exported dataset cached at: {DATA_EXPORT_PATH}")
    return str(HTML_OUTPUT_PATH)


def generate_live_meeting_page() -> str:
    """
    Generates /durhampolitics/live.html:
      - Left pane: Dynamically updating Executive Summary (updates every 60s)
      - Top-right pane: Embedded live video of the ongoing meeting
      - Bottom-right pane: Real-time running audio transcript (non-caption ASR)
    Also ensures /durhampolitics/live_status.json exists.
    """
    live_html_path = HTML_OUTPUT_PATH.parent / "live.html"
    live_status_path = HTML_OUTPUT_PATH.parent / "live_status.json"
    HTML_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not live_status_path.exists():
        live_status_path.write_text(json.dumps({
            "is_live": False,
            "body_id": None,
            "body_name": None,
            "video_id": None,
            "video_url": None,
            "title": None,
            "started_at": None,
            "summary_updated_at": None,
            "transcript_updated_at": None,
            "executive_summary": "",
            "topics_so_far": [],
            "votes_so_far": [],
            "debates_so_far": [],
            "transcript_lines": [],
            "source_mode": "realtime_audio_asr"
        }, indent=2), encoding="utf-8")

    live_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
  <title>Live Meeting in Progress | Durham Politics Tracker</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-base: #070b14;
      --bg-surface: #0f1623;
      --bg-card: #151e30;
      --bg-elevated: #1c2841;
      --border: #23304c;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --accent: #3b82f6;
      --danger: #ef4444;
      --success: #10b981;
      --warn: #f59e0b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      background: var(--bg-base);
      color: var(--text-main);
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    #authOverlay {{
      position: fixed; inset: 0; z-index: 9999;
      background: radial-gradient(circle at top, #13203d 0%, #070b14 70%);
      display: flex; align-items: center; justify-content: center;
    }}
    .auth-card {{
      width: 100%; max-width: 400px; background: var(--bg-surface);
      border: 1px solid var(--border); border-radius: 14px; padding: 28px;
      box-shadow: 0 24px 60px rgba(0,0,0,0.6);
    }}
    .auth-card h2 {{ font-size: 18px; margin-bottom: 6px; }}
    .auth-card p {{ font-size: 13px; color: var(--text-muted); margin-bottom: 18px; }}
    .auth-input {{
      width: 100%; padding: 10px 12px; margin-bottom: 12px; border-radius: 8px;
      border: 1px solid var(--border); background: var(--bg-card); color: var(--text-main);
      font-size: 14px;
    }}
    .auth-btn {{
      width: 100%; padding: 10px 14px; border-radius: 8px; border: none;
      background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #fff;
      font-weight: 700; font-size: 14px; cursor: pointer;
    }}
    #liveApp {{
      display: none;
      flex-direction: column;
      height: 100vh;
      width: 100%;
    }}
    header {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 20px; background: var(--bg-surface); border-bottom: 1px solid var(--border);
      gap: 12px; flex-shrink: 0; flex-wrap: wrap;
    }}
    .hdr-left {{ display: flex; align-items: center; gap: 12px; min-width: 0; }}
    .live-pill {{
      display: inline-flex; align-items: center; gap: 6px;
      padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 800;
      background: rgba(239,68,68,0.2); color: #fca5a5; border: 1px solid rgba(239,68,68,0.45);
      text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap;
    }}
    .live-dot {{
      width: 8px; height: 8px; border-radius: 50%; background: #ef4444;
      box-shadow: 0 0 8px #ef4444; animation: pulse 1.4s infinite;
    }}
    @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}
    .hdr-title {{ font-size: 15px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .hdr-right {{ display: flex; align-items: center; gap: 10px; font-size: 12px; color: var(--text-muted); }}
    .btn-back {{
      padding: 6px 12px; border-radius: 8px; border: 1px solid var(--border);
      background: var(--bg-card); color: var(--text-main); text-decoration: none;
      font-size: 12px; font-weight: 600;
    }}
    .btn-back:hover {{ background: var(--bg-elevated); }}

    /* Split Layout: Left = Exec Summary, Top-Right = Video, Bottom-Right = Running Transcript */
    .split-grid {{
      flex: 1;
      display: grid;
      grid-template-columns: minmax(420px, 1.15fr) minmax(380px, 0.85fr);
      grid-template-rows: 1fr 1fr;
      gap: 12px;
      padding: 12px;
      min-height: 0;
    }}
    .pane {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      min-height: 0;
      overflow: hidden;
    }}
    .pane-left {{ grid-column: 1; grid-row: 1 / span 2; }}
    .pane-top-right {{ grid-column: 2; grid-row: 1; }}
    .pane-bottom-right {{ grid-column: 2; grid-row: 2; }}
    .pane-header {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 14px; background: var(--bg-card); border-bottom: 1px solid var(--border);
      font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
      color: #cbd5e1; flex-shrink: 0; gap: 8px;
    }}
    .pane-body {{ flex: 1; overflow-y: auto; padding: 16px; min-height: 0; }}
    .video-wrap {{ flex: 1; background: #000; position: relative; min-height: 0; }}
    .video-wrap iframe {{ position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }}
    .section-hdr {{
      font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em;
      color: #60a5fa; margin: 16px 0 8px 0;
    }}
    .section-hdr:first-child {{ margin-top: 0; }}
    .exec-box {{
      background: var(--bg-card); border: 1px solid var(--border); border-left: 3px solid var(--accent);
      border-radius: 8px; padding: 14px; font-size: 13.5px; line-height: 1.6; color: #e2e8f0;
    }}
    .topic-card, .vote-card {{
      background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
      padding: 12px; margin-bottom: 10px;
    }}
    .topic-head {{
      display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 4px;
    }}
    .ts-chip {{
      display: inline-flex; align-items: center; gap: 4px; font-family: 'JetBrains Mono', monospace;
      font-size: 11px; font-weight: 600; color: #93c5fd; background: rgba(37,99,235,0.2);
      border: 1px solid rgba(96,165,250,0.35); border-radius: 999px; padding: 2px 8px;
      text-decoration: none;
    }}
    .transcript-line {{
      font-size: 12.5px; line-height: 1.5; padding: 5px 8px; border-radius: 6px;
      border-bottom: 1px solid rgba(35,48,76,0.45);
    }}
    .transcript-line:hover {{ background: rgba(59,130,246,0.08); }}
    .t-ts {{
      font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #60a5fa;
      margin-right: 8px; text-decoration: none;
    }}
    .empty-state {{
      height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;
      text-align: center; color: var(--text-muted); gap: 10px; padding: 24px;
    }}
    @media (max-width: 960px) {{
      body {{ height: auto; overflow: auto; }}
      #liveApp {{ height: auto; }}
      .split-grid {{ grid-template-columns: 1fr; grid-template-rows: auto; }}
      .pane-left, .pane-top-right, .pane-bottom-right {{ grid-column: 1; grid-row: auto; min-height: 360px; }}
      .video-wrap {{ min-height: 280px; }}
    }}
  </style>
</head>
<body>
  <div id="authOverlay">
    <form class="auth-card" onsubmit="handleAuth(event)">
      <h2>Durham Politics Tracker — Live Feed</h2>
      <p>Enter credentials to access the real-time meeting dashboard.</p>
      <input id="authUser" class="auth-input" type="text" placeholder="Username" required>
      <input id="authPass" class="auth-input" type="password" placeholder="Password" required>
      <div id="authErr" style="color:#fca5a5;font-size:12px;margin-bottom:10px;display:none;">Invalid credentials or pending approval.</div>
      <button class="auth-btn" type="submit">Unlock Live Meeting</button>
      <div style="margin-top:12px;text-align:center;font-size:12px;color:var(--text-muted);">
        Need an account? <a href="/durhampolitics/signup.html" style="color:#60a5fa;text-decoration:none;font-weight:600;">Request Access &rarr;</a>
        &nbsp;&bull;&nbsp;
        <a href="/durhampolitics/docs.html" style="color:var(--text-muted);text-decoration:none;">Documentation</a>
      </div>
    </form>
  </div>

  <div id="liveApp">
    <header>
      <div class="hdr-left">
        <span class="live-pill" id="liveBadge"><span class="live-dot"></span> <span id="liveBadgeText">Checking...</span></span>
        <div class="hdr-title" id="liveTitle">Durham Local Government Live Meeting Monitor</div>
      </div>
      <div class="hdr-right">
        <span id="summaryStatus">Summary updates every 60s (Real-time Audio ASR)</span>
        <a href="/durhampolitics/docs.html" class="btn-back">&#128214; Docs</a>
        <a href="/durhampolitics/" class="btn-back">&larr; Back to Archive</a>
      </div>
    </header>

    <div class="split-grid">
      <!-- LEFT: Dynamically Updating Executive Summary -->
      <section class="pane pane-left">
        <div class="pane-header">
          <span>Executive Summary of Discussion So Far</span>
          <span id="summaryTimer" style="font-family:'JetBrains Mono',monospace;color:#6ee7b7;">Next update: 60s</span>
        </div>
        <div class="pane-body" id="summaryPane">
          <div class="empty-state">Waiting for live stream audio analysis...</div>
        </div>
      </section>

      <!-- TOP RIGHT: Live Video -->
      <section class="pane pane-top-right">
        <div class="pane-header">
          <span>Live Meeting Video</span>
          <a id="openYtLink" href="#" target="_blank" rel="noopener noreferrer" style="color:#93c5fd;text-decoration:none;display:none;">Open on YouTube &#8599;</a>
        </div>
        <div class="video-wrap" id="videoWrap">
          <div class="empty-state">No live video stream active right now.</div>
        </div>
      </section>

      <!-- BOTTOM RIGHT: Running Transcript -->
      <section class="pane pane-bottom-right">
        <div class="pane-header">
          <span>Running Transcript (Real-Time Video Audio ASR)</span>
          <div style="display:flex;align-items:center;gap:8px;">
            <input id="transcriptFilter" type="text" placeholder="Filter..." oninput="renderTranscript()" style="background:var(--bg-surface);border:1px solid var(--border);color:#fff;padding:3px 8px;border-radius:6px;font-size:11px;width:110px;">
            <label style="display:inline-flex;align-items:center;gap:4px;font-size:11px;text-transform:none;cursor:pointer;">
              <input id="autoScrollToggle" type="checkbox" checked> Auto-scroll
            </label>
          </div>
        </div>
        <div class="pane-body" id="transcriptPane" style="padding:10px;">
          <div class="empty-state">Real-time audio transcript will appear here once a meeting begins.</div>
        </div>
      </section>
    </div>
  </div>

  <script>
    const SHARED_ACTIVE_KEY = "rann_auth_last_active";
    const INACTIVITY_TIMEOUT_MS = 60 * 60 * 1000;
    let lastActiveMem = Date.now();
    let currentVideoId = null;
    let latestData = null;
    let secondsToSummaryRefresh = 60;

    function touchActivity() {{
      lastActiveMem = Date.now();
      try {{ localStorage.setItem(SHARED_ACTIVE_KEY, lastActiveMem.toString()); }} catch(e) {{}}
    }}
    function getLastActive() {{
      try {{
        const s = parseInt(localStorage.getItem(SHARED_ACTIVE_KEY) || "0", 10);
        return Math.max(s || 0, lastActiveMem);
      }} catch(e) {{ return lastActiveMem; }}
    }}
    ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'].forEach(ev => {{
      window.addEventListener(ev, () => touchActivity(), {{ passive: true }});
    }});
    setInterval(() => {{
      const isAuthed = sessionStorage.getItem("rann_session_active") || sessionStorage.getItem("durham_pol_auth");
      if (isAuthed && (Date.now() - getLastActive() > INACTIVITY_TIMEOUT_MS)) {{
        sessionStorage.removeItem("rann_session_active");
        sessionStorage.removeItem("durham_pol_auth");
        document.getElementById("liveApp").style.display = "none";
        document.getElementById("authOverlay").style.display = "flex";
      }}
    }}, 5000);

    async function sha256Hex(str) {{
      const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
      return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
    }}

    async function handleAuth(e) {{
      e.preventDefault();
      const u = document.getElementById("authUser").value.trim().toLowerCase();
      const p = document.getElementById("authPass").value.trim();
      if (u === "rann" && p === "{MASTER_PASSWORD}") {{
        sessionStorage.setItem("rann_session_active", "valid");
        sessionStorage.setItem("durham_pol_auth", "granted");
        touchActivity();
        unlockLive();
        return;
      }}
      if (u === "durhampol" && p === "{PAGE_PASSWORD}") {{
        sessionStorage.setItem("durham_pol_auth", "granted");
        touchActivity();
        unlockLive();
        return;
      }}
      try {{
        const res = await fetch("/durhampolitics/approved_users.json?t=" + Date.now(), {{ cache: "no-store" }});
        if (res.ok) {{
          const data = await res.json();
          const match = ((data && data.users) || []).find(x =>
            x.status === "APPROVED" &&
            (x.allowed_pages || []).includes("/durhampolitics") &&
            ((x.username || "").toLowerCase() === u || (x.email || "").toLowerCase() === u)
          );
          if (match && match.salt && match.password_hash) {{
            const h = await sha256Hex(match.salt + ":" + p);
            if (h === match.password_hash) {{
              sessionStorage.removeItem("rann_session_active");
              sessionStorage.setItem("durham_pol_auth", "granted");
              touchActivity();
              unlockLive();
              return;
            }}
          }}
        }}
      }} catch (err) {{}}
      document.getElementById("authErr").style.display = "block";
    }}

    function unlockLive() {{
      document.getElementById("authOverlay").style.display = "none";
      document.getElementById("liveApp").style.display = "flex";
      fetchLiveStatus(true);
      setInterval(() => fetchLiveStatus(false), 10000);
      setInterval(() => {{
        secondsToSummaryRefresh = secondsToSummaryRefresh <= 1 ? 60 : secondsToSummaryRefresh - 1;
        const el = document.getElementById("summaryTimer");
        if (el) el.innerText = "Next summary sync: " + secondsToSummaryRefresh + "s";
        if (secondsToSummaryRefresh === 60) fetchLiveStatus(true);
      }}, 1000);
    }}

    function esc(s) {{
      return String(s || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    }}

    async function fetchLiveStatus(forceSummary) {{
      try {{
        const res = await fetch("/durhampolitics/live_status.json?t=" + Date.now(), {{ cache: "no-store" }});
        if (!res.ok) return;
        const data = await res.json();
        const prevSummaryTs = latestData ? latestData.summary_updated_at : null;
        latestData = data;

        const badge = document.getElementById("liveBadgeText");
        const titleEl = document.getElementById("liveTitle");
        const ytLink = document.getElementById("openYtLink");

        if (!data || !data.is_live) {{
          badge.innerText = "OFFLINE";
          titleEl.innerText = "No Meeting Currently in Progress";
          ytLink.style.display = "none";
          currentVideoId = null;
          document.getElementById("videoWrap").innerHTML = '<div class="empty-state"><strong>No Durham meeting is currently live.</strong><span>When City Council, DPS Board, or BOCC goes live, this page activates automatically with real-time audio transcription and 60-second executive summaries.</span><a href="/durhampolitics/" class="btn-back">Return to Meeting Archives</a></div>';
          document.getElementById("summaryPane").innerHTML = '<div class="empty-state">No live session in progress. Past meetings and Executive Summary PDFs are available in the main archive.</div>';
          document.getElementById("transcriptPane").innerHTML = '<div class="empty-state">Standing by for next live broadcast...</div>';
          return;
        }}

        const bName = data.body_name || (data.body_id || "").toUpperCase();
        badge.innerText = "LIVE • " + (data.body_id || "").toUpperCase();
        titleEl.innerText = data.title || (bName + " — Live Meeting");
        if (data.video_url) {{
          ytLink.href = data.video_url;
          ytLink.style.display = "inline";
        }}

        if (data.video_id && data.video_id !== currentVideoId) {{
          currentVideoId = data.video_id;
          document.getElementById("videoWrap").innerHTML = `<iframe src="https://www.youtube.com/embed/${{encodeURIComponent(data.video_id)}}?autoplay=1&rel=0" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>`;
        }}

        if (forceSummary || data.summary_updated_at !== prevSummaryTs) {{
          renderSummary(data);
        }}
        renderTranscript();
      }} catch (e) {{
        console.error("Live status poll failed:", e);
      }}
    }}

    function renderSummary(data) {{
      const pane = document.getElementById("summaryPane");
      const updatedStr = data.summary_updated_at ? new Date(data.summary_updated_at).toLocaleTimeString() : "Updating...";
      document.getElementById("summaryStatus").innerText = "Last summary: " + updatedStr + " • Real-time Audio ASR";

      let html = `
        <div class="section-hdr">Executive Overview So Far</div>
        <div class="exec-box">${{esc(data.executive_summary || "Listening to live meeting audio and synthesizing initial summary...")}}</div>
      `;

      const topics = data.topics_so_far || [];
      html += `<div class="section-hdr">Agenda Topics Discussed So Far (${{topics.length}})</div>`;
      if (!topics.length) {{
        html += `<div style="font-size:12.5px;color:var(--text-dim);">Topics will populate automatically as agenda items are discussed.</div>`;
      }} else {{
        topics.forEach(t => {{
          const tsUrl = (data.video_url && t.start_seconds !== undefined) ? `${{data.video_url}}&t=${{t.start_seconds}}s` : (data.video_url || "#");
          html += `
            <div class="topic-card">
              <div class="topic-head">
                <strong style="font-size:13px;color:#fff;">${{esc(t.title)}}</strong>
                <a class="ts-chip" href="${{tsUrl}}" target="_blank" rel="noopener noreferrer">&#9658; ${{esc(t.timestamp_label || "Live")}}</a>
              </div>
              <div style="font-size:12.5px;color:var(--text-muted);line-height:1.5;">${{esc(t.discussion_summary || "")}}</div>
              ${{t.vote_summary ? `<div style="font-size:12px;color:#6ee7b7;margin-top:6px;"><strong>Vote / Action:</strong> ${{esc(t.vote_summary)}}</div>` : ""}}
            </div>
          `;
        }});
      }}

      const votes = data.votes_so_far || [];
      html += `<div class="section-hdr">Motions &amp; Votes Observed So Far (${{votes.length}})</div>`;
      if (!votes.length) {{
        html += `<div style="font-size:12.5px;color:var(--text-dim);">No formal votes detected yet in the live audio.</div>`;
      }} else {{
        votes.forEach(v => {{
          const tsUrl = (data.video_url && v.timestamp_seconds !== undefined) ? `${{data.video_url}}&t=${{v.timestamp_seconds}}s` : (data.video_url || "#");
          html += `
            <div class="vote-card">
              <div class="topic-head">
                <strong style="font-size:13px;color:#fff;">${{esc(v.item_title)}}</strong>
                <a class="ts-chip" href="${{tsUrl}}" target="_blank" rel="noopener noreferrer">&#9658; ${{esc(v.timestamp_label || "")}}</a>
              </div>
              <div style="font-size:12px;color:#93c5fd;">Outcome: <strong>${{esc(v.outcome || "Recorded")}}</strong> ${{v.tally ? "(" + esc(v.tally) + ")" : ""}}</div>
              ${{v.notes ? `<div style="font-size:12px;color:var(--text-muted);margin-top:4px;">${{esc(v.notes)}}</div>` : ""}}
            </div>
          `;
        }});
      }}

      pane.innerHTML = html;
    }}

    function renderTranscript() {{
      const pane = document.getElementById("transcriptPane");
      if (!latestData || !latestData.is_live) return;
      const filter = (document.getElementById("transcriptFilter").value || "").trim().toLowerCase();
      const lines = (latestData.transcript_lines || []).filter(l => !filter || (l.text || "").toLowerCase().includes(filter));
      if (!lines.length) {{
        pane.innerHTML = '<div class="empty-state">Transcribing live audio stream via local ASR...</div>';
        return;
      }}
      const baseUrl = latestData.video_url || "";
      pane.innerHTML = lines.map(l => {{
        const href = baseUrl && l.seconds !== undefined ? `${{baseUrl}}&t=${{l.seconds}}s` : baseUrl;
        return `<div class="transcript-line"><a class="t-ts" href="${{href}}" target="_blank" rel="noopener noreferrer">[${{esc(l.timestamp)}}]</a><span>${{esc(l.text)}}</span></div>`;
      }}).join("");

      if (document.getElementById("autoScrollToggle").checked) {{
        pane.scrollTop = pane.scrollHeight;
      }}
    }}

    (function() {{
      const sessionAuth = sessionStorage.getItem("rann_session_active") || sessionStorage.getItem("durham_pol_auth");
      if (sessionAuth && (Date.now() - getLastActive() <= INACTIVITY_TIMEOUT_MS)) {{
        touchActivity();
        unlockLive();
      }}
    }})();
  </script>
</body>
</html>
"""
    live_html_path.write_text(live_html, encoding="utf-8")
    print(f"✓ Live Meeting split-pane page generated at: {live_html_path}")
    return str(live_html_path)

if __name__ == "__main__":
    generate_durhampolitics_page()
