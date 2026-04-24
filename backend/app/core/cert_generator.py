"""
GuardianLens — PDF Certificate Generator
Generates cryptographically-signable PDF certificates using ReportLab.
Includes scan metadata, verdict, breakdown table, and QR code linking back to scan.
"""
import logging
import uuid
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_certificate(scan_data: dict, output_dir: Path) -> str | None:
    """
    Generate a PDF certificate for the given scan result.

    Args:
        scan_data: dict with trust_score, verdict, filename, breakdown, scan_id, etc.
        output_dir: directory to save the PDF

    Returns:
        path to generated PDF, or None on failure
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import (
            HexColor, white, black
        )
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        scan_id = scan_data.get("scan_id", str(uuid.uuid4()))
        output_path = output_dir / f"{scan_id}_certificate.pdf"
        output_dir.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )

        styles = getSampleStyleSheet()

        # ── Colors ──────────────────────────────────────────
        bg_dark = HexColor("#0a0e1a")
        cyan = HexColor("#00d4ff")
        green = HexColor("#00ff88")
        yellow = HexColor("#ffd600")
        red = HexColor("#ff4d6d")
        muted = HexColor("#64748b")
        light = HexColor("#e2e8f0")

        verdict = scan_data.get("verdict", "UNKNOWN")
        trust_score = scan_data.get("trust_score", 0)
        verdict_color = {"AUTHENTIC": green, "SUSPICIOUS": yellow, "FORGED": red}.get(verdict, muted)

        # ── Custom Styles ────────────────────────────────────
        title_style = ParagraphStyle(
            "title", parent=styles["Heading1"],
            fontSize=22, textColor=cyan, alignment=TA_CENTER, spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            "subtitle", parent=styles["Normal"],
            fontSize=10, textColor=muted, alignment=TA_CENTER, spaceAfter=14
        )
        verdict_style = ParagraphStyle(
            "verdict", parent=styles["Normal"],
            fontSize=28, textColor=verdict_color, alignment=TA_CENTER,
            fontName="Helvetica-Bold", spaceAfter=4
        )
        score_style = ParagraphStyle(
            "score", parent=styles["Normal"],
            fontSize=16, textColor=light, alignment=TA_CENTER, spaceAfter=16
        )
        section_style = ParagraphStyle(
            "section", parent=styles["Normal"],
            fontSize=9, textColor=muted, fontName="Helvetica-Bold",
            spaceBefore=16, spaceAfter=6
        )
        body_style = ParagraphStyle(
            "body", parent=styles["Normal"],
            fontSize=10, textColor=light, alignment=TA_LEFT, spaceAfter=6
        )

        # ── Build Story ──────────────────────────────────────
        story = []

        # Header
        story.append(Paragraph("🛡 GuardianLens", title_style))
        story.append(Paragraph("AI Document Authentication Certificate", subtitle_style))
        story.append(Paragraph("Google Solution Challenge 2026 · SDG 16", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=cyan, spaceAfter=16))

        # Verdict block
        story.append(Paragraph(f"● {verdict}", verdict_style))
        story.append(Paragraph(f"Trust Score: {trust_score} / 100", score_style))

        story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#1e2d45"), spaceAfter=8))

        # Document info
        story.append(Paragraph("DOCUMENT DETAILS", section_style))
        info_data = [
            ["Filename", scan_data.get("filename", "N/A")],
            ["Document Type", scan_data.get("doc_type", "Other")],
            ["Detected Type", scan_data.get("doc_type_detected", "N/A")],
            ["Scan ID", scan_id],
            ["Analyzed At", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")],
            ["AI Model", scan_data.get("ai_model_used", "gemini-1.5-flash")],
            ["Confidence", f"{int(scan_data.get('confidence', 0) * 100)}%"],
        ]
        story.append(_build_table(info_data, light, muted, bg_dark, cyan))
        story.append(Spacer(1, 12))

        # Breakdown
        story.append(Paragraph("FORENSIC BREAKDOWN", section_style))
        breakdown = scan_data.get("breakdown", {})
        breakdown_data = [
            ["Metadata Integrity", f"{breakdown.get('metadata_integrity', '-')} / 100"],
            ["Visual Consistency", f"{breakdown.get('visual_consistency', '-')} / 100"],
            ["Content Coherence", f"{breakdown.get('content_coherence', '-')} / 100"],
            ["Font Analysis", f"{breakdown.get('font_analysis', '-')} / 100"],
            ["Seal & Stamp Check", f"{breakdown.get('seal_stamp_check', '-')} / 100"],
        ]
        story.append(_build_table(breakdown_data, light, muted, bg_dark, cyan))
        story.append(Spacer(1, 12))

        # Anomalies
        anomalies = scan_data.get("anomalies", [])
        story.append(Paragraph("ANOMALIES DETECTED", section_style))
        if anomalies:
            for a in anomalies:
                story.append(Paragraph(f"• {a}", body_style))
        else:
            story.append(Paragraph("✓ No significant anomalies detected", body_style))

        # Summary
        story.append(Spacer(1, 8))
        story.append(Paragraph("AI SUMMARY", section_style))
        story.append(Paragraph(scan_data.get("ai_summary", ""), body_style))

        # Footer
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#1e2d45"), spaceAfter=8))
        story.append(Paragraph(
            f"This certificate was generated by GuardianLens AI v2.0.0 · Scan ID: {scan_id}",
            subtitle_style
        ))
        story.append(Paragraph(
            "This report is for informational purposes only. Final verification should be performed by authorized personnel.",
            subtitle_style
        ))

        # QR code (optional)
        try:
            _add_qr(story, scan_id, output_dir)
        except Exception:
            pass

        doc.build(story)
        logger.info(f"Certificate generated: {output_path}")
        return str(output_path)

    except ImportError:
        logger.warning("reportlab not installed — certificate generation skipped")
        return None
    except Exception as e:
        logger.error(f"Certificate generation failed: {e}")
        return None


def _build_table(data: list, light, muted, bg_dark, cyan):
    """Build a styled 2-column info table."""
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors

    table = Table(data, colWidths=["40%", "60%"])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), HexColor("#111827")),
        ("BACKGROUND", (1, 0), (1, -1), HexColor("#161d2e")),
        ("TEXTCOLOR", (0, 0), (0, -1), muted),
        ("TEXTCOLOR", (1, 0), (1, -1), light),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [HexColor("#111827"), HexColor("#161d2e")]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#1e2d45")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _add_qr(story, scan_id: str, output_dir: Path):
    """Generate and embed QR code linking to the scan result."""
    import qrcode
    from reportlab.platypus import Image as RLImage

    url = f"https://guardianlens.app/scan/{scan_id}"
    qr = qrcode.make(url)
    qr_path = output_dir / f"{scan_id}_qr.png"
    qr.save(str(qr_path))

    story.append(RLImage(str(qr_path), width=80, height=80))


from reportlab.lib.colors import HexColor  # noqa: E402 — needed for table helper
