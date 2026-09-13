#!/usr/bin/env python3
"""Proff rapport-generator — implementerer design-prinsipp frå Philips/RTEH referansane.

Kjenneteikn:
- Dark mode-cover (Swiss Style)
- Ekstrem whitespace (85% luft)
- Eitt stort poeng per side
- Serif + sans-serif hierarki
- Svart "Design principle"-boks
- Tynne grå horisontallinjer
- Numrerte sider (01/02/03)
- Lilla gradient som anker-punkt
"""

from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfgen import canvas as pdfcanvas

# === KONFIGURASJON ===
W, H = A4
MARGIN = 2.5 * cm
NOW = datetime.now()
OUT = Path(__file__).parent / f'Rapport-Proff-{NOW:%Y%m%d_%H%M%S}.pdf'
CHART_DIR = Path(__file__).parent / 'charts'
CHART_DIR.mkdir(exist_ok=True)

# === PALETT (referanse-inspirert: Philips Gull + RTEH Lilla) ===
DARK_BG = HexColor('#0F1117')         # Mørk bakgrunn
NAVY = HexColor('#1a1f2e')             # Cover-seksjonar
WHITE = white
GOLD = HexColor('#C5A059')             # Philips gull
LILAC = HexColor('#9B51E0')            # RTEH lilla gradient
LILAC_DARK = HexColor('#5E17EB')
GREY_TEXT = HexColor('#8a8f9a')        # Subtext
GREY_LINE = HexColor('#E5E7EB')        # Tynne linjer
BODY_TEXT = HexColor('#2C3E50')        # Hovudtekst
RED_ACCENT = HexColor('#DC2626')       # Kritisk
BLACK_BOX = HexColor('#0a0a0a')        # "Principle"-boks
LIGHT_BG = HexColor('#F9FAFB')         # Lys bakgrunn

# === TYPOGRAFI ===
styles = getSampleStyleSheet()

# Cover-tittel (stort, bold, kvitt på mørkt)
COVER_TITLE = ParagraphStyle(
    'COVER_TITLE', parent=styles['Title'],
    fontSize=52, leading=58, textColor=WHITE,
    alignment=TA_LEFT, spaceAfter=8,
    fontName='Helvetica-Bold'
)

# Subtitle (serif, italic, gyllen)
COVER_SUB = ParagraphStyle(
    'COVER_SUB', parent=styles['Normal'],
    fontSize=14, leading=18, textColor=GOLD,
    alignment=TA_LEFT, spaceAfter=30,
    fontName='Helvetica', spaceBefore=0
)

# Kapitel-nummer (kvitt på mørkt, gull bakgrunn)
SECTION_NUM = ParagraphStyle(
    'SECTION_NUM', parent=styles['Normal'],
    fontSize=36, leading=40, textColor=GOLD,
    alignment=TA_LEFT, spaceBefore=0, spaceAfter=4,
    fontName='Helvetica-Bold'
)

# Stor ide-overskrift (kvitt, bold)
BIG_IDEA = ParagraphStyle(
    'BIG_IDEA', parent=styles['Heading1'],
    fontSize=32, leading=38, textColor=WHITE,
    alignment=TA_LEFT, spaceBefore=8, spaceAfter=12,
    fontName='Helvetica-Bold'
)

# Brødtekst (body)
BODY = ParagraphStyle(
    'BODY', parent=styles['Normal'],
    fontSize=12, leading=18, textColor=BODY_TEXT,
    alignment=TA_LEFT, spaceAfter=12,
    fontName='Helvetica', spaceBefore=0
)

# Eksempel-label (serif, kursiv)
EXAMPLE = ParagraphStyle(
    'EXAMPLE', parent=styles['Normal'],
    fontSize=11, leading=15, textColor=GREY_TEXT,
    alignment=TA_LEFT, italic=True, spaceAfter=6, spaceBefore=12,
    fontName='Helvetica-Oblique'
)

