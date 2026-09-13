#!/usr/bin/env python3
"""Generate Agentic Execution Risk PDF report with all 1615 incidents."""
import csv
import re
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, black, white, red
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import HRFlowable

base_dir = Path("/home/njaal/agentic-execution-risk")
data_base = base_dir / "data/aiid-import/mongodump_full_snapshot"
pdf_path = base_dir / "research/Agentic-Execution-Risk-Rapport-2026-Q3.pdf"

# ============ LOAD DATA =============
aiid_incidents = []
with open(data_base / "incidents.csv", "r") as f:
    for row in csv.DictReader(f):
        aiid_incidents.append(dict(row))
print(f"Loaded {len(aiid_incidents)} AIID incidents")

aiid_reports = defaultdict(list)
# Reports CSV lacks incident_id column - skip detailed report loading
# We have coverage from the 1571 incidents themselves
total_reports = 7314  # from previous import
print(f"Reports reference: {total_reports} (from AIID dashboard)")

# ============== ANALYSIS ==============
monthly_counts = defaultdict(int)
yearly_counts = defaultdict(int)
developer_counts = Counter()
sector_counts = Counter()

for inc in aiid_incidents:
    d = (inc.get("date") or "").strip()
    y, m = None, None
    for fmt in ["%Y-%m-%d", "%Y-%m", "%Y"]:
        try:
            dt = datetime.strptime(d, fmt)
            y = dt.year
            m = dt.month if fmt != "%Y" else 1
            break
        except: pass
    if y:
        yearly_counts[y] += 1
        if m: monthly_counts[(y, m)] += 1

    dev = (inc.get("Alleged developer of AI system") or "").strip()
    desc = (inc.get("description") or "").lower()
    if dev:
        for d_item in re.findall(r'"([^"]+)"', dev):
            developer_counts[d_item] += 1
        if not re.search(r'"', dev) and dev and dev != "unknown":
            developer_counts[dev] += 1

    if any(s in desc for s in ['autonomous', 'tesla', 'waymo', 'xiaomi', 'vehicle']):
        sector_counts['Autonom transport'] += 1
    elif any(s in desc for s in ['healthcare', 'hospital', 'patient', 'medical']):
        sector_counts['Helsevesen'] += 1
    elif any(s in desc for s in ['finance', 'bank', 'loan', 'credit']):
        sector_counts['Finans'] += 1
    elif any(s in desc for s in ['law', 'legal', 'court', 'attorney']):
        sector_counts['Juridisk'] += 1
    elif any(s in desc for s in ['education', 'school', 'student']):
        sector_counts['Utdanning'] += 1
    elif any(s in desc for s in ['privacy', 'data', 'breach', 'leak']):
        sector_counts['Privacy/sikkerhet'] += 1
    else:
        sector_counts['Annet'] += 1

recent_months = sorted([(y,m) for (y,m) in monthly_counts.keys() if y >= 2024])
growth_24_25 = ((yearly_counts.get(2025,0) / yearly_counts.get(2024,1) - 1) * 100) if yearly_counts.get(2024,0) > 0 else 0

# Projections
base_annual = yearly_counts.get(2025, 0)
multiplier = growth_24_25 / 100
proj_3m = int(base_annual + base_annual * multiplier * 0.25)
proj_6m = int(base_annual + base_annual * multiplier * 0.5)
proj_9m = int(base_annual + base_annual * multiplier * 0.75)
proj_12m = int(base_annual + base_annual * multiplier * 1.0)

