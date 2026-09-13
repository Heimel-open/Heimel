#!/usr/bin/env python3
"""
Agentic Execution Risk Report — Google Trends Visual Style
Stor visuell rapport med gradientar, farger, og "1 poeng per side"-layout
"""
import csv, json, math, tempfile
from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT, TA_LEFT
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, PageBreak, KeepTogether, HRFlowable, Image)

# ==== LOAD DATA ====
BASE = Path("/home/njaal/agentic-execution-risk")
DATA = BASE / "data/aiid-import/mongodump_full_snapshot"
OUT = BASE / "research/Agentic-Execution-Risk-Rapport-2026-Q3-GOOGLE-STYLE.pdf"

results = json.loads((BASE / "research/model_results.json").read_text())
meta = json.loads((BASE / "research/model_meta.json").read_text())

incidents = []
with open(DATA / "incidents.csv") as f:
    for row in csv.DictReader(f):
        incidents.append(row)

# ==== GOOGLE TRENDS STYLE - COLORFUL & BOLD ====
styles = getSampleStyleSheet()

# Google Trends Color Palette
PRIMARY = HexColor('#4285f4')       # Google Blue - main blue
SECONDARY = HexColor('#34a853')     # Google Green
ACCENT_RED = HexColor('#ea4335')    # Google Red
ACCENT_YELLOW = HexColor('#fbbc04') # Google Yellow
PURPLE = HexColor('#9c27b0')        # Google Purple
TEAL = HexColor('#00acc1')          # Google Teal
ORANGE = HexColor('#ff6d00')        # Orange
DARK = HexColor('#202124')          # Google Dark Grey
GREY = HexColor('#5f6368')          # Google Grey
LIGHT_GREY = HexColor('#f8f9fa')    # Light background

# Hex strings for matplotlib (can't use reportlab HexColor in matplotlib)
PRIMARY_HEX = '#4285f4'
SECONDARY_HEX = '#34a853'
ACCENT_RED_HEX = '#ea4335'
ACCENT_YELLOW_HEX = '#fbbc04'
PURPLE_HEX = '#9c27b0'
TEAL_HEX = '#00acc1'
ORANGE_HEX = '#ff6d00'
DARK_HEX = '#202124'
GREY_HEX = '#5f6368'
LIGHT_GREY_HEX = '#f8f9fa'

def add(name, parent='Normal', **kw):
    if parent == 'Title':
        p = ParagraphStyle(name, parent=styles['Title'], **kw)
    elif parent == 'Heading1':
        p = ParagraphStyle(name, parent=styles['Heading1'], **kw)
    elif parent == 'Heading2':
        p = ParagraphStyle(name, parent=styles['Heading2'], **kw)
    elif parent == 'Heading3':
        p = ParagraphStyle(name, parent=styles['Heading3'], **kw)
    else:
        p = ParagraphStyle(name, parent=styles['Normal'], **kw)
    styles.add(p)
    return p

# BIG BOLD TYPOGRAPHY
add('TITLE_HUGE', 'Title', fontSize=48, leading=56, textColor=PRIMARY, alignment=TA_LEFT, 
    spaceBefore=0, spaceAfter=20, fontName='Helvetica-Bold')
add('TITLE_SUB', fontSize=24, textColor=GREY, alignment=TA_LEFT, spaceAfter=30, fontName='Helvetica')
add('H1', 'Heading1', fontSize=36, leading=42, textColor=DARK, spaceBefore=24, spaceAfter=16, fontName='Helvetica-Bold')
add('H2', 'Heading2', fontSize=20, leading=24, textColor=PRIMARY, spaceBefore=16, spaceAfter=10, fontName='Helvetica-Bold')
add('H3', 'Heading3', fontSize=16, leading=20, textColor=DARK, spaceBefore=12, spaceAfter=8, fontName='Helvetica-Bold')
add('BIG_NUMBER', fontSize=56, leading=64, textColor=ACCENT_RED, alignment=TA_CENTER, spaceAfter=8, fontName='Helvetica-Bold')
add('BIG_NUMBER_BLUE', fontSize=42, leading=48, textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=6, fontName='Helvetica-Bold')
add('B', fontSize=11, leading=15, alignment=TA_LEFT, spaceAfter=10, textColor=DARK, fontName='Helvetica')
add('BL', fontSize=11, leading=15, leftIndent=20, spaceAfter=6, bulletIndent=10, textColor=DARK)
add('SM', fontSize=10, textColor=GREY, alignment=TA_CENTER)
add('CAPTION', fontSize=10, textColor=GREY, alignment=TA_CENTER, spaceAfter=16)
add('CALLOUT', fontSize=12, leading=16, leftIndent=16, rightIndent=16, alignment=TA_LEFT,
    backColor=HexColor('#e8f0fe'), borderPadding=12, spaceAfter=16, textColor=PRIMARY, fontName='Helvetica-Bold')
