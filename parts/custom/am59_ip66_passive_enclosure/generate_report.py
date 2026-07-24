"""Generate the release-style AM59 IP66 concept report PDF."""

# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PARAMS = json.loads((HERE / "params.json").read_text(encoding="utf-8"))
OUTPUT = REPO / "output" / "pdf" / "AM59_IP66_Low_CG_Concept_Report.pdf"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#246B8E")
TEAL = colors.HexColor("#168B83")
ORANGE = colors.HexColor("#D9822B")
INK = colors.HexColor("#24313C")
MUTED = colors.HexColor("#637381")
LIGHT = colors.HexColor("#EAF0F4")
PALE_TEAL = colors.HexColor("#E4F4F1")
PALE_ORANGE = colors.HexColor("#FBEFDF")
WHITE = colors.white
RED = colors.HexColor("#A33A36")

PAGE_W, PAGE_H = letter
MARGIN_X = 0.55 * inch
MARGIN_TOP = 0.55 * inch
MARGIN_BOTTOM = 0.55 * inch


def _styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.3,
            leading=11.2,
            textColor=INK,
            spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=6.7,
            leading=8.6,
            textColor=INK,
        ),
        "tiny": ParagraphStyle(
            "Tiny",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=5.8,
            leading=7.2,
            textColor=INK,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=21,
            textColor=NAVY,
            spaceBefore=2,
            spaceAfter=9,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=BLUE,
            spaceBefore=8,
            spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=sample["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=8.7,
            leading=10.5,
            textColor=NAVY,
            spaceBefore=5,
            spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.0,
            leading=10.5,
            textColor=INK,
            leftIndent=11,
            firstLineIndent=-7,
            bulletIndent=0,
            spaceAfter=3,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=sample["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=6.5,
            leading=8,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=5,
        ),
        "metric": ParagraphStyle(
            "Metric",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=17,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=6.2,
            leading=7.2,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=27,
            leading=29,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=12,
            leading=15,
            textColor=BLUE,
            alignment=TA_LEFT,
        ),
    }


STYLES = _styles()


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"- {text}", STYLES["bullet"])


def section(title: str, number: str | None = None) -> Paragraph:
    label = f"{number}. {title}" if number else title
    return p(label, "h1")


def subsection(title: str) -> Paragraph:
    return p(title, "h2")


def callout(title: str, body: str, tone: str = "teal") -> Table:
    bg = PALE_TEAL if tone == "teal" else PALE_ORANGE
    edge = TEAL if tone == "teal" else ORANGE
    data = [[p(f"<b>{title}</b><br/>{body}", "body")]]
    table = Table(data, colWidths=[PAGE_W - 2 * MARGIN_X])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.8, edge),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def table(
    rows: list[list[object]],
    widths: list[float],
    *,
    font_size: float = 6.7,
    header_rows: int = 1,
    highlight_rows: tuple[int, ...] = (),
    alignments: dict[int, str] | None = None,
) -> Table:
    cooked: list[list[object]] = []
    cell_style = ParagraphStyle(
        "Cell",
        parent=STYLES["small"],
        fontSize=font_size,
        leading=font_size + 1.7,
    )
    header_style = ParagraphStyle(
        "CellHeader",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=WHITE,
    )
    for row_index, row in enumerate(rows):
        cooked.append(
            [
                value
                if hasattr(value, "wrap")
                else Paragraph(str(value), header_style if row_index < header_rows else cell_style)
                for value in row
            ]
        )
    result = Table(cooked, colWidths=widths, repeatRows=header_rows)
    commands: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C4CC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for row_index in range(header_rows, len(rows)):
        if row_index % 2 == 0:
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), LIGHT))
    for row_index in highlight_rows:
        commands.append(("BACKGROUND", (0, row_index), (-1, row_index), PALE_TEAL))
        commands.append(("LINEABOVE", (0, row_index), (-1, row_index), 1.0, TEAL))
        commands.append(("LINEBELOW", (0, row_index), (-1, row_index), 1.0, TEAL))
    if alignments:
        for column, alignment in alignments.items():
            commands.append(("ALIGN", (column, header_rows), (column, -1), alignment))
    result.setStyle(TableStyle(commands))
    return result


def image(path: Path, max_width: float, max_height: float) -> Image:
    item = Image(str(path))
    scale = min(max_width / item.imageWidth, max_height / item.imageHeight)
    item.drawWidth = item.imageWidth * scale
    item.drawHeight = item.imageHeight * scale
    return item


def metric_strip(metrics: list[tuple[str, str]]) -> Table:
    row = []
    for value, label in metrics:
        row.append(
            Table(
                [[p(value, "metric")], [p(label, "metric_label")]],
                colWidths=[(PAGE_W - 2 * MARGIN_X) / len(metrics)],
            )
        )
    result = Table([row], colWidths=[(PAGE_W - 2 * MARGIN_X) / len(metrics)] * len(metrics))
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C4CC")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C4CC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return result