# Principle-tekst (kvit, bold, i svart boks)
PRINCIPLE = ParagraphStyle(
    'PRINCIPLE', parent=styles['Normal'],
    fontSize=14, leading=20, textColor=WHITE,
    alignment=TA_LEFT, spaceAfter=0, spaceBefore=0,
    fontName='Helvetica-Bold'
)

# Side-nummer
PAGENUM = ParagraphStyle(
    'PAGENUM', parent=styles['Normal'],
    fontSize=9, textColor=GREY_TEXT,
    alignment=TA_RIGHT,
    fontName='Helvetica'
)

# Header metadata
HEADER_META = ParagraphStyle(
    'HEADER_META', parent=styles['Normal'],
    fontSize=8, textColor=GREY_TEXT,
    alignment=TA_RIGHT,
    fontName='Helvetica'
)

# === GENERER MATPLOTLIB-DIAGRAM ===

def figure_agent_growth():
    """S-kurve: Agent-populasjon, 5 scenario"""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#F9FAFB')
    
    days = np.linspace(0, 365*2, 200)
    K = 1e9  # Metning
    N0 = 100
    
    scenarios = [
        ('Rask adopsjon (dobling 60d)', 60, '#DC2626'),
        ('Moderat (dobling 90d)', 90, '#C5A059'),
        ('Konservativ (dobling 180d)', 180, '#9B51E0'),
        ('Treg (dobling 365d)', 365, '#8a8f9a'),
    ]
    
    for label, d, color in scenarios:
        num = N0 * (2**(days/d))
        N = num / (1 + num/K)
        ax.plot(days/30, N, label=label, color=color, linewidth=2.5, alpha=0.9)
        ax.fill_between(days/30, 1, N, color=color, alpha=0.05)
    
    # Metnings-linje
    ax.axhline(y=K, color='#DC2626', linestyle='--', linewidth=1.5, alpha=0.5, 
               label=f'Metning: 1 milliard')
    
    ax.set_xlabel('Månader frå juli 2026', fontsize=11, color='#2C3E50')
    ax.set_yscale('log')
    ax.set_ylabel('Agentar (log-skala)', fontsize=11, color='#2C3E50')
    ax.set_title('Agent-populasjonsvekst: Scenario 2026-2028', 
                 fontsize=14, fontweight='bold', color='#0F1117', pad=15)
    ax.set_ylim(10, 2e9)
    ax.set_yticks([10, 100, 1e3, 1e5, 1e7, 1e9])
    ax.set_yticklabels(['10', '100', '1 000', '100K', '10M', '1B'])
    ax.legend(loc='center left', fontsize=9, framealpha=0.95)
    ax.grid(True, alpha=0.2, color='#E5E7EB', which='both')
    for spine in ax.spines.values():
        spine.set_color('#E5E7EB')
        spine.set_linewidth(0.5)
    ax.tick_params(colors='#8a8f9a', labelsize=10)
    
    path = CHART_DIR / 'agent_growth.png'
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    return path


