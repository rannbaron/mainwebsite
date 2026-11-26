#!/usr/bin/env python3
"""
Ingests extracted timestamped agenda items & vote/debate timestamps into durham_politics.db,
generates hyperlinked Executive Summary PDFs for every meeting via ReportLab,
and regenerates the static Durham Politics Tracker website.
"""

import html as html_lib
import json
import re
import sys
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_SCRIPT_DIR = Path(__file__).resolve().parent
_PKG_PARENT = _SCRIPT_DIR.parent.parent
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))
if "/home/rann/src" not in sys.path and Path("/home/rann/src").exists():
    sys.path.insert(0, "/home/rann/src")
from durham_politics_tracker.config import BODIES, OUTPUT_DIR
from durham_politics_tracker.database import DurhamPoliticsDB
from durham_politics_tracker.site_generator import generate_durhampolitics_page

EXTRACTED_PATH = _SCRIPT_DIR / "agenda_timestamps_extracted.json"
VOTE_DISCUSSIONS_PATH = _SCRIPT_DIR / "vote_discussions_extracted.json"
SUMMARIES_DIR = OUTPUT_DIR / "summaries"


def hhmmss_to_seconds(ts: str) -> Optional[int]:
    if not ts:
        return None
    m = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", str(ts).strip())
    if not m:
        return None
    if m.group(3) is not None:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    return int(m.group(1)) * 60 + int(m.group(2))


def format_seconds(secs: Optional[int]) -> str:
    if secs is None:
        return ""
    secs = max(0, int(secs))
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def esc(text: str) -> str:
    return html_lib.escape(str(text or ""), quote=False)