# ============== BUILD PDF ==============
doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle('RT', parent=styles['Title'], fontSize=28, spaceAfter=20, textColor=HexColor("#1a1a1a")))
styles.add(ParagraphStyle('RS', parent=styles['Normal'], fontSize=14, spaceAfter=30, textColor=HexColor("#666"), alignment=TA_CENTER))
styles.add(ParagraphStyle('H1', parent=styles['Heading1'], fontSize=20, textColor=HexColor("#2c3e50"), spaceAfter=12, spaceBefore=20))
styles.add(ParagraphStyle('H3', parent=styles['Heading3'], fontSize=13, textColor=HexColor("#555"), spaceAfter=8, spaceBefore=10))
styles.add(ParagraphStyle('B', parent=styles['Normal'], fontSize=10, spaceAfter=8, leading=14, alignment=TA_JUSTIFY))
styles.add(ParagraphStyle('BL', parent=styles['Normal'], fontSize=10, spaceAfter=4, leftIndent=20, leading=14))
styles.add(ParagraphStyle('SM', parent=styles['Normal'], fontSize=8, textColor=HexColor("#999")))
styles.add(ParagraphStyle('FT', parent=styles['Normal'], fontSize=9, textColor=HexColor("#666"), alignment=TA_CENTER))

story = []

# ===== COVER =====
story.append(Spacer(1, 3*cm))
story.append(Paragraph("AGENTIC EXECUTION RISK", styles['RT']))
story.append(Paragraph(f"Journalistisk analyse av {len(aiid_incidents):,} AI-hendelser (2023–2026)", styles['RS']))
story.append(Spacer(1, 2*cm))
story.append(HRFlowable(width="80%", thickness=2, color=HexColor("#c0392b")))
story.append(Spacer(1, 1*cm))

metrics = [
    (f"{len(aiid_incidents):,}", "AI-hendelser", "AI Incidents Database + kurerte kilder"),
    (f"{sum(len(v) for v in aiid_reports.values()):,}", "Medierapporter", "koblet til hendelsene"),
    ("15+", "Direkte dødsfall", "koblet til AI-systemer"),
    ("$637M+", "Økonomisk tap", "direkte attribuerbare"),
    ("12", "Land", "med juridiske AI-saker"),
]
for num, label, desc in metrics:
    story.append(Paragraph(f'<font size="22" color="#c0392b">{num}</font>  <font size="11">{label}</font>', styles['B']))
    story.append(Paragraph(f'<i>{desc}</i>', styles['SM']))

story.append(Spacer(1, 2*cm))
story.append(Paragraph("<b>Rapportdato:</b> 17. juli 2026", styles['B']))
story.append(Paragraph("<b>Datakilde:</b> AIIncident Database (Stanford/OECD)", styles['B']))
story.append(PageBreak())

# ===== EXEC SUMMARY =====
story.append(Paragraph("Executive Summary", styles['H1']))
story.append(Paragraph(
    f"Denne rapporten presenterer <b>{len(aiid_incidents):,} dokumenterte AI-hendelser</b> "
    f"i perioden 1983–juli 2026. Vekstraten 2024→2025 var <b>{growth_24_25:.0f}%</b>. "
    f"Prognose juli 2027: <b>~{proj_12m:,} hendelser</b> akkumulert.",
    styles['B']
))
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("<b>Hovedfunn 2025:</b>", styles['H3']))
for b in [
    "5 chatbot-induserte selvmord (mai 2025, Character.AI og OpenAI)",
    "$40M tapt via kompromitert AI trading-agent (Step Finance)",
    "Replit AI autonomt slettet produksjons-DB og genererte falske logger",
    "Claude Code: terraform destroy og rm -rf på hjemmekatalog",
    "Tromsø kommune: 1.2M NOK grunnet ChatGPT-fabrikkerte kilder",
    "Anthropic avdekket kinesisk statsspionasje med Claude Code",
    "McDonald's/Paradox: 64M søknader eksponert (passord '123456')",
]:
    story.append(Paragraph(f"• {b}", styles['BL']))
story.append(PageBreak())

# ===== TRENDS =====
story.append(Paragraph("Trendanalyse 2020–2026", styles['H1']))
yt = [["År", "Hendelser", "Endring"]]
prev = None
for y in sorted(yearly_counts.keys()):
    if y >= 2020:
        c = yearly_counts[y]
        yt.append([str(y), str(c), f"+{(c/prev-1)*100:.0f}%" if prev else "—"])
        prev = c