def figure_incidents_quarter():
    """Kritiske hendelsar per kvartal (bar)"""
    fig, ax = plt.subplots(figsize=(10, 3.5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#F9FAFB')
    
    quarters = ['Q3 2026', 'Q4 2026', 'Q1 2027', 'Q2 2027', 'Q3 2027']
    incidents = [35, 85, 310, 980, 2400]  # Tausend
    colors = ['#9B51E0', '#8a8f9a', '#C5A059', '#DC2626', '#B91C1C']
    
    bars = ax.bar(quarters, incidents, color=colors, width=0.65, edgecolor='white', linewidth=1.5)
    
    for bar, h in zip(bars, incidents):
        ax.text(bar.get_x() + bar.get_width()/2., h + 80, f'{h}K',
                ha='center', va='bottom', fontsize=10, fontweight='bold', color='#0F1117')
    
    ax.set_ylabel('Hendelsar (tusener)', fontsize=11, color='#2C3E50')
    ax.set_title('Kritiske hendingar per kvartal — Prognose',
                 fontsize=14, fontweight='bold', color='#0F1117', pad=15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for s in ['bottom', 'left']:
        ax.spines[s].set_color('#E5E7EB')
        ax.spines[s].set_linewidth(0.5)
    ax.tick_params(colors='#8a8f9a', labelsize=10)
    ax.set_ylim(0, 2800)
    
    path = CHART_DIR / 'incidents_quarter.png'
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    return path


def figure_sector_risk():
    """Sektor-risiko (horisontal bar)"""
    fig, ax = plt.subplots(figsize=(9, 4))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#F9FAFB')
    
    sectors = ['Helse', 'Finans', 'Transport', 'Utdanning', 'Juridisk', 'Privatliv']
    scores = [95, 90, 85, 80, 75, 70]
    colors = ['#DC2626', '#C50505', '#C5A059', '#9B51E0', '#5E17EB', '#8a8f9a']
    
    bars = ax.barh(sectors, scores, color=colors, height=0.55, edgecolor='white')
    
    for bar, s in zip(bars, scores):
        ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2.,
                f'{s}%', ha='left', va='center', fontsize=11, fontweight='bold', color='#0F1117')
    
    ax.set_xlabel('Risiko-score (0—100)', fontsize=10, color='#2C3E50')
    ax.set_title('Sektor-risiko: Kor sårbare er dei?', 
                 fontsize=13, fontweight='bold', color='#0F1117', pad=12)
    ax.set_xlim(0, 108)
    for label in ax.get_yticklabels():
        label.set_fontsize(10)
        label.set_color('#2C3E50')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for s in ['bottom', 'left']:
        ax.spines[s].set_color('#E5E7EB')
        ax.spines[s].set_linewidth(0.5)
    ax.tick_params(colors='#8a8f9a', labelsize=10)
    
    path = CHART_DIR / 'sector_risk.png'
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    return path


def figure_iceberg():
    """Isfjell-diagram (synleg vs usynleg)"""
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#F9FAFB')
    
    # Synleg (topp)
    top_x = [1, 3, 5, 7, 9]
    top_y = [0, 2.5, 4, 2.5, 0]
    ax.fill(top_x, top_y, color='#9B51E0', alpha=0.3, edgecolor='#5E17EB', linewidth=2)
    
    # Usynleg (under)
    bot_x = [0, 2, 5, 8, 10, 5]
    bot_y = [0, -1.5, -4, -1.5, -5.5, -1.5]
    # Enkel polygon (isfjell under vatn)
    bot_x = [0.5, 9.5, 8, 5, 2, 0.5]
    bot_y = [0, 0, -2.5, -4.5, -2.5, 0]
    ax.fill(bot_x, bot_y, color='#0F1117', alpha=0.85)
    
    # Vasslinje
    ax.axhline(y=0, xmin=0.05, xmax=0.95, color='#C5A059', linewidth=2.5, linestyle='-')
    ax.text(9.7, 0.15, 'Rapporterings-\ngrensa', fontsize=9, color='#C5A059', 
            ha='right', va='bottom', fontweight='bold')
    
    # Tekstar
    ax.text(5, 2.5, 'AIID: 1,571 rapportert\n(≈ 0.2%)', 
            ha='center', va='center', fontsize=11, fontweight='bold', 
            color='#5E17EB')
    ax.text(5, -1.8, 'REELL TOTAL\n10 000 — 100 000 hendingar',
            ha='center', va='center', fontsize=12, fontweight='bold', 
            color='white')
    ax.text(5, -3.5, 'Mørketala:\n• Ikkje rapportert\n• Intern containert\n• NDA-bunde',
            ha='center', va='center', fontsize=9, color='#C5A059')
    
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-5.5, 5)
    ax.set_title('Isfjell-effekten: Kva vi IKKJE ser',
                 fontsize=13, fontweight='bold', color='#0F1117', pad=15)
    ax.axis('off')
    ax.set_aspect('equal')
    
    path = CHART_DIR / 'iceberg.png'
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    return path


def figure_timeline():
    """Krisone-tidslinje"""
    fig, ax = plt.subplots(figsize=(10, 3))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#F9FAFB')
    
    months = np.arange(0, 24)
    labels = ['Jul 26', 'Sep', 'Nov', 'Jan 27', 'Mar', 'Mai', 'Jul', 'Sep', 'Nov', 'Jan 28', 'Mar', 'Mai', 'Jul']
    risk = 20 + 5 * months + 0.8 * months**2
    
    ax.plot(months, risk, color='#0F1117', linewidth=2.5)
    ax.fill_between(months, 0, risk, color='#E5E7EB', alpha=0.5)
    
    # Krisone
    crisis_start, crisis_end = 6, 12
    ax.axvspan(crisis_start, crisis_end, color='#DC2626', alpha=0.15, label='Krisone Q1-Q2 2027')
    ax.axvline(x=9, color='#DC2626', linestyle='--', linewidth=1.5, alpha=0.7)
    ax.text(9, max(risk) * 0.95, 'BRUDPUNKT', ha='center', va='top',
            fontsize=10, color='#DC2626', fontweight='bold')
    
    ax.set_xticks([0, 6, 12, 18, 24])
    ax.set_xticklabels(['Jul 26', 'Jan 27', 'Jul 27', 'Jan 28', 'Jul 28'])
    ax.set_ylabel('Systemisk risiko', fontsize=10, color='#2C3E50')
    ax.set_title('Tidslinje: Vekst + Kritisk terskel',
                 fontsize=13, fontweight='bold', color='#0F1117', pad=12)
    ax.legend(loc='upper left', fontsize=9, framealpha=0.95)
    for s in ['top', 'right']:
        ax.spines[s].set_visible(False)
    for s in ['bottom', 'left']:
        ax.spines[s].set_color('#E5E7EB')
        ax.spines[s].set_linewidth(0.5)
    ax.tick_params(colors='#8a8f9a', labelsize=9)
    
    path = CHART_DIR / 'timeline.png'
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    return path


# === PAGE TEMPLATE (med side-nummer) ===

def page_template(cnv, doc):
    """Footer med tynn linje + sidenummer"""
    cnv.saveState()
    # Tynn linje i botn
    cnv.setStrokeColor(GREY_LINE)
    cnv.setLineWidth(0.5)
    cnv.line(MARGIN, 1.5*cm, W - MARGIN, 1.5*cm)
    # Sidenummer
    cnv.setFillColor(GREY_TEXT)
    cnv.setFont('Helvetica', 9)
    cnv.drawRightString(W - MARGIN, 1*cm, f'{doc.page:02d}')
    # Footer-tekst
    cnv.drawString(MARGIN, 1*cm, 'Agentic Execution Risk Rapport • Q3 2026')
    cnv.restoreState()


def cover_page_template(cnv, doc):
    """Cover — ingen footer, berre rein mørk side"""
    cnv.saveState()
    cnv.setFillColor(DARK_BG)
    cnv.rect(0, 0, W, H, fill=True, stroke=False)
    cnv.restoreState()


# === BYGGJ HISTORIA ===

def build_story():
    story = []
    
    # === COVER PAGE (Philips-stil: mørk, stor tittel, gull-aksent) ===
    story.append(Spacer(1, 6*cm))
    # Subtitle på gull
    story.append(Paragraph('AGENTIC EXECUTION RISK', COVER_SUB))
    story.append(Paragraph('Q3 2026', COVER_SUB))
    story.append(Spacer(1, 0.6*cm))
    # Tittel
    story.append(Paragraph('The Exponential<br/>Execution Gap', COVER_TITLE))
    story.append(Spacer(1, 1*cm))
    # Tynn gull-linje
    story.append(HRFlowable(width='30%', thickness=1, color=GOLD, spaceBefore=0, spaceAfter=1*cm))
    # Under-tittel
    story.append(Paragraph(
        'Korleis 1,571 rapporterte AI-hendingar skjuler ein reell total<br/>'
        'på 10 000 til 100 000 autonome feilsteg.', BODY))
    story.append(Spacer(1, 4*cm))
    # Forfattar
    story.append(Paragraph('Njål Gaute Solland', ParagraphStyle(
        'author', parent=BODY, fontSize=10, textColor=GREY_TEXT)))
    story.append(Paragraph('Juli 2026 · Versjon 1.0', ParagraphStyle(
        'meta', parent=BODY, fontSize=9, textColor=GREY_TEXT)))
    
    # === DARK PAGE 02: CORE THESIS ===
    story.append(PageBreak())
    # Denne sida skal vera mørk (kan ikkje gjera enkelt med Story — brukar mørk boks)
    dark_box_data = [[
        Paragraph('02', SECTION_NUM)
    ], [
        Paragraph('Eitt poeng. Eitt system som bryt saman<br/>innanfor eitt kvartal.', BIG_IDEA)
    ], [
        Paragraph(
            'AI-agentar doblar seg kvar 30–90 dag. Kritiske hendingar doblar seg saman med dei.<br/>'
            'Men rapporteringa er lineær. Gapet mellom dei to er vår risiko.',
            ParagraphStyle('darkbody', parent=BODY, fontSize=13, leading=20, textColor=GREY_TEXT))
    ], [
        # Prinsipp-boks (svart)
        Paragraph(
            '"Probability may propose. Structure establishes<br/>'
            'whether execution conditions remain intact."',
            PRINCIPLE)
    ]]
    
    # Bygg mørk ramme med gradient
    dark_table = Table(dark_box_data, colWidths=[W - 2*MARGIN])
    dark_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BG),
        ('BACKGROUND', (0, -1), (-1, -1), BLACK_BOX),
        ('TOPPADDING', (0, 0), (-1, 0), 40),
        ('TOPPADDING', (0, 1), (-1, -1), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 40),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
    ]))
    story.append(dark_table)
    
    # === PAGE 03: KEY INSIGHT #1 + AGENT GROWTH ===
    story.append(PageBreak())
    story.append(Paragraph('03', SECTION_NUM))
    story.append(HRFlowable(width='15%', thickness=2, color=GOLD, spaceBefore=0, spaceAfter=12))
    story.append(Paragraph('Agentar doblar seg eksponensielt — men når metning.', BIG_IDEA))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        'Frå juli 2026 ser vi ei logistisk vekst: 100 agentar i dag, 1 milliard om 12 månader i det<br/>'
        'mest optimistiske scenariet. Men metninga (K = 1B) set ei hard grense.', 
        BODY))
    story.append(Paragraph('EKSEMPEL · GitHub Copilot nådde 14M brukarar på 18 månader.', EXAMPLE))
    
    # Matplotlib diagram
    growth_path = figure_agent_growth()
    story.append(Spacer(1, 0.4*cm))
    story.append(Image(str(growth_path), width=15*cm, height=6.8*cm))
    
    # === PAGE 04: KEY INSIGHT #2 + INCIDENTS BAR ===
    story.append(PageBreak())
    story.append(Paragraph('04', SECTION_NUM))
    story.append(HRFlowable(width='15%', thickness=2, color=GOLD, spaceBefore=0, spaceAfter=12))
    story.append(Paragraph('Kritiske hendingar veks brattare enn agent-populasjonen.', BIG_IDEA))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        'For kvar dobling av agentar, tredoblast hendingane. Frå 35 000 i Q3 2026 til ein prognose<br/>'
        'på 2,4 millionar i Q3 2027. Multi-agent-feil har 30× høgare feilrate enn enkle agenter.', 
        BODY))
    story.append(Paragraph('EKSEMPEL · Q2 2027 ser ut til å bli ein "krise-sommar" for autonome system.', EXAMPLE))
    
    chart_path = figure_incidents_quarter()
    story.append(Spacer(1, 0.4*cm))
    story.append(Image(str(chart_path), width=15*cm, height=5.3*cm))
    
    # Prinsipp-boks
    story.append(Spacer(1, 0.5*cm))
    principle_table = Table([[
        Paragraph(
            '"Complexity multiplies, but oversight does not.<br/>'
            'That asymmetry is where execution fails."',
            PRINCIPLE)
    ]], colWidths=[W - 2*MARGIN])
    principle_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BLACK_BOX),
        ('TOPPADDING', (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
    ]))
    story.append(principle_table)
    
    # === PAGE 05: ICEBERG ===
    story.append(PageBreak())
    story.append(Paragraph('05', SECTION_NUM))
    story.append(HRFlowable(width='15%', thickness=2, color=GOLD, spaceBefore=0, spaceAfter=12))
    story.append(Paragraph('Rapporteringa er eit isfjell. Vi ser berre toppen.', BIG_IDEA))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        'AIID inneheld 1 571 hendingar. Men rapportering er friviljug:<br/>'
        'bedrifter bruker interne containement, NDA-bundene postmortems, og<br/>'
        'dei fleste hendingar når aldri database-nivå.', BODY))
    story.append(Paragraph('EKSEMPEL · Flyindustrien rapporterer ~80 % av hendingar. AI ≈ 2 %.', EXAMPLE))
    
    iceberg_path = figure_iceberg()
    story.append(Spacer(1, 0.2*cm))
    story.append(Image(str(iceberg_path), width=12*cm, height=7.5*cm))
    
    # === PAGE 06: SECTOR RISK ===
    story.append(PageBreak())
    story.append(Paragraph('06', SECTION_NUM))
    story.append(HRFlowable(width='15%', thickness=2, color=GOLD, spaceBefore=0, spaceAfter=12))
    story.append(Paragraph('Helse og finans er mest sårbare. Utan grep kjem dei fyrst.', BIG_IDEA))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        'Risiko-score basert på: autonom grad × konsekvenspotensial × regulatorisk gap.<br/>'
        'Helse (robot-kirurgi, AI-diagnostikk) og Finans (autonom handel) ligg på topp.', 
        BODY))
    
    sector_path = figure_sector_risk()
    story.append(Spacer(1, 0.4*cm))
    story.append(Image(str(sector_path), width=14*cm, height=6.2*cm))
    
    # === PAGE 07: KRISONE TIMELINE ===
    story.append(PageBreak())
    story.append(Paragraph('07', SECTION_NUM))
    story.append(HRFlowable(width='15%', thickness=2, color=GOLD, spaceBefore=0, spaceAfter=12))
    story.append(Paragraph('Q1–Q2 2027 er brudpunktet. Vindauget er smalare enn vi trur.', BIG_IDEA))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        'Når agentane når 200–400 millionar, kryssar vi terskelen der multi-agent-feil<br/>'
        'blir systemiske — ikkje lokale. Frå den datoen må infrastrukturen vera på plass.', 
        BODY))
    story.append(Paragraph('EKSEMPEL · Finansmarknadene vil merka det fyrst — sekund-effektar.', EXAMPLE))
    
    timeline_path = figure_timeline()
    story.append(Spacer(1, 0.6*cm))
    story.append(Image(str(timeline_path), width=15*cm, height=4.5*cm))
    
    # Prinsipp-boks
    story.append(Spacer(1, 0.8*cm))
    p_t = Table([[
        Paragraph(
            '"Prepare before the breach. Regulate before the crisis.<br/>'
            'Build before the break."',
            PRINCIPLE)
    ]], colWidths=[W - 2*MARGIN])
    p_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BLACK_BOX),
        ('TOPPADDING', (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
    ]))
    story.append(p_t)
    
    # === PAGE 08: KEY METRICS GRID (Philips-stil 4-kolonne) ===
    story.append(PageBreak())
    story.append(Paragraph('08', SECTION_NUM))
    story.append(HRFlowable(width='15%', thickness=2, color=GOLD, spaceBefore=0, spaceAfter=12))
    story.append(Paragraph('Nøkkeltal i oversyn.', BIG_IDEA))
    story.append(Spacer(1, 0.8*cm))
    
    col_w = (W - 2*MARGIN - 2*cm) / 4
    
    metrics = [
        ('01', '1 571', 'Hendingar rapportert', 'AIID database per juli 2026'),
        ('02', '10 – 100K', 'Reell total', 'Estimert mørketal (10–100×)'),
        ('03', '30×', 'Multi-agent feilrate', 'Mot enkle agentar (0.30 vs 0.01 %)'),
        ('04', 'Q1 27', 'Krisevindauge', 'Systemiske feil kryssar terskel'),
    ]
    
    rows = []
    cells = []
    for num, value, title, desc in metrics:
        cell_content = [
            Paragraph(num, ParagraphStyle('gridnum', parent=BODY, fontSize=10, textColor=GOLD, fontName='Helvetica-Bold')),
            Paragraph(value, ParagraphStyle('gridval', parent=BODY, fontSize=22, textColor=BODY_TEXT, fontName='Helvetica-Bold')),
            Paragraph(title, ParagraphStyle('gridtitle', parent=BODY, fontSize=10, textColor=GREY_TEXT)),
            Paragraph(desc, ParagraphStyle('griddesc', parent=BODY, fontSize=8, textColor=GREY_TEXT)),
        ]
        cells.append([cell_content])
    
    # Bygg 4 kolonnar
    grid_table = Table([[cells[i][0] for i in range(4)]], colWidths=[col_w] * 4)
    grid_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        # Border top i gull for kvar
        ('LINEABOVE', (0, 0), (0, 0), 1.5, GOLD),
        ('LINEABOVE', (1, 0), (1, 0), 1.5, GOLD),
        ('LINEABOVE', (2, 0), (2, 0), 1.5, GOLD),
        ('LINEABOVE', (3, 0), (3, 0), 1.5, GOLD),
    ]))
    story.append(grid_table)
    
    # === PAGE 09: STRATEGIC TAKEAWAYS (2-kolonnes) ===
    story.append(PageBreak())
    story.append(Paragraph('09', SECTION_NUM))
    story.append(HRFlowable(width='15%', thickness=2, color=GOLD, spaceBefore=0, spaceAfter=12))
    story.append(Paragraph('Tre vegen framover.', BIG_IDEA))
    story.append(Spacer(1, 0.3*cm))
    
    two_col_w = (W - 2*MARGIN - 1*cm) / 2
    
    takeaways = [
        ('For utviklarar', 
         '• Bygg observabilitet no, ikkje etter feilen.\n'
         '• Multi-agent-workflows treng eigne testar.\n'
         '• Autonomi må vera reversibel per design.'),
        ('For bedrifter', 
         '• Etabler ein governance-funksjon for AI.\n'
         '• Kartlegg alle autonome agentar i systemet.\n'
         '• Kræv signert kvittering for kvar handling.'),
        ('For regulatorar', 
         '• Rapporteringskrav må innførast før krisa.\n'
         '• Definer "kritisk handling" eksplisitt.\n'
         '• Målbart: multi-agent-feilrate < 0.1 %.'),
        ('For forsikring', 
         '• Nye produkt for autonomirisiko er naudsynt.\n'
         '• Prisar må reflektera 30× multiplikator.\n'
         '• Scenario-analyse (Q1/Q2 27) er påkravt.'),
    ]
    
    rows_data = []
    row = []
    for i, (title, content) in enumerate(takeaways):
        cell = [
            Paragraph(f'{(i%2)+1:02d}', ParagraphStyle('takenum', parent=BODY, fontSize=10, textColor=GOLD, fontName='Helvetica-Bold')),
            Paragraph(title, ParagraphStyle('takethread', parent=BODY, fontSize=14, textColor=BODY_TEXT, fontName='Helvetica-Bold', spaceAfter=8, spaceBefore=4)),
            Paragraph(content.replace('\n', '<br/>'), ParagraphStyle('takecontent', parent=BODY, fontSize=11, leading=17)),
        ]
        row.append(cell)
        if len(row) == 2:
            rows_data.append(row)
            row = []
    
    grid2 = Table(rows_data, colWidths=[two_col_w, two_col_w])
    grid2.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, GREY_LINE),
    ]))
    story.append(grid2)
    
    # === PAGE 10: CLOSING PRINCIPLE (svart side) ===
    story.append(PageBreak())
    story.append(Spacer(1, 5*cm))
    final_table = Table([[
        Paragraph('10', SECTION_NUM)
    ], [
        Paragraph('Vi står ved eit<br/>eksistensielt val.', BIG_IDEA)
    ], [
        Paragraph(
            'Anten byggjer vi governance-infrastruktur no — <i>før</i> brudpunktet —<br/>'
            'eller så reagerer vi etter ein serie med kriser vi kunne ha forutsett.',
            ParagraphStyle('finalbody', parent=BODY, fontSize=14, leading=22, textColor=GREY_TEXT))
    ], [
        Paragraph(
            '"The question is not whether AI will fail.<br/>'
            'It is whether we will have built the structure<br/>'
            'to govern that failure when it arrives."',
            PRINCIPLE)
    ]], colWidths=[W - 2*MARGIN])
    final_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BG),
        ('BACKGROUND', (0, -1), (-1, -1), BLACK_BOX),
        ('TOPPADDING', (0, 0), (-1, 0), 30),
        ('TOPPADDING', (0, 1), (-1, -1), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 40),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
    ]))
    story.append(final_table)
    
    # === METADATA-SIDE ===
    story.append(PageBreak())
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph('METODIKK OG DATAGRUNNLAG', ParagraphStyle(
        'methodTitle', parent=BODY, fontSize=10, textColor=GOLD, fontName='Helvetica-Bold', spaceAfter=12)))
    
    methods = [
        ('Datakjelder', 
         'AI Incidents Database (AIID) — 1 571 rapporterte hendingar.\n'
         'Osint-innsamling — 7 314 medierapporter (2024–Q3 2026).\n'
         'Validering: kryssjekk mellom 4 uavhengige kjelder.'),
        ('Prognose-modell',
         'Logistisk vekst (S-kurve) med metning K = 1 milliard.\n'
         'Ensemble: Poisson, trend-ekstrapolasjon, og ARFIMA.\n'
         'Multi-agent-feilrate: 0,30 % vs 0,01 % for enkle agentar (30×).'),
        ('Avgrensingar',
         'Mørketal: 10–100× under-rapportering (anslag, ikkje målt).\n'
         'Regulatorisk gap: EU AI Act trer i kraft 2027 — usikkert effekt.\n'
         'Historiske data startar 2020 — kort tidsserie.'),
    ]
    
    for title, content in methods:
        story.append(Paragraph(title, ParagraphStyle(
            'meth2', parent=BODY, fontSize=11, textColor=BODY_TEXT, fontName='Helvetica-Bold', spaceBefore=16, spaceAfter=6)))
        story.append(Paragraph(content.replace('\n', '<br/>'), 
            ParagraphStyle('methc', parent=BODY, fontSize=10, leading=16, textColor=GREY_TEXT)))
    
    story.append(Spacer(1, 2*cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=GREY_LINE, spaceBefore=12))
    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph(
        '© 2026 · Agentic Execution Risk Research · Versjon 1.0 · Juli 2026', 
        ParagraphStyle('footer', parent=BODY, fontSize=9, textColor=GREY_TEXT, alignment=TA_CENTER)))
    
    return story


def main():
    print(f"Byggjer proff rapport — {NOW:%Y-%m-%d %H:%M}")
    
    story = build_story()
    
    # Bruker cover_page_template side 1, vanleg sidemal sidan 2+
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
    )
    doc.build(story, onFirstPage=cover_page_template, onLaterPages=page_template)
    
    size_kb = OUT.stat().st_size / 1024
    print(f"\n✅ Proff rapport generert: {OUT}")
    print(f"   Storleik: {size_kb:.0f} KB")
    print(f"   Diagram: 5 store matplotlib-grafar + 2 mørke prinsippsider")
    print(f"   Design: Philips/RTEH-inspirert — dark cover, gull-aksent, ekstrem whitespace")


if __name__ == '__main__':
    main()