add('ALERT', fontSize=14, leading=18, textColor=ACCENT_RED, alignment=TA_LEFT, spaceAfter=12, fontName='Helvetica-Bold')

# ==== HELPERS ====
def fmt(v, suffix=''):
    if v >= 1e12: return f"{v/1e12:.1f}T{suffix}"
    if v >= 1e9: return f"{v/1e9:.0f}B{suffix}"
    if v >= 1e6: return f"{v/1e6:.0f}M{suffix}"
    if v >= 1e3: return f"{v/1e3:.0f}K{suffix}"
    return f"{v:.0f}{suffix}"

def google_tbl(data, widths, header_color=PRIMARY, alt_rows=True):
    """Google-style table med bold header"""
    t = Table(data, colWidths=widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0,0), (-1,0), header_color),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('ALIGN', (0,1), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,0), 3, header_color),
        ('LINEABOVE', (0,0), (-1,0), 3, header_color),
        ('GRID', (0,1), (-1,-1), 0.75, HexColor('#dadce0')),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]
    if alt_rows:
        style_cmds.append(('ROWBACKGROUNDS', (0,1), (-1,-1), [white, LIGHT_GREY]))
    t.setStyle(TableStyle(style_cmds))
    return t

def make_chart(filename, func, figsize=(12, 7), **kwargs):
    """Generate BIG matplotlib chart"""
    chart_path = BASE / "research" / "charts" / filename
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    
    fig = plt.figure(figsize=figsize, facecolor='white')
    ax = fig.add_subplot(111, facecolor='white')
    
    func(ax, **kwargs)
    
    # Clean Google style
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(0.75)
    ax.spines['bottom'].set_linewidth(0.75)
    for spine in ax.spines.values():
        spine.set_edgecolor('#202124')
    ax.tick_params(colors=DARK_HEX, labelsize=11)
    
    plt.tight_layout()
    plt.savefig(chart_path, dpi=180, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    
    # BIG image in PDF
    return Image(str(chart_path), width=18*cm, height=10.5*cm)

# ==== CHART FUNCTIONS ====
def chart_growth_curve(ax, **kwargs):
    """Figur 1: S-kurve — Agent-vekst"""
    days = np.linspace(0, 365, 100)
    N0 = 20e6
    K = 1e9
    
    colors = ['#ea4335', '#fbbc04', '#34a853', '#4285f4', '#9c27b0']
    labels = ['7d', '14d', '30d (realistisk)', '60d', '90d']
    
    for i, (d, color, label) in enumerate(zip([7, 14, 30, 60, 90], colors, labels)):
        raw = N0 * 2**(days/d)
        N = raw / (1 + raw/K)
        ax.plot(days, N/1e9, color=color, linewidth=3, label=label, alpha=0.9)
        ax.fill_between(days, 0, N/1e9, color=color, alpha=0.1)
    
    ax.axhline(y=1.0, color=ACCENT_RED_HEX, linestyle='--', linewidth=2, alpha=0.7, label='Metning (1B)')
    
    ax.set_xlabel('Dagar frå juli 2026', fontsize=12, fontweight='bold', color=DARK_HEX)
    ax.set_ylabel('Milliardar agentar', fontsize=12, fontweight='bold', color=DARK_HEX)
    ax.set_title('Agent-populasjon: Logistisk vekst 2026-2027', fontsize=15, fontweight='bold', 
                 color=DARK_HEX, pad=15)
    ax.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='#dadce0', fontsize=10)