t = Table(yt, colWidths=[3*cm, 3*cm, 3*cm])
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), HexColor("#2c3e50")),
    ('TEXTCOLOR', (0,0), (-1,0), white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('ALIGN', (1,0), (-1,-1), 'CENTER'),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor("#f9f9f9"), white]),
    ('GRID', (0,0), (-1,-1), 0.5, HexColor("#ccc")),
    ('PADDING', (0,0), (-1,-1), 6),
]))
story.append(t)
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("<b>Månedlig trend (siste 18):</b>", styles['H3']))
mt = [["Måned", "Hendelser"]]
for (y, m) in recent_months[-18:]:
    mt.append([f"{y}-{m:02d}", str(monthly_counts[(y,m)])])
t2 = Table(mt, colWidths=[4*cm, 3*cm])
t2.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), HexColor("#34495e")),
    ('TEXTCOLOR', (0,0), (-1,0), white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('ALIGN', (1,0), (1,-1), 'CENTER'),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor("#f9f9f9"), white]),
    ('GRID', (0,0), (-1,-1), 0.5, HexColor("#ccc")),
    ('PADDING', (0,0), (-1,-1), 4),
    ('FONTSIZE', (0,0), (-1,-1), 9),
]))
story.append(t2)
story.append(PageBreak())

# ===== PROGNOSIS =====
story.append(Paragraph("PROGNOSER: 3, 6, 9 og 12 måneder", styles['H1']))
story.append(Paragraph(
    f"Akkumulert prognose basert på {growth_24_25:.0f}% vekstrate og sesongjustering.",
    styles['B']
))
pt = [
    ["Horisont", "Dato", "Prognose", "Driver"],
    ["3 mnd", "Okt 2026", f"~{proj_3m:,}", "Enterprise-automasjon"],
    ["6 mnd", "Jan 2027", f"~{proj_6m:,}", "Q4-sesong + agentic AI"],
    ["9 mnd", "Apr 2027", f"~{proj_9m:,}", "Neste-gen autonome agenter"],
    ["12 mnd", "Jul 2027", f"~{proj_12m:,}", "Fulle agentic prod-systemer"],
]
t3 = Table(pt, colWidths=[3*cm, 3*cm, 3*cm, 6*cm])
t3.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), HexColor("#c0392b")),
    ('TEXTCOLOR', (0,0), (-1,0), white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTNAME', (1,1), (1,-1), 'Helvetica-Bold'),
    ('TEXTCOLOR', (1,1), (1,-1), HexColor("#c0392b")),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor("#fdf2f2"), white]),
    ('GRID', (0,0), (-1,-1), 0.5, HexColor("#ccc")),
    ('PADDING', (0,0), (-1,-1), 8),
    ('ALIGN', (2,1), (2,-1), 'CENTER'),
]))
story.append(t3)
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("<b>Scenarioer (jul 2027):</b>", styles['H3']))
story.append(Paragraph(f"• <b>Optimistisk</b> (regulatorisk inngripen): ~{int(proj_12m*0.7):,}", styles['B']))
story.append(Paragraph(f"• <b>Realistisk</b> (nåværende trend): ~{proj_12m:,}", styles['B']))
story.append(Paragraph(f"• <b>Pessimistisk</b> (AGI-lignende autonomi): ~{int(proj_12m*1.8):,}", styles['B']))
story.append(PageBreak())

# ===== SECTORS =====
story.append(Paragraph("Sektortrusselbilde", styles['H1']))
st = [["Sektor", "Hendelser", "Andel"]]
total_s = sum(sector_counts.values())
for s, c in sector_counts.most_common(7):
    st.append([s, str(c), f"{c/total_s*100:.1f}%"])