def build_meeting_pdf(meeting: dict, out_path: Path):
    """Generates a clean, hyperlinked Executive Summary PDF for one meeting."""
    body_info = BODIES.get(meeting["body_id"], {})
    body_name = body_info.get("name", meeting["body_id"].upper())
    video_url = meeting.get("video_url") or ""

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"{meeting['title']} — Executive Summary",
        author="Durham Politics Tracker",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle", parent=styles["Heading1"],
        fontName="Helvetica-Bold", fontSize=16, leading=20,
        textColor=colors.HexColor("#0f172a"), spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=14,
        textColor=colors.HexColor("#475569"), spaceAfter=10,
    )
    h2_style = ParagraphStyle(
        "SecH2", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=12, leading=16,
        textColor=colors.HexColor("#1e3a8a"), spaceBefore=12, spaceAfter=6,
    )
    item_title_style = ParagraphStyle(
        "ItemTitle", parent=styles["Heading3"],
        fontName="Helvetica-Bold", fontSize=10.5, leading=14,
        textColor=colors.HexColor("#0f172a"), spaceBefore=8, spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "BodyTxt", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9.5, leading=13.5,
        textColor=colors.HexColor("#1e293b"), spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "MetaTxt", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, leading=12.5,
        textColor=colors.HexColor("#334155"),
    )
    vote_box_style = ParagraphStyle(
        "VoteTxt", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, leading=13,
        textColor=colors.HexColor("#1e293b"), leftIndent=10, spaceAfter=4,
    )

    story = []
    story.append(Paragraph(esc(body_name.upper()), ParagraphStyle(
        "Kicker", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=8.5, textColor=colors.HexColor("#2563eb"), spaceAfter=2,
    )))
    story.append(Paragraph(esc(meeting["title"]), title_style))
    story.append(Paragraph(
        f"Executive Summary of Agenda Discussions &amp; Formal Votes &bull; {esc(meeting['date'])}",
        subtitle_style,
    ))

    # Metadata block
    video_link_html = (
        f'<a href="{esc(video_url)}" color="#1d4ed8"><u>Watch Full Meeting Video on YouTube</u></a>'
        if video_url else "N/A"
    )
    meta_rows = [
        [Paragraph("<b>Date:</b> " + esc(meeting["date"]), meta_style),
         Paragraph("<b>Type:</b> " + esc(meeting.get("meeting_type") or "Regular Meeting"), meta_style)],
        [Paragraph("<b>Presiding Chair:</b> " + esc(meeting.get("presiding_chair") or "Not specified"), meta_style),
         Paragraph("<b>Duration:</b> " + esc(meeting.get("duration") or "N/A"), meta_style)],
        [Paragraph("<b>Recorded Votes:</b> " + str(len(meeting.get("votes", []))), meta_style),
         Paragraph("<b>Full Video:</b> " + video_link_html, meta_style)],
    ]
    meta_tbl = Table(meta_rows, colWidths=[3.3 * inch, 3.7 * inch])
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 10))

    # Executive Overview
    story.append(Paragraph("Executive Overview", h2_style))
    story.append(Paragraph(esc(meeting.get("executive_summary") or "No overview available."), body_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=6, spaceAfter=6))

    # Agenda Items Breakdown
    agenda_items = meeting.get("agenda_items") or []
    story.append(Paragraph(f"Agenda Items &amp; Topic Discussions ({len(agenda_items)})", h2_style))
    if not agenda_items:
        story.append(Paragraph(
            "Detailed timestamped agenda breakdown unavailable (auto-captions/transcript not available for this recording).",
            body_style,
        ))
    else:
        for idx, ag in enumerate(agenda_items, 1):
            num_lbl = f"{ag['item_number']}: " if ag.get("item_number") else f"Topic {idx}: "
            ts_lbl = ag.get("timestamp_label") or format_seconds(ag.get("start_seconds"))
            ts_url = ag.get("video_timestamp_url") or video_url
            ts_html = (
                f' &nbsp; <a href="{esc(ts_url)}" color="#1d4ed8"><u>[Watch @ {esc(ts_lbl)}]</u></a>'
                if ts_lbl and ts_url else ""
            )
            cat = ag.get("category") or ""
            cat_html = f' <font size="8" color="#64748b">({esc(cat)})</font>' if cat else ""
            story.append(Paragraph(f"{esc(num_lbl)}{esc(ag['title'])}{cat_html}{ts_html}", item_title_style))
            if ag.get("discussion_summary"):
                story.append(Paragraph(f"<b>Discussion:</b> {esc(ag['discussion_summary'])}", body_style))
            if ag.get("vote_summary"):
                story.append(Paragraph(f"<b>Vote / Action:</b> {esc(ag['vote_summary'])}", vote_box_style))

    # Formal Votes Table / List
    votes = meeting.get("votes") or []
    if votes:
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=8, spaceAfter=6))
        story.append(Paragraph(f"Formal Votes Recorded ({len(votes)})", h2_style))
        for idx, v in enumerate(votes, 1):
            ts_lbl = v.get("timestamp_label") or format_seconds(v.get("timestamp_seconds"))
            ts_url = v.get("video_timestamp_url") or video_url
            ts_html = (
                f' &nbsp; <a href="{esc(ts_url)}" color="#1d4ed8"><u>[@ {esc(ts_lbl)}]</u></a>'
                if ts_lbl and ts_url else ""
            )
            outcome_color = "#15803d" if "pass" in (v.get("outcome") or "").lower() else "#b91c1c"
            story.append(Paragraph(
                f"{idx}. {esc(v['item_title'])} "
                f'<font color="{outcome_color}"><b>[{esc(v.get("outcome"))} — {esc(v.get("tally"))}]</b></font>{ts_html}',
                item_title_style,
            ))
            if v.get("discussion_detail"):
                story.append(Paragraph(f"<b>Discussion &amp; Deliberation:</b> {esc(v['discussion_detail'])}", body_style))
            details = []
            if v.get("mover"):
                details.append(f"<b>Mover:</b> {esc(v['mover'])}")
            if v.get("seconder"):
                details.append(f"<b>Seconder:</b> {esc(v['seconder'])}")
            if v.get("ayes"):
                details.append(f"<b>Ayes:</b> {esc(', '.join(v['ayes']))}")
            nays_clean = [n for n in (v.get("nays") or []) if n and str(n).strip().lower() not in ("none", "n/a", "0")]
            if nays_clean:
                details.append(f'<font color="#b91c1c"><b>Nays:</b> {esc(", ".join(nays_clean))}</font>')
            if v.get("notes"):
                details.append(f"<b>Notes:</b> {esc(v['notes'])}")
            if details:
                story.append(Paragraph(" | ".join(details), vote_box_style))

    # Key Policy Disagreements
    disagreements = meeting.get("disagreements") or []
    if disagreements:
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=8, spaceAfter=6))
        story.append(Paragraph(f"Notable Policy Debates &amp; Disagreements ({len(disagreements)})", h2_style))
        for idx, d in enumerate(disagreements, 1):
            ts_lbl = d.get("timestamp_label") or format_seconds(d.get("timestamp_seconds"))
            ts_url = d.get("video_timestamp_url") or video_url
            ts_html = (
                f' &nbsp; <a href="{esc(ts_url)}" color="#1d4ed8"><u>[@ {esc(ts_lbl)}]</u></a>'
                if ts_lbl and ts_url else ""
            )
            story.append(Paragraph(f"{idx}. {esc(d['issue'])}{ts_html}", item_title_style))
            story.append(Paragraph(esc(d.get("summary") or ""), body_style))
            sa = d.get("side_a", {})
            sb = d.get("side_b", {})
            if sa.get("position"):
                story.append(Paragraph(
                    f"<b>Side A ({esc(sa['position'])}):</b> {esc('; '.join(sa.get('arguments') or []))} "
                    f"<i>[{esc(', '.join(sa.get('members') or []))}]</i>",
                    vote_box_style,
                ))
            if sb.get("position"):
                story.append(Paragraph(
                    f"<b>Side B ({esc(sb['position'])}):</b> {esc('; '.join(sb.get('arguments') or []))} "
                    f"<i>[{esc(', '.join(sb.get('members') or []))}]</i>",
                    vote_box_style,
                ))
            if d.get("resolution"):
                story.append(Paragraph(f"<b>Resolution:</b> {esc(d['resolution'])}", vote_box_style))

    doc.build(story)