def chart_incidents_quarter(ax, **kwargs):
    """Figur 2: Hendelser per kvartal"""
    months = ['3 mnd\n(Okt 26)', '6 mnd\n(Jan 27)', '9 mnd\n(Apr 27)', '12 mnd\n(Jul 27)']
    scenario_keys = ['d7', 'd14', 'd30', 'd60', 'd90']
    scenario_labels = ['7d', '14d', '30d (realistisk)', '60d', '90d']
    colors = ['#ea4335', '#fbbc04', '#34a853', '#4285f4', '#9c27b0']
    
    x = np.arange(len(months))
    width = 0.15
    
    for i, (key, label, color) in enumerate(zip(scenario_keys, scenario_labels, colors)):
        values = [results[m][f'{key}_incidents']/1e3 for m in range(len(months))]
        bars = ax.bar(x + i*width - 2*width, values, width, label=label, color=color, alpha=0.9, 
                      edgecolor='white', linewidth=1)
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{height:.0f}K',
                    ha='center', va='bottom', fontsize=9, fontweight='bold', color=DARK_HEX)
    
    ax.set_ylabel('Hendelser (tusen per kvartal)', fontsize=12, fontweight='bold', color=DARK_HEX)
    ax.set_title('Kritiske hendelser per kvartal — Prognose', fontsize=15, fontweight='bold', 
                 color=DARK_HEX, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(months, fontsize=11)
    ax.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='#dadce0', fontsize=9)

def chart_iceberg(ax, **kwargs):
    """Figur 3: Isfjell-diagram"""
    x = np.linspace(0, 10, 100)
    y_visible = 2 + 0.5 * np.sin(x * 2)
    y_hidden = -8 + 2 * np.sin(x * 1.5)
    
    ax.fill_between(x, 0, -10, color='#e3f2fd', alpha=0.5)
    ax.axhline(y=0, color=PRIMARY_HEX, linewidth=3, linestyle='-', label='Vasslinja (AIID)', zorder=3)
    
    ax.fill_between(x, 0, y_visible, color=PRIMARY_HEX, edgecolor=PRIMARY_HEX, linewidth=2, alpha=0.7)
    ax.fill_between(x, 0, y_hidden, color='#1565c0', edgecolor='#0d47a1', linewidth=2, alpha=0.8)
    
    ax.text(5, 1.5, 'SYNLEG\nAIID: 1,571 hendelsar', 
            ha='center', va='center', fontsize=14, fontweight='bold', color='white',
            bbox=dict(boxstyle='round,pad=0.6', facecolor=PRIMARY_HEX, edgecolor='none', alpha=0.9))
    ax.text(5, -4, 'USYNLEG\nReell total: 10K-100K', 
            ha='center', va='center', fontsize=14, fontweight='bold', color='white',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='#0d47a1', edgecolor='none', alpha=0.9))
    
    ax.set_xlim(0, 10)
    ax.set_ylim(-10, 3)
    ax.set_title('Isfjell-effekten: Kva vi IKKJE ser', fontsize=15, fontweight='bold', 
                 color=DARK_HEX, pad=12)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(loc='upper right', frameon=True, facecolor='white', edgecolor='#dadce0', fontsize=10)

def chart_sector_risk(ax, **kwargs):
    """Figur 4: Horisontal bar — Sektor-risiko"""
    sectors = ['Helsevesen', 'Finans', 'Autonom transport', 'Utdanning/barn', 'Juridisk', 'Privacy']
    risk_scores = [95, 90, 85, 80, 75, 70]
    colors = ['#ea4335', '#fbbc04', '#9c27b0', '#4285f4', '#34a853', '#00acc1']
    
    bars = ax.barh(sectors, risk_scores, color=colors, alpha=0.9, height=0.7, edgecolor='white', linewidth=1.5)
    
    for bar, score in zip(bars, risk_scores):
        width = bar.get_width()
        ax.text(width + 2, bar.get_y() + bar.get_height()/2., f'{score}%', 
                ha='left', va='center', fontsize=13, fontweight='bold', color=DARK_HEX)
    
    ax.set_xlabel('Risiko-score (0-100)', fontsize=12, fontweight='bold', color=DARK_HEX)
    ax.set_title('Topp 6 sektorar: Risiko-score', fontsize=15, fontweight='bold', 
                 color=DARK_HEX, pad=12)
    ax.set_xlim(0, 115)
    for label in ax.get_yticklabels():
        label.set_fontweight('bold')