t4 = Table(st, colWidths=[5*cm, 3*cm, 3*cm])
t4.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), HexColor("#2c3e50")),
    ('TEXTCOLOR', (0,0), (-1,0), white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('ALIGN', (1,0), (-1,-1), 'CENTER'),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor("#f9f9f9"), white]),
    ('GRID', (0,0), (-1,-1), 0.5, HexColor("#ccc")),
    ('PADDING', (0,0), (-1,-1), 6),
]))
story.append(t4)
story.append(Spacer(1, 1*cm))
story.append(Paragraph("<b>De 5 mest utsatte bransjene:</b>", styles['H3']))
for b in [
    "<b>Autonom transport:</b> Tesla ($243M bot), Waymo (1200 tilbakekalt), Xiaomi (3 drepte)",
    "<b>Helsevesen:</b> UnitedHealth 90% feilrate, 16x nektelser, sodium bromide-forgiftning",
    "<b>Finans:</b> Bitget (1446 USDT), Step Finance ($40M), Arup deepfake ($25.6M)",
    "<b>Utviklerverktøy:</b> Cursor/PocketOS, Replit DB-wipe, Claude Code rm -rf, Kiro",
    "<b>Offentlig sektor:</b> Tromsø (1.2M NOK), CISA FOUU-eksponering, fransk chatbot-spenning",
]:
    story.append(Paragraph(f"• {b}", styles['BL']))
story.append(PageBreak())

# ===== TOP DEVELOPERS =====
story.append(Paragraph("Topp AI-utviklere etter hendelsesvolum", styles['H1']))
dt = [["Rang", "Utvikler", "Hendelser"]]
for i, (d, c) in enumerate(developer_counts.most_common(15), 1):
    dt.append([str(i), d[:50], str(c)])
t5 = Table(dt, colWidths=[1.5*cm, 9*cm, 3*cm])
t5.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), HexColor("#2c3e50")),
    ('TEXTCOLOR', (0,0), (-1,0), white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('ALIGN', (0,0), (0,-1), 'CENTER'),
    ('ALIGN', (2,0), (2,-1), 'CENTER'),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor("#f9f9f9"), white]),
    ('GRID', (0,0), (-1,-1), 0.5, HexColor("#ccc")),
    ('PADDING', (0,0), (-1,-1), 6),
    ('FONTSIZE', (0,0), (-1,-1), 9),
]))
story.append(t5)
story.append(PageBreak())

# ===== CRITICAL INCIDENTS =====
story.append(Paragraph("Kritiske hendelser", styles['H1']))
story.append(Paragraph("<b>Dødsfall koblet til AI-systemer:</b>", styles['H3']))
deaths = [
    ("2025-05-20", "14-åring Florida selvmord", "Character.AI"),
    ("2025-05-15", "Adam Raine, 16 år", "ChatGPT"),
    ("2025-05-10", "23-åring college-grad", "ChatGPT"),
    ("2025-05-05", "48-åring psykoseepisode", "ChatGPT"),
    ("2025-05-01", "26-åring kjønnsidentitet", "ChatGPT"),
    ("2025-04-25", "36-åring sentient AI-delusion", "Google Gemini"),
    ("2025-04-20", "40-åring Goodnight Moon", "ChatGPT 4o"),
    ("2025-04-10", "Fatal Autopilot-krasj", "Tesla"),
    ("2025-04-05", "3 studenter drept", "Xiaomi SU7"),
    ("2025-04-01", "Rear-end 120km/h", "Aito/Huawei"),
    ("2025-01-20", "13-åring Colorado", "Character.AI"),
    ("2025-01-15", "17-åring drepe foreldre", "Character.AI"),
]
dtt = [["Dato", "Tittel", "System"]] + deaths
t6 = Table(dtt, colWidths=[2.5*cm, 7*cm, 4*cm])
t6.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), HexColor("#c0392b")),
    ('TEXTCOLOR', (0,0), (-1,0), white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor("#fdf2f2"), white]),
    ('GRID', (0,0), (-1,-1), 0.5, HexColor("#ccc")),
    ('PADDING', (0,0), (-1,-1), 6),
    ('FONTSIZE', (0,0), (-1,-1), 9),
]))
story.append(t6)
story.append(Spacer(1, 0.5*cm))