def heat_flow_diagram() -> Drawing:
    drawing = Drawing(500, 124)
    boxes = [
        (5, 75, 92, 36, NAVY, "AM59 RF/DC", "200 W severe basis"),
        (127, 75, 92, 36, BLUE, "OEM sink", "180 W wet heat"),
        (249, 75, 92, 36, TEAL, "Wet airflow", "3 fans / 181.8 W"),
        (371, 75, 124, 36, colors.HexColor("#4B8063"), "Outdoor air", "45 C design ambient"),
        (5, 12, 100, 36, ORANGE, "Dry sources", "20+15+3+5+2 W"),
        (150, 12, 110, 36, colors.HexColor("#B56D23"), "Dry chamber", "45 W / 51.75 W"),
        (305, 12, 95, 36, BLUE, "Finned door", "UA = 2.75 W/K"),
        (440, 12, 55, 36, colors.HexColor("#4B8063"), "Air", "63.8 C"),
    ]
    for x, y, width, height, fill, title, subtitle in boxes:
        drawing.add(Rect(x, y, width, height, rx=4, ry=4, fillColor=fill, strokeColor=None))
        drawing.add(
            String(
                x + width / 2,
                y + 22,
                title,
                fontName="Helvetica-Bold",
                fontSize=7.4,
                fillColor=WHITE,
                textAnchor="middle",
            )
        )
        drawing.add(
            String(
                x + width / 2,
                y + 9,
                subtitle,
                fontName="Helvetica",
                fontSize=5.8,
                fillColor=WHITE,
                textAnchor="middle",
            )
        )

    def arrow(x1: float, y: float, x2: float, color: colors.Color) -> None:
        drawing.add(Line(x1, y, x2 - 6, y, strokeColor=color, strokeWidth=1.8))
        drawing.add(
            Polygon([x2 - 6, y - 4, x2, y, x2 - 6, y + 4], fillColor=color, strokeColor=None)
        )

    arrow(97, 93, 127, BLUE)
    arrow(219, 93, 249, TEAL)
    arrow(341, 93, 371, TEAL)
    arrow(105, 30, 150, ORANGE)
    arrow(260, 30, 305, BLUE)
    arrow(400, 30, 440, BLUE)
    drawing.add(
        String(
            250,
            57,
            "Only the lower branch crosses or originates inside the IP66 dry boundary.",
            fontName="Helvetica-Oblique",
            fontSize=6.8,
            fillColor=MUTED,
            textAnchor="middle",
        )
    )
    return drawing