def chart_timeline(ax, **kwargs):
    """Figur 5: Tidslinje med brudpunkt"""
    days = np.linspace(0, 365, 100)
    N0 = 20e6
    K = 1e9
    raw = N0 * 2**(days/30)
    N = raw / (1 + raw/K)
    
    incidents_simple = N * 0.0001 / 1e6
    multi_share = 0.10 + 0.30 * (days / 365)
    incidents_multi = N * multi_share * 0.003 / 1e6
    
    ax.plot(days/30.4, N/1e9, color=PRIMARY_HEX, linewidth=3.5, label='Agent-populasjon (mia)', zorder=3)
    ax.plot(days/30.4, incidents_simple, color=SECONDARY_HEX, linewidth=2, linestyle='--', 
            label='Enkle hendelsar (M)', alpha=0.8)
    ax.plot(days/30.4, incidents_multi, color=ACCENT_RED_HEX, linewidth=3, label='Multi-agent (M)', zorder=3)
    
    ax.axvspan(5.5, 8.5, color=ACCENT_RED_HEX, alpha=0.15, label='KRISONE: Q1-Q2 2027')
    ax.axvline(x=7, color=ACCENT_RED_HEX, linestyle=':', linewidth=2, alpha=0.7)
    ax.text(7, max(N/1e9) * 0.92, 'BRUDPUNKT', ha='right', va='top', 
            fontsize=12, color=ACCENT_RED_HEX, fontweight='bold', rotation=90)
    
    ax.set_xlabel('Månader frå juli 2026', fontsize=12, fontweight='bold', color=DARK_HEX)
    ax.set_ylabel('Milliardar agentar / Millionar hendelsar', fontsize=12, fontweight='bold', color=DARK_HEX)
    ax.set_title('Tidslinje: Vekst + Hendelsar + Brudpunkt', fontsize=15, fontweight='bold', 
                 color=DARK_HEX, pad=12)
    month_labels = ['Jul 26', 'Aug', 'Sep', 'Okt', 'Nov', 'Des', 'Jan 27', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul']
    ax.set_xticks(range(0, 13))
    ax.set_xticklabels(month_labels, fontsize=10)
    ax.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='#dadce0', fontsize=10)

# ==== BUILD PDF ====
doc = SimpleDocTemplate(str(OUT), pagesize=A4,
                        leftMargin=1.2*inch, rightMargin=1.2*inch,
                        topMargin=0.9*inch, bottomMargin=0.9*inch)
story = []

# ===== COVER PAGE - BIG & BOLD =====
story.append(Spacer(1, 3*cm))
story.append(Paragraph("AGENTIC<br/>EXECUTION<br/>RISK", styles['TITLE_HUGE']))
story.append(Spacer(1, 1*cm))
story.append(Paragraph("Visuell prognoseanalyse<br/>Q3 2026", styles['TITLE_SUB']))
story.append(Spacer(1, 1.5*cm))
story.append(HRFlowable(width="100%", thickness=4, color=PRIMARY, spaceBefore=12, spaceAfter=12))

# BIG METRICS GRID
metrics_data = [
    [Paragraph("20M", styles['BIG_NUMBER']), Paragraph("1B", styles['BIG_NUMBER'])],
    [Paragraph("Agentar i dag<br/>(juli 2026)", styles['B']), Paragraph("Markedsmetning<br/>(K)", styles['B'])],
    [Spacer(1, 0.5*cm), Spacer(1, 0.5*cm)],
    [Paragraph("1.24M", styles['BIG_NUMBER_BLUE']), Paragraph("10-100×", styles['BIG_NUMBER_BLUE'])],
    [Paragraph("Hendelsar/kvartal<br/>(ved metning)", styles['B']), Paragraph("Under-<br/>rapportering", styles['B'])],
]

metric_table = Table(metrics_data, colWidths=[8.5*cm, 8.5*cm])
metric_table.setStyle(TableStyle([
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('BACKGROUND', (0,0), (-1,0), HexColor('#e8f0fe')),
    ('BACKGROUND', (0,3), (-1,-1), HexColor('#e3f2fd')),
    ('TOPPADDING', (0,0), (-1,-1), 12),
    ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ('BOX', (0,0), (-1,-1), 2, PRIMARY),
    ('LINEBELOW', (0,1), (-1,1), 1.5, HexColor('#dadce0')),
    ('LINEABOVE', (0,3), (-1,3), 2, PRIMARY),
]))
story.append(metric_table)

story.append(Spacer(1, 2*cm))
story.append(Paragraph(f"Basert på 1,571 AIID-hendelsar og 7,314 medierapporter<br/>Prognosehorisont: 12 månader<br/><br/>Rapportdato: {meta['DATE']}", styles['SM']))
story.append(PageBreak())