def main():
    db = DurhamPoliticsDB()

    extracted = json.loads(EXTRACTED_PATH.read_text(encoding="utf-8")) if EXTRACTED_PATH.exists() else {}
    vote_discussions = json.loads(VOTE_DISCUSSIONS_PATH.read_text(encoding="utf-8")) if VOTE_DISCUSSIONS_PATH.exists() else {}
    print(f"Loaded extracted agenda/timestamps for {len(extracted)} meetings and detailed discussions for {len(vote_discussions)} votes.")

    agenda_count = 0
    vote_ts_count = 0
    dis_ts_count = 0
    vote_disc_count = 0

    with db.get_connection() as conn:
        cur = conn.cursor()
        for vote_id, detail in vote_discussions.items():
            if detail:
                cur.execute("UPDATE votes SET discussion_detail = ? WHERE id = ?", (detail, vote_id))
                vote_disc_count += 1
        for meeting_id, payload in extracted.items():
            # Replace agenda items for this meeting
            cur.execute("DELETE FROM agenda_items WHERE meeting_id = ?", (meeting_id,))
            for idx, ag in enumerate(payload.get("agenda_items", []), 1):
                secs = hhmmss_to_seconds(ag.get("timestamp_hhmmss", ""))
                lbl = format_seconds(secs) if secs is not None else (ag.get("timestamp_hhmmss") or "")
                cur.execute("""
                    INSERT OR REPLACE INTO agenda_items (
                        id, meeting_id, item_number, title, category,
                        description, discussion_summary, start_seconds, timestamp_label, vote_summary
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"ag_{meeting_id}_{idx:02d}",
                    meeting_id,
                    ag.get("item_number", f"Topic {idx}"),
                    ag.get("title", "Agenda Topic"),
                    ag.get("category", "Governance & Transparency"),
                    "",
                    ag.get("discussion_summary", ""),
                    secs,
                    lbl,
                    ag.get("vote_summary", ""),
                ))
                agenda_count += 1

            for vt in payload.get("vote_timestamps", []):
                secs = hhmmss_to_seconds(vt.get("timestamp_hhmmss", ""))
                if secs is not None:
                    cur.execute(
                        "UPDATE votes SET timestamp_seconds = ?, timestamp_label = ? WHERE id = ?",
                        (secs, format_seconds(secs), vt["vote_id"]),
                    )
                    vote_ts_count += 1

            for dt in payload.get("disagreement_timestamps", []):
                secs = hhmmss_to_seconds(dt.get("timestamp_hhmmss", ""))
                if secs is not None:
                    cur.execute(
                        "UPDATE sources_of_disagreement SET timestamp_seconds = ?, timestamp_label = ? WHERE id = ?",
                        (secs, format_seconds(secs), dt["disagreement_id"]),
                    )
                    dis_ts_count += 1

        # Set summary_pdf_url for all meetings
        all_ids = [r[0] for r in cur.execute("SELECT id FROM meetings").fetchall()]
        for m_id in all_ids:
            cur.execute(
                "UPDATE meetings SET summary_pdf_url = ? WHERE id = ?",
                (f"/durhampolitics/summaries/{m_id}.pdf", m_id),
            )

    print(f"DB updated: {agenda_count} agenda items, {vote_ts_count} vote timestamps, {dis_ts_count} debate timestamps.")

    # Export full dataset and build PDFs for every meeting
    dataset = db.export_full_dataset()
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    pdf_count = 0
    for mtg in dataset["meetings"]:
        out_pdf = SUMMARIES_DIR / f"{mtg['id']}.pdf"
        build_meeting_pdf(mtg, out_pdf)
        pdf_count += 1
    print(f"Generated {pdf_count} executive summary PDFs in {SUMMARIES_DIR}")

    out_html = generate_durhampolitics_page()
    print(f"Regenerated website at: {out_html}")


if __name__ == "__main__":
    main()
