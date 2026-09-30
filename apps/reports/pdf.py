"""Génération des rapports SAVIO au format PDF (ReportLab Platypus).

Une fonction par rapport. Chaque fonction reçoit les données déjà
préparées par la vue (mêmes querysets/listes utilisés pour le rendu HTML)
et renvoie un objet ``HttpResponse`` prêt à être servi en téléchargement.

ReportLab est volontairement préféré à WeasyPrint : pas de dépendance
système (Cairo/Pango/GTK), fonctionne tel quel sous Windows.
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Iterable, Sequence

from django.http import HttpResponse
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BRAND_COLOR = colors.HexColor("#4154f1")
HEADER_BG = colors.HexColor("#eef2ff")
HEADER_FG = colors.HexColor("#1f2937")
ROW_ALT = colors.HexColor("#f8f9fc")
BORDER = colors.HexColor("#d8def0")
MUTED = colors.HexColor("#6b7280")


def _styles() -> dict:
    """Crée les styles Paragraph utilisés dans tous les rapports."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "SavioTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=BRAND_COLOR,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "SavioSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=MUTED,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "SavioH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=HEADER_FG,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "kpi_value": ParagraphStyle(
            "SavioKpiValue",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=HEADER_FG,
        ),
        "kpi_label": ParagraphStyle(
            "SavioKpiLabel",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=MUTED,
        ),
        "cell": ParagraphStyle(
            "SavioCell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
        ),
        "cell_right": ParagraphStyle(
            "SavioCellRight",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
        ),
        "cell_muted": ParagraphStyle(
            "SavioCellMuted",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            textColor=MUTED,
        ),
    }


def _on_page(canvas, doc):
    """Pied de page commun : numéro de page + horodatage."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    footer = "SAVIO · Généré le {ts} · Page {n}".format(
        ts=timezone.localtime().strftime("%d/%m/%Y %H:%M"),
        n=canvas.getPageNumber(),
    )
    canvas.drawString(15 * mm, 10 * mm, footer)
    canvas.restoreState()


def _make_doc(buffer: BytesIO, *, landscape_mode: bool = False) -> SimpleDocTemplate:
    pagesize = landscape(A4) if landscape_mode else A4
    return SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title="Rapport SAVIO",
        author="SAVIO",
    )


def _table_style(extra: Sequence[tuple] = ()) -> TableStyle:
    """Style commun pour les tableaux de données."""
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
    ]
    cmds.extend(extra)
    return TableStyle(cmds)


def _kpi_block(items: Sequence[tuple[str, str]], styles: dict) -> Table:
    """Bloc d'indicateurs (label + valeur) côte à côte."""
    cells = [
        [Paragraph(value, styles["kpi_value"]) for _, value in items],
        [Paragraph(label, styles["kpi_label"]) for label, _ in items],
    ]
    col_count = len(items)
    table = Table(cells, colWidths=[(180 * mm) / col_count] * col_count)
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
            ]
        )
    )
    return table


def _header(title: str, period: tuple[str, str], styles: dict) -> list:
    """En-tête commun : titre + sous-titre période."""
    start, end = period
    return [
        Paragraph(title, styles["title"]),
        Paragraph(
            f"Période : du <b>{_fmt_date(start)}</b> au <b>{_fmt_date(end)}</b>",
            styles["subtitle"],
        ),
    ]


def _fmt_date(value: str | datetime) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(value or "—")


def _response(buffer: BytesIO, filename: str) -> HttpResponse:
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _build(filename: str, story: list, *, landscape_mode: bool = False) -> HttpResponse:
    buffer = BytesIO()
    doc = _make_doc(buffer, landscape_mode=landscape_mode)
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return _response(buffer, filename)


# ---------------------------------------------------------------------------
# Rapport global
# ---------------------------------------------------------------------------