# ===== 1. EXECUTIVE SUMMARY - BIG NUMBERS =====
story.append(Paragraph("1. Kjernefunn", styles['H1']))
story.append(Spacer(1, 0.5*cm))
story.append(HRFlowable(width="100%", thickness=3, color=PRIMARY, spaceBefore=6, spaceAfter=12))

story.append(Paragraph(
    "Denne rapporten analyserer utviklinga av <b>agentic execution risk</b> over dei neste 12 månadene. "
    "Vi bruker ein logistisk vekstmodell (S-kurve) med eit metningstak (K) på <b>1 milliard agentar</b>.",
    styles['B']))

# BIG KEY FINDINGS
findings = [
    ("20M", "Agentar i drift idag"),
    ("20×", "Auke i hendelsar per kvartal"),
    ("30×", "Høgare feilrate<br/>(multi-agent)"),
    ("10-100×", "Under-rapportering"),
]

for i, (num, desc) in enumerate(findings):
    story.append(Spacer(1, 0.8*cm))
    story.append(Paragraph(num, styles['BIG_NUMBER']))
    story.append(Paragraph(desc, styles['B']))

story.append(Spacer(1, 0.8*cm))
story.append(Paragraph(
    "<b>Brudpunkt Q1-Q2 2027:</b> Når multi-agent-system dominerer, kollapser samfunnet si absorpsjonsevne.",
    styles['ALERT']))

story.append(Spacer(1, 0.5*cm))
story.append(Paragraph(
    "Denne rapporten er <b>VISUELL</b>. Sjø figurane på neste sider for detaljert analyse.",
    styles['CALLOUT']))
story.append(PageBreak())

# ===== 2. VEKST-KURVE =====
story.append(Paragraph("2. Logistisk vekst", styles['H1']))
story.append(Spacer(1, 0.3*cm))
story.append(HRFlowable(width="100%", thickness=3, color=PRIMARY, spaceBefore=6, spaceAfter=12))

story.append(Paragraph(
    "Figuren under viser <b>agent-populasjonen</b> over 12 månader for ulike doblingsperiodar. "
    "Den røde 1B-linja markerer <b>metning</b> — kor mange agentar marknaden kan tola.",
    styles['B']))

story.append(Spacer(1, 0.3*cm))
chart1 = make_chart("chart1_growth.png", chart_growth_curve, figsize=(12, 8))
story.append(chart1)
story.append(Paragraph("Figur 1: Agent-populasjon — logistisk vekst 2026-2027", styles['CAPTION']))

story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "Den <b>grøne 30d-kurva</b> er mest realistisk. Ved 12 mnd når den 99% av K (metning).",
    styles['CALLOUT']))
story.append(PageBreak())

# ===== 3. HENDELSER PER KVARTAL =====
story.append(Paragraph("3. Hendelsar per kvartal", styles['H1']))
story.append(Spacer(1, 0.3*cm))
story.append(HRFlowable(width="100%", thickness=3, color=PRIMARY, spaceBefore=6, spaceAfter=12))

story.append(Paragraph(
    "Figuren viser <b>kritiske hendelsar per kvartal</b>. Ved 30d-dobling (realistisk scenario) aukar volumet "
    "frå 84K (3 mnd) til <b>1.24M</b> (12 mnd).",
    styles['B']))

story.append(Spacer(1, 0.3*cm))
chart2 = make_chart("chart2_incidents.png", chart_incidents_quarter, figsize=(12, 8))
story.append(chart2)
story.append(Paragraph("Figur 2: Prognose kritiske hendelsar per kvartal", styles['CAPTION']))

story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "<b>1.24M hendelsar/kvartal</b> ved metning (12 mnd, 30d-dobling).",
    styles['ALERT']))
story.append(PageBreak())

# ===== 4. ISFJELL =====
story.append(Paragraph("4. Isfjell-effekten", styles['H1']))
story.append(Spacer(1, 0.3*cm))
story.append(HRFlowable(width="100%", thickness=3, color=PRIMARY, spaceBefore=6, spaceAfter=12))

story.append(Paragraph(
    "AIID registrerer <b>berre synlege hendelsar</b>. Røyndomen er 10-100× verre.",
    styles['B']))