def _header_footer(canvas, doc) -> None:
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(LIGHT)
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN_X, PAGE_H - 0.37 * inch, PAGE_W - MARGIN_X, PAGE_H - 0.37 * inch)
        canvas.setFont("Helvetica-Bold", 6.4)
        canvas.setFillColor(NAVY)
        canvas.drawString(MARGIN_X, PAGE_H - 0.29 * inch, "AM59 IP66 LOW-CG OUTDOOR ENCLOSURE")
        canvas.setFont("Helvetica", 6.2)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 0.29 * inch, "V4 PRELIMINARY CONCEPT")
    canvas.setStrokeColor(LIGHT)
    canvas.line(MARGIN_X, 0.38 * inch, PAGE_W - MARGIN_X, 0.38 * inch)
    canvas.setFont("Helvetica", 6.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        MARGIN_X, 0.24 * inch, "Architecture review - prototype and vendor gates required"
    )
    canvas.drawRightString(PAGE_W - MARGIN_X, 0.24 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _cover(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - 0.16 * inch, PAGE_W, 0.16 * inch, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, 0, 0.18 * inch, PAGE_H, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 6.5)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(
        PAGE_W - MARGIN_X, 0.27 * inch, "24 JULY 2026  |  REVISION V4  |  PRELIMINARY"
    )
    canvas.restoreState()


def build_story() -> list:
    story: list = []
    hero = HERE / "references" / "views" / "am59_ip66_passive_v4_transparent_iso.png"
    exploded = HERE / "references" / "views" / "am59_ip66_passive_v4_service_exploded_iso.png"
    front = HERE / "references" / "views" / "am59_ip66_passive_v4_transparent_front.png"

    # Cover
    story.extend(
        [
            Spacer(1, 0.18 * inch),
            p("AM59 IP66", "cover_title"),
            p("LOW-CENTER-OF-GRAVITY<br/>OUTDOOR ENCLOSURE", "cover_title"),
            p(
                "First-principles concept, CAD, thermal budget, mass/CG, sealing, and qualification plan",
                "cover_sub",
            ),
            Spacer(1, 0.13 * inch),
            image(hero, 7.35 * inch, 4.0 * inch),
            Spacer(1, 0.08 * inch),
            metric_strip(
                [
                    ("7.64 kg", "EMPTY MASS"),
                    ("153 mm", "CG ABOVE DATUM"),
                    ("45 W", "DRY HEAT"),
                    ("IP66", "ASSEMBLY TARGET"),
                    ("$2.35-4.50k", "PROTO ROM"),
                ]
            ),
            Spacer(1, 0.12 * inch),
            callout(
                "Selected architecture",
                "The intact AM59 straddles a welded dry bulkhead. Its electronics and two DIN rails stay dry; its complete OEM heatsink/fan bank stays outside in a drained rain hood. Passive walls reject only the 45 W remaining inside.",
            ),
            PageBreak(),
        ]
    )

    # Decision
    story.extend(
        [
            section("Decision and requirements", "1"),
            callout(
                "Recommendation",
                "<b>Proceed with Architecture A as the prototype basis.</b> Do not purchase an enclosure cooler. First close the AM59 case-seal, dry/wet calorimetry, and moisture-protected fan gates.",
            ),
            subsection("Why this architecture wins"),
            bullet(
                "It keeps every unrated electronic surface and all future DIN equipment behind one compact IP66 dry boundary."
            ),
            bullet(
                "It keeps the supplied OEM heatsink and fan geometry intact instead of inventing an unapproved thermal interface."
            ),
            bullet(
                "It sizes cabin cooling for 45 W, not the AM59's full approximately 200 W electrical input."
            ),
            bullet(
                "Its passive safe state has no filter, cabin fan, TEC, condensate drain, or active-cooling failure mode."
            ),
            bullet(
                "The provisional axis is placed through the assembly's mass balance: empty radial CG is 0.91 mm."
            ),
            subsection("Explicitly outside this revision"),
            p(
                "No connector ports, RF feedthroughs, pressure vent, mast adapters, rotator mounting hardware, or final load-transfer structure are designed. Representative sealed blanks are used only in qualification planning."
            ),
            subsection("Source hierarchy"),
            table(
                [
                    ["Priority", "Source", "Controls"],
                    [
                        "1",
                        "AM59-005D.pdf",
                        "Model electrical limits, temperatures, outline callouts, nominal mass",
                    ],
                    [
                        "2",
                        "AM59-3S-64-64.STEP",
                        "Exact supplied packaging keep-out and assembly configuration",
                    ],
                    [
                        "3",
                        "Supplied Seifert/Hoffman PDFs and STEPs",
                        "Cooler ratings and exact local package envelopes",
                    ],
                    [
                        "4",
                        "V4 calculations and CAD",
                        "Preliminary architecture estimates; physical test controls",
                    ],
                ],
                [0.5 * inch, 2.3 * inch, 4.05 * inch],
                font_size=7.0,
                alignments={0: "CENTER"},
            ),
            Spacer(1, 0.08 * inch),
            p(
                "<b>Status:</b> architecture-review and prototype-quotation quality. Production release is prohibited until Section 11 gates close.",
                "small",
            ),
            PageBreak(),
        ]
    )

    # Architecture trade
    story.extend(
        [
            section("Quantified architecture trade", "2"),
            p(
                "The penalty is a transparent screening metric. Lower is better: 4x weather risk + 4x vendor-interface risk + 2x thermal risk + 1.5x mass kg + 0.025x CG-Z mm + 12x frontal area m2 + 0.0005x prototype USD - serviceability. Hard gates still control."
            ),
            table(
                [
                    [
                        "ID",
                        "Architecture",
                        "Dry W",
                        "kg",
                        "CG-Z",
                        "Radial",
                        "Front m2",
                        "ROM",
                        "W/V/T",
                        "Svc",
                        "Penalty",
                    ],
                    [
                        "A",
                        "Intact AM59 straddles sealed bulkhead; wet OEM sink/fans; passive dry chamber",
                        "45",
                        "7.64",
                        "153",
                        "0.91",
                        "0.147",
                        "$2.85k",
                        "2/3/3",
                        "4",
                        "40.48",
                    ],
                    [
                        "B",
                        "Vendor-authorized body/sink split at cold wall",
                        "30",
                        "6.6",
                        "134",
                        "6",
                        "0.135",
                        "$3.30k",
                        "2/5/2",
                        "3",
                        "45.52",
                    ],
                    [
                        "C",
                        "Entire AM59 in ventilated wet bay; separate dry DIN pod",
                        "23",
                        "6.0",
                        "132",
                        "5",
                        "0.140",
                        "$2.20k",
                        "5/4/2",
                        "5",
                        "50.08",
                    ],
                    [
                        "D",
                        "Complete AM59 in sealed active-cooled chamber",
                        "225",
                        "14.0",
                        "205",
                        "25",
                        "0.200",
                        "$5.20k",
                        "2/2/3",
                        "3",
                        "50.12",
                    ],
                ],
                [
                    0.25 * inch,
                    2.25 * inch,
                    0.37 * inch,
                    0.35 * inch,
                    0.42 * inch,
                    0.42 * inch,
                    0.5 * inch,
                    0.48 * inch,
                    0.47 * inch,
                    0.3 * inch,
                    0.48 * inch,
                ],
                font_size=5.45,
                highlight_rows=(1,),
                alignments={
                    0: "CENTER",
                    2: "RIGHT",
                    3: "RIGHT",
                    4: "RIGHT",
                    5: "RIGHT",
                    6: "RIGHT",
                    7: "RIGHT",
                    8: "CENTER",
                    9: "CENTER",
                    10: "RIGHT",
                },
            ),
            subsection("Architecture A - selected"),
            p(
                "The only amplifier modification is an external case-contacting transition boot and support clamp. The electronics remain dry; the intact OEM sink/fans remain wet. Risks are localized to a measurable seal band, orientation/support approval, fan environmental build, and calorimetry."
            ),
            subsection("Architecture B - best theoretical mass/CG, not releasable"),
            p(
                "The AM59 specification says a modular form is available for OEM integration. A body/sink separation could reduce mass and CG, but the supplied data contain no modular-interface drawing, TIM, flatness, fastener torque, structural rating, or warranty approval. It remains a vendor inquiry."
            ),
            subsection("Architecture C - rejected"),
            p(
                "A rain hood is not dust-tight. Neither the complete AM59 nor the standard installed fan build has a supplied outdoor/IP rating, so placing the entire amplifier in an airflow-open bay cannot support IP66 electronics reliability."
            ),
            subsection("Architecture D - rejected"),
            p(
                "It violates the no-heatsink-inside requirement and turns approximately 225 W into a cabin load, forcing large closed-loop cooling with severe mass, CG, power, wind, cost, and condensation penalties."
            ),
            PageBreak(),
        ]
    )

    # Exact amplifier / heat
    story.extend(
        [
            section("Exact amplifier inspection and heat split", "3"),
            table(
                [
                    ["AM59-3S-64-64 model datum", "Value"],
                    ["Frequency", "2998 MHz +/-20 MHz"],
                    ["Typical peak RF output", "+64 dBm = 2,512 W"],
                    ["Maximum duty", "3 percent"],
                    ["Positive supply", "+48 to +50 V, 4 A average"],
                    ["Negative supply", "-8 V, 80 mA average"],
                    ["Case operation / protection", "-10 to +70 C; off at 75 C; reset at 55 C"],
                    ["Nominal mass", "2.5 kg"],
                    ["Exact STEP", "80 solids; 364.12 x 102 x 200 mm"],
                    ["Main housing / flange", "~320 x 48 x 180 mm / ~320 x 3 x 200 mm"],
                    ["Forced-air system", "~45 mm fin field; three 60 mm-class fans"],
                    ["Selected-pose keep-out", "X -182.06..182.06; Y -53..49; Z 30..230 mm"],
                ],
                [3.0 * inch, 3.8 * inch],
                font_size=7.2,
            ),
            subsection("First-principles severe-basis allocation"),
            table(
                [
                    ["Quantity", "Basis", "Result"],
                    ["Positive input", "50 V x 4 A", "200 W"],
                    ["Negative-rail magnitude", "8 V x 0.08 A", "0.64 W"],
                    ["Average RF out", "2,512 W x 0.03 duty", "75.4 W"],
                    ["Matched heat estimate", "approximately 200 - 75", "approximately 125 W"],
                    ["Severe heat basis", "rounded electrical input", "200 W"],
                    ["Dry-side allocation", "10 percent assumption", "20 W"],
                    ["Wet-side rejection", "90 percent + 3 x 0.6 W fans", "181.8 W"],
                ],
                [2.45 * inch, 2.65 * inch, 1.7 * inch],
                font_size=7.0,
                alignments={2: "RIGHT"},
            ),
            Spacer(1, 0.08 * inch),
            callout(
                "Critical data gate",
                "The 125 W matched estimate, 200 W severe basis, and especially the 10 percent dry-side split are engineering assumptions. Vendor calorimetry or a matched/reflected-load prototype test must replace them. The PDF also contains an apparent AM10/AM59 prose inconsistency.",
                "orange",
            ),
            Spacer(1, 0.08 * inch),
            heat_flow_diagram(),
            PageBreak(),
        ]
    )

    # Cooling comparison
    story.extend(
        [
            section("Cooling technology comparison", "4"),
            subsection("Residual dry-load options"),
            table(
                [
                    [
                        "Option",
                        "Rating / estimate",
                        "Input",
                        "Mass",
                        "Ingress / service",
                        "Decision",
                    ],
                    [
                        "Passive finned door",
                        "51.75 W at 18.8 K; UA 2.75 W/K",
                        "0 W",
                        "included",
                        "No opening; clean fins",
                        "SELECT",
                    ],
                    [
                        "Fans only",
                        "Internal: 0 W net removal; external: uncredited augmentation",
                        "low",
                        "low",
                        "Fan/guard maintenance",
                        "No credit",
                    ],
                    [
                        "Seifert 3035303",
                        "30 W at 35/35",
                        "44-52 W",
                        "1.81 kg",
                        "IP66 / NEMA 4X",
                        "Too small at rating",
                    ],
                    [
                        "Seifert 3050303",
                        "50 W at 35/35; higher at +delta-T",
                        "58-60 W",
                        "3.18 kg",
                        "IP66 / NEMA 4X",
                        "Adequate, unnecessary",
                    ],
                    [
                        "Seifert 3102303",
                        "100 W at 35/35",
                        "115-118 W",
                        "5.90 kg",
                        "IP66 / NEMA 4X",
                        "Oversized",
                    ],
                    [
                        "Seifert 3152303 / 3200303",
                        "150 / 200 W",
                        "170-180 / 260-280 W",
                        "9.07 / 9.98 kg",
                        "IP66 / NEMA 4X",
                        "Grossly oversized",
                    ],
                    [
                        "Seifert 6105313 / 6105323",
                        "100 W at 35/35",
                        "125-139 W",
                        "9.53 kg",
                        "IP66 / NEMA 4X",
                        "Oversized",
                    ],
                    [
                        "Hoffman TE09",
                        "52 W at 35/35; ~85 W at +15 K",
                        "89 W",
                        "2.7-3.6 kg",
                        "IP65",
                        "IP gate; unnecessary",
                    ],
                    [
                        "Hoffman TE12 exact",
                        "94 W at 35/35; ~147 W at +15 K",
                        "162 W",
                        "5.0 kg",
                        "IP65; Type 4 shroud",
                        "Oversized",
                    ],
                    [
                        "Hoffman TE16 exact",
                        "166 W at 35/35; ~244 W at +15 K",
                        "295 W",
                        "6.7 kg",
                        "IP65",
                        "Grossly oversized",
                    ],
                    [
                        "Hoffman filter fan + shroud",
                        "13.6 m3/h needed at 10 K for 45 W",
                        "~20 W",
                        "~1 kg",
                        "Open exchange; filter service",
                        "Reject for IP6X",
                    ],
                    [
                        "Hoffman TX23 air-air",
                        "25 W/K",
                        "87 W",
                        "13.6 kg",
                        "Closed loop; Type 4/4X option",
                        "Reject mass/size",
                    ],
                ],
                [1.1 * inch, 1.65 * inch, 0.58 * inch, 0.63 * inch, 1.35 * inch, 1.06 * inch],
                font_size=5.7,
                highlight_rows=(1,),
            ),
            Spacer(1, 0.08 * inch),
            p(
                "<b>Exact local cooler geometry:</b> Seifert 3050303 is 153.50 x 134.93 x 206.00 mm; Hoffman TE121024010 is 159.45 x 182.32 x 304.68 mm; Hoffman TE162024020 is 180.01 x 177.76 x 400.00 mm. Seifert common data: AISI 304, -20 to +65 C, recessed, not roof-mountable; external and condensate kits are separate."
            ),
            callout(
                "Cooling decision",
                "Closed-loop active products can cool the residual load, but none improves this system after mass, wind area, power, cost, seal rating, condensation, and failure modes are counted. Add passive fin area first if prototype UA is low.",
            ),
            PageBreak(),
        ]
    )

    # Thermal
    story.extend(
        [
            section("Thermal budget and acceptance", "5"),
            table(
                [
                    ["Dry source", "Heat"],
                    ["AM59 dry-side leakage at severe basis", "20 W"],
                    ["Future DIN components", "15 W"],
                    ["Present controls/monitoring allowance", "3 W"],
                    ["Residual solar + wet-to-dry conduction", "5 W"],
                    ["Rounding/model allowance", "2 W"],
                    ["Nominal design", "45 W"],
                    ["Selection margin", "+15 percent"],
                    ["Margin-adjusted", "51.75 W"],
                ],
                [5.4 * inch, 1.4 * inch],
                font_size=7.2,
                highlight_rows=(8,),
                alignments={1: "RIGHT"},
            ),
            subsection("Lumped zero-wind model"),
            table(
                [
                    ["Parameter", "Value", "Acceptance meaning"],
                    ["Bare effective area", "0.35 m2", "White shell, excluding wet hood"],
                    ["Finned-door effective area", "0.15 m2", "Fifteen open vertical fins"],
                    [
                        "Conservative overall U",
                        "5.5 W/m2-K",
                        "Natural convection + radiation estimate",
                    ],
                    ["Passive UA", "2.75 W/K", "Model prediction"],
                    ["Required UA", "2.59 W/K", "51.75 W / (65-45 C)"],
                    ["UA margin", "6.28 percent", "Narrow; prototype test controls"],
                    ["Nominal dry-air temperature", "61.4 C", "45 W at 45 C ambient"],
                    ["Margin-load dry-air temperature", "63.8 C", "51.75 W at 45 C ambient"],
                ],
                [2.35 * inch, 1.35 * inch, 3.1 * inch],
                font_size=7.0,
                highlight_rows=(5, 8),
            ),
            Spacer(1, 0.08 * inch),
            callout(
                "Thermal pass condition",
                "At 45 C ambient, zero wind, production coating/shield/interfaces, and representative DIN population, demonstrate UA >=2.59 W/K and dry air <=65 C. If not, increase external passive area before evaluating active cooling.",
                "orange",
            ),
            subsection("Failure posture"),
            p(
                "The dry chamber has no active cooler to fail. AM59 fan loss is an RF-operating fault: detect fan tach/current and case temperature, then inhibit or derate RF below the OEM trip. No blocked-fan operation is assumed safe until mapped."
            ),
            PageBreak(),
        ]
    )

    # Mechanical
    story.extend(
        [
            section("Mechanical concept and service", "6"),
            image(exploded, 7.2 * inch, 3.85 * inch),
            p(
                "Exploded service/weather view. Orange translucent volumes are future DIN reserves; blue is the dry clamp; teal is the transition boot. Hood and shield are non-pressure-boundary weather parts.",
                "caption",
            ),
            table(
                [
                    ["Subsystem", "Preliminary geometry", "Design intent"],
                    [
                        "Welded dry body",
                        "416 x 128 x 286 mm evaluated envelope; 1.5 mm shell; 3 mm bulkhead",
                        "Small IP66 volume around electronics side only",
                    ],
                    [
                        "AM59 opening",
                        "328 x 188 mm",
                        "Exact STEP clearance plus molded transition boot",
                    ],
                    [
                        "Service door",
                        "416 x 286 x 2 mm; 15 fins, 30 x 240 mm",
                        "Direct DIN access and passive heat rejection",
                    ],
                    [
                        "DIN carrier",
                        "Two 300 mm x 35 mm rails; centers Z=80/200 mm",
                        "~16 modules/rail; heavy items on lower rail",
                    ],
                    [
                        "DIN reserves",
                        "Two 310 x 50 x 58 mm envelopes",
                        "15 W / 1.5 kg combined future allowance",
                    ],
                    [
                        "Wet hood",
                        "510 mm airflow length x 150 mm depth",
                        "Floodable; large downward openings; freely drained",
                    ],
                    [
                        "Sun shield",
                        "520 x 330 x 1 mm; 3 degree slope",
                        "White, ventilated, >=12 mm air gap",
                    ],
                ],
                [1.25 * inch, 2.45 * inch, 3.1 * inch],
                font_size=6.7,
            ),
            subsection("Amplifier service sequence"),
            p(
                "Remove the +Y service door, remove the DIN carrier, disconnect future internal interfaces, release the dry clamp, then withdraw the AM59 toward the wet side. Replace the transition boot after disturbance. No wet-side backer or through-fastener must be removed."
            ),
            PageBreak(),
        ]
    )

    # Weather
    story.extend(
        [
            section("IP66 boundary, rain control, and airflow", "7"),
            image(front, 5.0 * inch, 2.6 * inch),
            p(
                "Front view through the transparent shell; vertical door fins remain sheltered by the ventilated solar shield.",
                "caption",
            ),
            subsection("Dry-boundary sealing"),
            bullet(
                "Continuous 5052 welds; finish-machine or locally finish gasket lands after welding."
            ),
            bullet(
                "One-piece service-door gasket with hard compression stops and blind captive inserts."
            ),
            bullet(
                "One-piece molded double-lip AM59 transition boot; outer flange seals axially, inner lips seal radially."
            ),
            bullet(
                "The boot seals the annular wall opening, but vendor construction evidence and a populated wet test must also exclude an internal bypass through the heatsink thermal wall, attachment fasteners, fan-lead path, or wet-side case joints."
            ),
            bullet(
                "Dry clamp loads blind welded studs/bosses; no fastener crosses the pressure boundary."
            ),
            bullet(
                "Mask conductive bond lands and isolate stainless/aluminum couples except at deliberate bonds."
            ),
            subsection("Wet-bay airflow"),
            table(
                [
                    ["Parameter", "Value"],
                    ["Gross downward inlet and exhaust opening", "21,750 mm2 each"],
                    ["Net opening at 85 percent guard free area", "18,488 mm2 each"],
                    ["Velocity at 63 m3/h free-air reference", "0.95 m/s"],
                    ["Dynamic pressure", "0.55 Pa"],
                    ["Estimated hood/labyrinth loss", "3 Pa"],
                    ["Acceptance ceiling", "<=5 Pa at approved operating point"],
                ],
                [4.2 * inch, 2.6 * inch],
                font_size=7.0,
            ),
            p(
                "Both openings face downward and act as primary drains. Production splash floors receive positive falls to both ends. Guards, hems, ice, dust, and wind must not trap water or short-circuit exhaust to inlet.",
                "small",
            ),
            callout(
                "IP66 claim boundary",
                "The hood is not IP-rated and does not need to be. The complete populated dry chamber must independently pass IEC 60529 IP6X and IPX6. IP67 immersion is neither required nor claimed.",
            ),
            PageBreak(),
        ]
    )

    # mass and BOM
    story.extend(
        [
            section("Mass, CG, wind, and preliminary BOM", "8"),
            table(
                [
                    ["Installed item", "Mass", "CG-Z"],
                    ["Pressure body", "1.346 kg", "150.5 mm"],
                    ["Finned service door", "0.985 kg", "145.0 mm"],
                    ["Rain hood", "0.847 kg", "172.9 mm"],
                    ["Solar shield", "0.460 kg", "310.0 mm"],
                    ["Clamp + seals", "0.395 kg", "mixed"],
                    ["DIN carrier + rails", "0.387 kg", "~142 mm"],
                    ["AM59", "2.500 kg", "132.3 mm proxy"],
                    ["Fasteners, finish, bonds, wiring", "0.720 kg", "allocated"],
                    ["Complete empty", "7.641 kg", "153.2 mm"],
                    ["+ low future DIN payload", "9.141 kg", "141.2 mm"],
                ],
                [3.8 * inch, 1.4 * inch, 1.6 * inch],
                font_size=7.0,
                highlight_rows=(9, 10),
                alignments={1: "RIGHT", 2: "RIGHT"},
            ),
            p(
                "Provisional axis: X=0, Y=25 mm, Z=0 reference plane. Empty radial CG is 0.91 mm; with 1.5 kg on the lower rail it is 9.91 mm. This datum is not a mounting design."
            ),
            metric_strip(
                [
                    ("0.147 m2", "FRONT WIND"),
                    ("0.100 m2", "SIDE WIND"),
                    ("0.172 m2", "PLAN / UPLIFT"),
                ]
            ),
            subsection("Quantity-one enclosure budget"),
            table(
                [
                    ["Lot", "Mass", "Low", "High"],
                    ["Welded body + finned door", "2.33 kg", "$900", "$1,500"],
                    ["Rain hood + sun shield", "1.31 kg", "$250", "$500"],
                    ["Machined dry clamp", "0.264 kg", "$300", "$600"],
                    ["Transition boot + door gasket", "0.131 kg", "$350", "$800"],
                    ["DIN carrier + rails", "0.387 kg", "$100", "$200"],
                    ["Coating, bonds, fasteners, isolation", "0.54 kg", "$250", "$500"],
                    ["Prototype test instrumentation", "not installed", "$200", "$400"],
                    ["TOTAL excluding AM59", "5.14 kg", "$2,350", "$4,500"],
                ],
                [3.25 * inch, 1.15 * inch, 1.15 * inch, 1.25 * inch],
                font_size=7.0,
                highlight_rows=(8,),
                alignments={1: "RIGHT", 2: "RIGHT", 3: "RIGHT"},
            ),
            p(
                "Budget excludes the AM59, future DIN equipment, ports, feedthroughs, pressure vent, mast/rotator interfaces, and production elastomer mold tooling. Supplier quotations control.",
                "small",
            ),
            PageBreak(),
        ]
    )

    # Qualification
    story.extend(
        [
            section("Qualification plan", "9"),
            table(
                [
                    ["Test", "Method / configuration", "Preliminary acceptance"],
                    [
                        "Dimensional first article",
                        "3D scan AM59 band; flatness, squeeze, torque, extraction",
                        "Continuous seal band; released tolerance stack",
                    ],
                    [
                        "AM59 calorimetry",
                        "Matched, max duty, reduced voltage, allowed mismatch",
                        "Replace 200 W / 10 percent assumptions",
                    ],
                    [
                        "Passive thermal",
                        "45 C, zero wind, production shield/coating, 51.75 W dry",
                        "UA >=2.59 W/K; dry air <=65 C",
                    ],
                    [
                        "Wet thermal",
                        "181.8 W wet load, reduced voltage, fan faults",
                        "Case map below released limits; safe inhibit",
                    ],
                    [
                        "Installed airflow",
                        "Fan curves, delta-P, flow, rain/guards/dust",
                        "Hood loss <=5 Pa; no recirculation",
                    ],
                    [
                        "Wet-side endurance",
                        "Rain, condensation, freeze/thaw, dust, restart",
                        "No fan/lead/coating functional degradation",
                    ],
                    [
                        "IEC 60529 IP6X",
                        "Complete populated dry boundary; deferred holes blanked",
                        "Dust-tight",
                    ],
                    [
                        "IEC 60529 IPX6",
                        "All orientations; target boot, door, welds, underside",
                        "No harmful water ingress",
                    ],
                    [
                        "Production leak screen",
                        "Pressure decay or tracer correlated to passed IP units",
                        "Released production limit",
                    ],
                    [
                        "Environmental cycling",
                        "Thermal/pressure, humidity, altitude, UV, corrosion",
                        "No seal set, leak, crack, or unsafe condition",
                    ],
                    [
                        "Mechanical",
                        "Shock, vibration, fan imbalance, clamp/hood/door fatigue",
                        "No loss of retention or resonance failure",
                    ],
                    [
                        "Electrical and RF",
                        "Bonding, insulation after wet, EMC, fan fault, RF inhibit",
                        "Safe shutdown and compliance",
                    ],
                ],
                [1.25 * inch, 3.65 * inch, 1.9 * inch],
                font_size=6.15,
            ),
            Spacer(1, 0.08 * inch),
            callout(
                "No IP67 work",
                "Qualification stops at the complete-assembly IP66 objective. Immersion caps, submersion seals, and IP67 pressure assumptions are intentionally excluded.",
            ),
            PageBreak(),
        ]
    )

    # Gates
    story.extend(
        [
            section("Assumptions and release gates", "10"),
            subsection("AM59 and fan - hard vendor gates"),
            bullet(
                "Approve vertical bulkhead orientation, case-contacting seal, clamp/support loads, wet-side use, service method, and warranty."
            ),
            bullet(
                "Prove no water bypass through the heatsink thermal wall, attachment fasteners, fan-lead route, or wet-side case joints; otherwise use a vendor-sealed modular/cold-wall interface."
            ),
            bullet(
                "Control the delivered-unit outline and scan a continuous seal band; resolve any STEP/drawing/physical mismatch."
            ),
            bullet(
                "Resolve the reverse-monitor connector ambiguity and confirm the twelve M4 locations, engagement, torque, orientation, and allowable support loads."
            ),
            bullet(
                "Provide calorimetry or approve test evidence for total loss, dry/wet split, allowed mismatch, and case map."
            ),
            bullet(
                "Release the exact moisture-protected fan suffix, wet lead sealing, life, and installed fan curve without reducing qualified flow."
            ),
            subsection("Seals and fabricated enclosure"),
            bullet(
                "Seal supplier releases boot gland, compound, coating compatibility, tolerances, compression, torque, replacement interval, and IP6X/IPX6 evidence."
            ),
            bullet(
                "Door gasket gland, corner radii, hard stops, insert pitch, welding distortion, and finish-machined flatness are detailed."
            ),
            bullet(
                "Zero-wind passive UA meets 2.59 W/K after final coating, wiring, interface blanks, and DIN population."
            ),
            bullet(
                "Production hood loss is <=5 Pa with no water/ice trap or exhaust-to-inlet short circuit."
            ),
            subsection("Deferred system data"),
            bullet(
                "Replace 18 W and 1.5 kg future DIN allowances with actual selected equipment; keep heavy items on the lower rail."
            ),
            bullet(
                "Define site ambient, solar, altitude, salinity, ice, wind, gust, fatigue, and orientation."
            ),
            bullet(
                "Later design ports/feedthroughs, pressure equalization, protective earth/RF/lightning bonds, rotator interface, mast adapter, and cable loops."
            ),
            Spacer(1, 0.07 * inch),
            callout(
                "Prototype release condition",
                "Do not cut metal until the physical AM59 seal-band scan and written vendor orientation/support response are reviewed. Do not release production until calorimetry, passive UA, installed airflow, and complete-assembly IP6X/IPX6 pass.",
                "orange",
            ),
            PageBreak(),
        ]
    )

    # Deliverables and refs
    story.extend(
        [
            section("Deliverables and references", "11"),
            subsection("Reproducible local package"),
            table(
                [
                    ["Artifact", "Purpose"],
                    ["model.py", "Parametric CadQuery source of truth"],
                    [
                        "params.json",
                        "Dimensions, source data, trade study, thermal/mass budgets, gates",
                    ],
                    ["spec.json", "Geometry and fit evaluation contract"],
                    [
                        "fit_check.py",
                        "Exact AM59/vendor-cooler, thermal, mass/CG, airflow, and architecture checks",
                    ],
                    ["render_concept.py", "Colored design-review views"],
                    [
                        "exports/am59_ip66_passive_enclosure_v4.step",
                        "Evaluated welded dry-body STEP",
                    ],
                    [
                        "assemblies/am59_ip66_passive_enclosure.py",
                        "Complete context assembly export driver",
                    ],
                    ["PRELIMINARY_BOM.csv", "Quotation-oriented preliminary BOM"],
                    ["DESIGN.md", "Detailed editable engineering narrative"],
                ],
                [2.5 * inch, 4.3 * inch],
                font_size=7.1,
            ),
            subsection("Vendor evidence"),
            p(
                "<b>Local:</b> AM59-005D.pdf and exact AM59 STEP; Seifert 3050303 STEP, drawing, and catalog; Hoffman Spec-00580.pdf and exact TE12/TE16 STEP files."
            ),
            p(
                "<b>Official web:</b><br/>"
                '<link href="https://img.ebmpapst.com/products/datasheets/DC-axial-fan-612NGLE-ENU.pdf" color="#246B8E">ebm-papst 612 NGLE datasheet</link><br/>'
                '<link href="https://www.nvent.com/sites/default/files/acquiadam/assets/Spec-00580.pdf" color="#246B8E">nVent Hoffman thermoelectric specification</link><br/>'
                '<link href="https://www.nvent.com/eldon/sku?item_number=TE121024010&amp;locale=en-GB" color="#246B8E">nVent Hoffman TE121024010 product</link><br/>'
                '<link href="https://www.nvent.com/en-us/hoffman/products/filter-fan-shrouds-type-44x-0" color="#246B8E">nVent Hoffman Type 4/4X filter-fan shrouds</link><br/>'
                '<link href="https://www.nvent.com/sites/default/files/acquiadam/assets/Spec-00624.pdf" color="#246B8E">nVent Hoffman ClimaGuard air-to-air specification</link><br/>'
                '<link href="https://www.automationdirect.com/pn/3050303" color="#246B8E">Seifert 3050303 distributor listing</link>'
            ),
            Spacer(1, 0.12 * inch),
            p(
                "<b>Analysis integrity:</b> all dimensions are millimeters, masses kilograms, heat watts, and temperatures degrees Celsius unless stated. Calculated values are intentionally distinguished from vendor-rated data. Physical and vendor evidence supersedes this report."
            ),
            Spacer(1, 0.15 * inch),
            callout(
                "Engineering conclusion",
                "The simplest credible IP66 system is not a larger actively cooled box. It is a small sealed dry chamber around only what must stay dry, with the intact OEM heat rejection left outside and a testable elastomer boundary between them.",
            ),
        ]
    )
    return story


def generate() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame = Frame(
        MARGIN_X,
        MARGIN_BOTTOM,
        PAGE_W - 2 * MARGIN_X,
        PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
        id="normal",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    cover = PageTemplate(id="cover", frames=[frame], onPage=_cover)
    normal = PageTemplate(id="normal", frames=[frame], onPage=_header_footer)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="AM59 IP66 Low-CG Outdoor Enclosure V4",
        author="Parametric CAD engineering concept",
        subject="Architecture, CAD, thermal, mass/CG, sealing, BOM, and qualification",
    )
    doc.addPageTemplates([cover, normal])
    story = build_story()
    # The first page uses the cover template; switch all later pages to normal.
    story.insert(
        story.index(next(item for item in story if isinstance(item, PageBreak))),
        NextPageTemplate("normal"),
    )
    doc.build(story)
    return OUTPUT


if __name__ == "__main__":
    print(generate())