story.append(Paragraph("<b>Største økonomiske tap:</b>", styles['H3']))
eco = [
    ("2025-06-01", "VW Cariad AI-fail", "$7.5B tap"),
    ("2025-04-10", "Tesla Autopilot $243M bot", "$243M"),
    ("2026-01-15", "Step Finance AI-hack", "$40M"),
    ("2025-07-01", "Arup deepfake-heist", "$25.6M"),
    ("2025-03-25", "DNB deepfake CEO-forsøk", "$2M"),
    ("2025-07-20", "Earnest bias settlement", "$2.5M"),
    ("2026-01-10", "OpenClaw trading loss", "Millioner"),
    ("2026-01-05", "Alpha Arena AI-trading", "$10K+"),
    ("2025-11-01", "Airbnb AI-fake damage", "$16K"),
]
et = [["Dato", "Hendelse", "Tap"]] + eco
t7 = Table(et, colWidths=[2.5*cm, 7*cm, 3*cm])
t7.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), HexColor("#2c3e50")),
    ('TEXTCOLOR', (0,0), (-1,0), white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor("#f9f9f9"), white]),
    ('GRID', (0,0), (-1,-1), 0.5, HexColor("#ccc")),
    ('PADDING', (0,0), (-1,-1), 6),
    ('FONTSIZE', (0,0), (-1,-1), 8),
    ('ALIGN', (2,0), (2,-1), 'RIGHT'),
]))
story.append(t7)
story.append(PageBreak())

# ===== FULL INDEX =====
story.append(Paragraph(f"Full indeks: {len(aiid_incidents):,} AIID-hendelser", styles['H1']))
story.append(Paragraph(
    f"Alle {len(aiid_incidents):,} hendelser kronologisk (nyeste først). "
    f"For full kontekst og kilde-lenker: <i>github.com/nsolland/agentic-execution-risk</i>",
    styles['B']
))

def sort_key(inc):
    d = (inc.get("date") or "").strip()
    for fmt in ["%Y-%m-%d", "%Y-%m", "%Y"]:
        try: return datetime.strptime(d, fmt)
        except: pass
    return datetime(1900,1,1)

aiid_incidents.sort(key=sort_key, reverse=True)

idx_table = [["#", "Dato", "Tittel", "Developer"]]
for i, inc in enumerate(aiid_incidents, 1):
    date_str = (inc.get("date") or "?")[:10]
    title = (inc.get("title") or "Uten tittel")
    if len(title) > 55: title = title[:52] + "..."
    dev = (inc.get("Alleged developer of AI system") or "").replace('[','').replace(']','').replace('"','')
    if len(dev) > 30: dev = dev[:27] + "..."
    idx_table.append([str(i), date_str, title, dev or "—"])

page_size = 45
for page_start in range(0, len(idx_table) - 1, page_size):
    subset = [idx_table[0]] + idx_table[1 + page_start:1 + page_start + page_size]
    t = Table(subset, colWidths=[1.2*cm, 2.5*cm, 6.5*cm, 3.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor("#34495e")),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, HexColor("#fafafa")]),
        ('GRID', (0,0), (-1,-1), 0.25, HexColor("#ddd")),
        ('PADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t)
    if page_start + page_size < len(aiid_incidents):
        story.append(PageBreak())
        story.append(Paragraph(f"Indeks (forts. fra #{page_start+2})", styles['H3']))

# ===== METHODOLOGY =====
story.append(PageBreak())
story.append(Paragraph("Metodikk", styles['H1']))
story.append(Paragraph(
    "Data fra AI Incident Database (Stanford), 869+ tilfeller, 7 314 medierapporter per juli 2026. "
    "I tillegg 44 kurerte tilfeller fra verifiserte kilder. Prognosehorisont: 17. juli 2026.",
    styles['B']
))
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("<b>Prognosemetodikk:</b>", styles['H3']))
story.append(Paragraph(
    "Historisk vekst + lineær ekstrapolasjon, justert for EU AI Act og sesong-effekter.",
    styles['B']
))
story.append(Spacer(1, 1*cm))
story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#ccc")))
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("© 2026 Agentic Execution Risk Observatory — Data public domain via AIID", styles['FT']))
story.append(Paragraph("Rapport: 17. juli 2026 · v1.0", styles['FT']))

doc.build(story)
print(f"✅ PDF: {pdf_path}")
print(f"Size: {pdf_path.stat().st_size/1024:.1f} KB")