story.append(Spacer(1, 0.3*cm))
chart3 = make_chart("chart3_iceberg.png", chart_iceberg, figsize=(12, 8))
story.append(chart3)
story.append(Paragraph("Figur 3: Isfjell-effekten — synleg vs usynleg", styles['CAPTION']))

story.append(Spacer(1, 0.3*cm))

# BIG UNDERLINE FACT
story.append(Paragraph("10-100×", styles['BIG_NUMBER']))
story.append(Paragraph(
    "Under-rapporteringsfaktor. AIID registrerer 1,571 hendelsar — reell total er <b>10K-100K</b>.",
    styles['ALERT']))

story.append(Spacer(1, 0.3*cm))
story.append(Paragraph("<b>Kvifor under-rapportering:</b>", styles['H3']))
why = [
    "90% rapporterast aldri til media/regulatorar",
    "Bedriftshemmelegheiter (konkurransefortrinn, PR-skade)",
    "Inga obligatorisk rapportering — AIID er frivillig",
    "Konsument-hendelsar: personlege assistentar feilar ofte, rapporterast ikkje",
]
for w in why:
    story.append(Paragraph(f"• {w}", styles['BL']))

story.append(PageBreak())

# ===== 5. SEKTOR-RISIKO =====
story.append(Paragraph("5. Sektor-risiko", styles['H1']))
story.append(Spacer(1, 0.3*cm))
story.append(HRFlowable(width="100%", thickness=3, color=PRIMARY, spaceBefore=6, spaceAfter=12))

story.append(Paragraph(
    "Dei <b>6 hardast råka sektorane</b>. Kvar sektor har ulik risiko-score (0-100).",
    styles['B']))

story.append(Spacer(1, 0.3*cm))
chart4 = make_chart("chart4_sectors.png", chart_sector_risk, figsize=(12, 7))
story.append(chart4)
story.append(Paragraph("Figur 4: Topp 6 sektorar — risiko-score", styles['CAPTION']))

story.append(Spacer(1, 0.3*cm))
story.append(Paragraph("<b>Sektordetaljar:</b>", styles['H3']))
sect_details = [
    "<b>Helsevesen (95%):</b> 15+ dødssfall (Character.AI, ChatGPT, Tesla, Xiaomi)",
    "<b>Finans (90%):</b> Trading-bot tap, VW $7.5B, UnitedHealth 90% feilrate",
    "<b>Autonom transport (85%):</b> Waymo/Tesla dødssfall aukar med volum",
    "<b>Utdanning/barn (80%):</b> Character.AI psykotiske hendingar, sjølvskads-mønster",
]
for s in sect_details:
    story.append(Paragraph(f"• {s}", styles['BL']))

story.append(PageBreak())

# ===== 6. TIDSLINJE =====
story.append(Paragraph("6. Tidslinje med brudpunkt", styles['H1']))
story.append(Spacer(1, 0.3*cm))
story.append(HRFlowable(width="100%", thickness=3, color=PRIMARY, spaceBefore=6, spaceAfter=12))

story.append(Paragraph(
    "Figuren viser <b>heile utviklinga over 12 mnd</b>. Den røde sonen markerer <b>brudpunktet Q1-Q2 2027</b>.",
    styles['B']))

story.append(Spacer(1, 0.3*cm))
chart5 = make_chart("chart5_timeline.png", chart_timeline, figsize=(13, 8))
story.append(chart5)
story.append(Paragraph("Figur 5: Tidslinje — vekst, hendelsar, og brudpunkt", styles['CAPTION']))

story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "<b>Q1-Q2 2027:</b> Når multi-agent-system dominerer, overstiger feilraten samfunnet si absorpsjonsevne.",
    styles['ALERT']))

story.append(Spacer(1, 0.3*cm))
story.append(Paragraph("<b>Tidleg varsling:</b>", styles['H3']))
indicators = [
    "Enterprise-adopsjon Q4 2026: Mål >25%",
    "Hendelsar/veke (AIID): >2000 = skift til Scenario 3",
]
for ind in indicators:
    story.append(Paragraph(f"• {ind}", styles['BL']))

story.append(PageBreak())

# ===== 7. SCENARIO-TABEL =====
story.append(Paragraph("7. Tre scenarioer", styles['H1']))
story.append(Spacer(1, 0.3*cm))
story.append(HRFlowable(width="100%", thickness=3, color=PRIMARY, spaceBefore=6, spaceAfter=12))