def build_global_pdf(
    *,
    start: str,
    end: str,
    total: int,
    open_count: int,
    closed_count: int,
    by_status: Iterable[dict],
    by_priority: Iterable[dict],
    evolution: Iterable[dict],
) -> HttpResponse:
    styles = _styles()
    story: list = []
    story.extend(_header("Rapport global", (start, end), styles))
    story.append(
        _kpi_block(
            [
                ("Demandes sur la période", str(total)),
                ("En cours", str(open_count)),
                ("Clôturées", str(closed_count)),
            ],
            styles,
        )
    )
    story.append(Spacer(1, 10))

    # Répartition par statut
    story.append(Paragraph("Répartition par statut", styles["h2"]))
    rows = [["Statut", "Nombre"]]
    for r in by_status:
        rows.append([Paragraph(str(r["label"]), styles["cell"]), str(r["total"])])
    if len(rows) == 1:
        rows.append(["Aucune donnée.", ""])
    table = Table(rows, colWidths=[120 * mm, 60 * mm])
    table.setStyle(
        _table_style(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    story.append(table)

    # Répartition par priorité
    story.append(Paragraph("Répartition par priorité", styles["h2"]))
    rows = [["Priorité", "Nombre"]]
    for r in by_priority:
        rows.append([Paragraph(str(r["label"]), styles["cell"]), str(r["total"])])
    if len(rows) == 1:
        rows.append(["Aucune donnée.", ""])
    table = Table(rows, colWidths=[120 * mm, 60 * mm])
    table.setStyle(_table_style([("ALIGN", (1, 0), (1, -1), "RIGHT")]))
    story.append(table)

    # Évolution quotidienne
    story.append(Paragraph("Évolution quotidienne", styles["h2"]))
    rows = [["Date", "Demandes créées"]]
    for r in evolution:
        rows.append([_fmt_date(r["day"]), str(r["total"])])
    if len(rows) == 1:
        rows.append(["Aucune activité sur la période.", ""])
    table = Table(rows, colWidths=[120 * mm, 60 * mm], repeatRows=1)
    table.setStyle(_table_style([("ALIGN", (1, 0), (1, -1), "RIGHT")]))
    story.append(table)

    return _build(f"rapport-global_{start}_{end}.pdf", story)


# ---------------------------------------------------------------------------
# Rapport demandes
# ---------------------------------------------------------------------------

def build_tickets_pdf(
    *,
    start: str,
    end: str,
    total: int,
    tickets: Iterable,
    status_filter: str | None,
    priority_filter: str | None,
) -> HttpResponse:
    styles = _styles()
    story: list = []
    story.extend(_header("Rapport des demandes SAV", (start, end), styles))

    # Récap des filtres actifs
    filters_bits = []
    if status_filter:
        filters_bits.append(f"statut = <b>{status_filter}</b>")
    if priority_filter:
        filters_bits.append(f"priorité = <b>{priority_filter}</b>")
    filters_line = " · ".join(filters_bits) if filters_bits else "aucun filtre supplémentaire"
    story.append(
        Paragraph(
            f"{total} demande(s) trouvée(s) · {filters_line}",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 4))

    rows = [
        ["Référence", "Sujet", "Client", "Technicien", "Statut", "Priorité", "Créée le"]
    ]
    for t in tickets:
        rows.append(
            [
                Paragraph(str(t.reference), styles["cell"]),
                Paragraph(_truncate(t.subject, 60), styles["cell"]),
                Paragraph(
                    str(getattr(t.client, "display_name", "") or t.client),
                    styles["cell"],
                ),
                Paragraph(
                    str(t.assigned_to) if t.assigned_to else "—",
                    styles["cell"] if t.assigned_to else styles["cell_muted"],
                ),
                Paragraph(t.get_status_display(), styles["cell"]),
                Paragraph(t.get_priority_display(), styles["cell"]),
                Paragraph(
                    timezone.localtime(t.created_at).strftime("%d/%m/%Y %H:%M"),
                    styles["cell"],
                ),
            ]
        )
    if len(rows) == 1:
        rows.append([Paragraph("Aucun résultat.", styles["cell_muted"])] + [""] * 6)

    # Largeurs adaptées au paysage A4 (utile = ~267 mm)
    col_widths = [25 * mm, 70 * mm, 45 * mm, 40 * mm, 25 * mm, 25 * mm, 30 * mm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(_table_style())
    story.append(table)

    return _build(
        f"rapport-demandes_{start}_{end}.pdf",
        story,
        landscape_mode=True,
    )


# ---------------------------------------------------------------------------
# Rapport par technicien
# ---------------------------------------------------------------------------

def build_by_technician_pdf(
    *,
    start: str,
    end: str,
    rows: Iterable,
    unassigned: int,
) -> HttpResponse:
    styles = _styles()
    story: list = []
    story.extend(_header("Rapport par technicien", (start, end), styles))
    story.append(
        Paragraph(
            f"Demandes non affectées sur la période : <b>{unassigned}</b>",
            styles["subtitle"],
        )
    )

    data = [["Technicien", "Spécialité", "Total", "En cours", "Clôturées"]]
    for r in rows:
        name = f"{(r.last_name or '').upper()} {r.first_name or ''}".strip()
        if not r.is_active:
            name = f"{name}  (inactif)"
        data.append(
            [
                Paragraph(name or "—", styles["cell"]),
                Paragraph(r.specialty or "—", styles["cell"]),
                str(getattr(r, "total", 0) or 0),
                str(getattr(r, "open_tickets", 0) or 0),
                str(getattr(r, "closed_tickets", 0) or 0),
            ]
        )
    if len(data) == 1:
        data.append(
            [Paragraph("Aucun technicien.", styles["cell_muted"])] + [""] * 4
        )

    col_widths = [70 * mm, 50 * mm, 20 * mm, 20 * mm, 20 * mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        _table_style(
            [
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(table)

    return _build(f"rapport-techniciens_{start}_{end}.pdf", story)


# ---------------------------------------------------------------------------
# Rapport par client
# ---------------------------------------------------------------------------

def build_by_client_pdf(
    *,
    start: str,
    end: str,
    rows: Iterable,
) -> HttpResponse:
    styles = _styles()
    story: list = []
    story.extend(_header("Rapport par client", (start, end), styles))

    data = [["Client", "Type", "Ville", "Total", "En cours", "Clôturées"]]
    for r in rows:
        data.append(
            [
                Paragraph(str(r), styles["cell"]),
                Paragraph(
                    r.get_type_display() if hasattr(r, "get_type_display") else "—",
                    styles["cell"],
                ),
                Paragraph(r.city or "—", styles["cell"]),
                str(getattr(r, "total", 0) or 0),
                str(getattr(r, "open_tickets", 0) or 0),
                str(getattr(r, "closed_tickets", 0) or 0),
            ]
        )
    if len(data) == 1:
        data.append(
            [Paragraph("Aucune activité client sur la période.", styles["cell_muted"])]
            + [""] * 5
        )

    col_widths = [60 * mm, 30 * mm, 35 * mm, 20 * mm, 20 * mm, 20 * mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        _table_style(
            [
                ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(table)

    return _build(f"rapport-clients_{start}_{end}.pdf", story)


# ---------------------------------------------------------------------------
# Petite utilité
# ---------------------------------------------------------------------------

def _truncate(value: str, length: int) -> str:
    if value is None:
        return ""
    s = str(value)
    return s if len(s) <= length else s[: length - 1] + "…"