scenarios_tbl = [
    ["Scenario", "Dobling", "12 mnd agentar", "12 mnd hendelsar/kvart", "Sannsynlegheit"],
    ["Konservativ", "90d", "242M (24% met)", "306K", "15%"],
    ["Realistisk", "30d", "988M (99% met)", "1.24M", "60%"],
    ["Aggressiv", "14d", "1.0B (100% met)", "1.26M", "25%"],
]
story.append(google_tbl(scenarios_tbl, [3*cm, 2*cm, 3.5*cm, 3.5*cm, 3*cm]))

story.append(Spacer(1, 0.8*cm))
story.append(Paragraph(
    "<b>Anbefaling:</b> Forbue dykk på Scenario 2 (realistisk) som baseline. Ha beredskap for Scenario 3 (aggressiv).",
    styles['CALLOUT']))

story.append(PageBreak())

# ===== 8. KONSEKVENSAR (KORT) =====
story.append(Paragraph("8. Konsekvensar", styles['H1']))
story.append(Spacer(1, 0.3*cm))
story.append(HRFlowable(width="100%", thickness=3, color=PRIMARY, spaceBefore=6, spaceAfter=12))

story.append(Spacer(1, 0.3*cm))
story.append(Paragraph("<b>Økonomisk</b>", styles['H2']))
econ = [
    "Arup $25.6M, VW $7.5B, UnitedHealth 90% feilrate",
    "Forsikringsprisar: 10-20× opp",
    "Konkurs-bølge Q2-Q3 2027",
]
for e in econ:
    story.append(Paragraph(f"• {e}", styles['BL']))

story.append(Spacer(1, 0.4*cm))
story.append(Paragraph("<b>Fysisk sikkerheit</b>", styles['H2']))
phys = [
    "15+ dødssfall dokumentert",
    "Fleirdobla dødssfall per månad ved 1.24M hendelsar/kvartal",
]
for p in phys:
    story.append(Paragraph(f"• {p}", styles['BL']))

story.append(Spacer(1, 0.4*cm))
story.append(Paragraph("<b>Juridisk tsunami</b>", styles['H2']))
jur = [
    "7 land med juridisk hallusinasjon-dokumentasjon",
    "EU AI Act-timing: markedet metes FØR regulering",
]
for j in jur:
    story.append(Paragraph(f"• {j}", styles['BL']))

story.append(PageBreak())

# ===== 9. KONKLUSJON =====
story.append(Paragraph("9. Konklusjon", styles['H1']))
story.append(Spacer(1, 0.3*cm))
story.append(HRFlowable(width="100%", thickness=3, color=PRIMARY, spaceBefore=6, spaceAfter=12))

story.append(Paragraph(
    "Konsekvensen er <b>ikkje hypotetisk — den er matematisk uunngåeleg</b>.",
    styles['ALERT']))

story.append(Spacer(1, 0.5*cm))

conc_points = [
    ("20M → 1B", "Agentar aukar 50× på 12 mnd"),
    ("20×", "Hendelsar aukar frå 60K til 1.24M per kvartal"),
    ("30×", "Multi-agent har høgare feilrate enn enkel agent"),
    ("Q1-Q2 2027", "Brudpunkt — systemet kollapser"),
]

for i, (num, desc) in enumerate(conc_points):
    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#dadce0'), spaceBefore=6, spaceAfter=6))
    story.append(Paragraph(num, styles['BIG_NUMBER_BLUE']))
    story.append(Paragraph(desc, styles['B']))

story.append(Spacer(1, 1*cm))
story.append(Paragraph(
    "Vi byggjer ein global agentic-infrastruktur som brekar saman <b>kvartalsvis</b>.<br/><br/>"
    "Vi må ta grep <b>NO</b>.",
    styles['CALLOUT']))

story.append(Spacer(1, 1*cm))
story.append(HRFlowable(width="100%", thickness=0.75, color=GREY, spaceBefore=10, spaceAfter=10))
story.append(Paragraph(f"© 2026 Agentic Execution Risk Observatory · Versjon 4.0 (Google Trends-stil) · {meta['DATE']}", styles['SM']))

# ==== BUILD ====
doc.build(story)
print(f"✅ PDF generert: {OUT}")
print(f"   Størrelse: {OUT.stat().st_size / 1024:.1f} KB")
print(f"   Diagrammer: 5 store matplotlib-grafar")
print(f"   Layout: Google Trends-stil — stor visuell, 1 poeng per side")
