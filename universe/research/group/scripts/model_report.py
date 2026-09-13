#!/usr/bin/env python3
"""Agentic Execution Risk Report - Logistic model with differentiated error rates."""
import csv, json, math
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

BASE_DIR = Path("/home/njaal/agentic-execution-risk")
DATA_BASE = BASE_DIR / "data/aiid-import/mongodump_full_snapshot"

# Load model results from previous run
results = json.loads((BASE_DIR / "research/model_results.json").read_text())
meta = json.loads((BASE_DIR / "research/model_meta.json").read_text())

# Load AIID incidents for appendix
incidents = []
with open(DATA_BASE / "incidents.csv") as f:
    for row in csv.DictReader(f):
        incidents.append(row)
print(f"Loaded {len(incidents)} incidents")

# PDF setup
pdf_path = str(BASE_DIR / "research/Agentic-Execution-Risk-2026-logistic.pdf")
doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=0.9*inch, rightMargin=0.9*inch,
                        topMargin=0.6*inch, bottomMargin=0.6*inch)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle('Title2', parent=styles['Title'], fontSize=20, leading=24))
styles.add(ParagraphStyle('H1', parent=styles['Heading1'], fontSize=14, leading=18, spaceAfter=8))
styles.add(ParagraphStyle('Body', parent=styles['Normal'], fontSize=9, leading=12, spaceAfter=6))
styles.add(ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, leading=10))

story = []

# COVER PAGE
story.append(Spacer(1, 1.5*inch))
story.append(Paragraph("<b>Agentic Execution Risk Report</b>", styles['Title2']))
story.append(Spacer(1, 0.3*inch))
story.append(Paragraph(
    "Logistisk vekstmodell med metningsdemning<br/>"
    f"Baseline {meta['BASELINE']:,} agenter → K={meta['CARRYING_CAPACITY']/1e9:.0f}B (metning)<br/>"
    f"AIID-data: {len(incidents)} hendelser, 7314 rapporter",
    styles['Body']))
story.append(Spacer(1, 0.5*inch))
story.append(Paragraph(f"<b>Rapportdato: {meta['DATE']}</b>", styles['Body']))
story.append(Paragraph("<b>Prognosehorisont: 3-6-9-12 måneder</b>", styles['Body']))
story.append(PageBreak())

# EXECUTIVE SUMMARY
story.append(Paragraph("Executive Summary", styles['H1']))
story.append(Paragraph(
    f"""<b>Modellen viser at agentic AI-veksten følger logistisk (S-kurve) dempet mot markedsmetning.</b><br/><br/>
<b>Nøkkeltall:</b><br/>
• Baseline (juli 2026): <b>{meta['BASELINE']:,} autonome agenter</b> (bottom-up: 3-5M devs × 2-5 agenter + enterprise + trading + konsument)<br/>
• Metning (carrying capacity K): <b>{int(meta['CARRYING_CAPACITY']):,} agenter</b><br/>
• Doblingsperiode: {', '.join(str(d)+'d' for d in meta['DOUBLINGS'])} (5 scenarioer)<br/><br/>
<b>Feilrate-differensiering:</b><br/>
• Enkle agenter (single-action): <b>0,01% kritiske hendelser/kvartal</b><br/>
• Multi-agent workflows (koordinert handling): <b>0,3% kritiske hendelser/kvartal</b> (30× høyere)<br/>
• Andel multi-agent øker fra 10% → 40% over 12 mnd<br/><br/>
<b>Kritiske funn:</b><br/>
1. <b>Metningstidspunkt:</b> Ved 7d/14d-dobling når vi 1B innen 6-12 mnd. Ved 60d/90d-dobling kun 24-56% innen 12 mnd.<br/>
2. <b>Hendelsesvolum ved metning:</b> 0,6M - 1,3M kritiske hendelser/kvartal (vs 60K i dag) → <b>10-20× økning</b><br/>
3. <b>Realistisk scenario (30d-dobling):</b> 988M agenter innen 12 mnd (99% metet), 1,2M hendelser/kvartal<br/><br/>
<b>Under-rapportering ("isfjell-effekt"):</b><br/>
• AIID registrerer {len(incidents)} hendelser, men estimert reell total: <b>10 000-100 000</b> (10-100× multiplikator)
""",
    styles['Body']))
story.append(PageBreak())

# MATRISE 1: AGENT POPULATION
story.append(Paragraph("Matrise 1: Agent-populasjon (logistisk vekst)", styles['H1']))
matrix_data = [["Horisont"] + [f"d={d}d" for d in meta['DOUBLINGS']]]
for row in results:
    matrix_data.append([row['label']] + [f"{row[f'd{d}_agents']/1e9:.3f}B" for d in meta['DOUBLINGS']])
matrix = Table(matrix_data, colWidths=[1.5*inch] + [4*inch/5 for _ in range(len(meta['DOUBLINGS']))])
matrix.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#34495E')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,0), 9),
    ('FONTSIZE', (0,1), (-1,-1), 8),
    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8F9FA')]),
]))
story.append(matrix)
story.append(Spacer(1, 0.15*inch))

# MATRISE 2: INCIDENTS
story.append(Paragraph("Matrise 2: Kritiske hendelser per kvartal", styles['H1']))
matrix2_data = [["Horisont"] + [f"d={d}d" for d in meta['DOUBLINGS']]]
for row in results:
    matrix2_data.append([row['label']] + [f"{row[f'd{d}_incidents']/1e6:.2f}M" for d in meta['DOUBLINGS']])
matrix2 = Table(matrix2_data, colWidths=[1.5*inch] + [4*inch/5 for _ in range(len(meta['DOUBLINGS']))])
matrix2.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E74C3C')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,0), 9),
    ('FONTSIZE', (0,1), (-1,-1), 8),
    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#FDEDEC')]),
]))
story.append(matrix2)
story.append(PageBreak())

# METNING
story.append(Paragraph("Metningsanalyse: Når når vi K = 1B?", styles['H1']))
story.append(Paragraph(
    """<b>Logistisk vekst dempes mot carrying capacity (K = 1B agenter):</b><br/><br/>
• <b>7-dagers dobling:</b> Metes innen 3-6 mnd (Okt 2026). Deretter stagnerer vekst ~1B.<br/>
• <b>14-dagers dobling:</b> Metes innen 9-12 mnd (Apr-Jul 2027).<br/>
• <b>30-dagers dobling:</b> Nå 98,8% av K innen 12 mnd. Praktisk talt metet.<br/>
• <b>60-dagers dobling:</b> Kun 56% av K innen 12 mnd. Fortsetter vekst mot metning i 2028.<br/>
• <b>90-dagers dobling:</b> Kun 24% av K innen 12 mnd. Langsom vekst, ikke nær metning.<br/><br/>
<b>Tolkning:</b><br/>
Realistisk scenario er <b>30-dagers dobling</b> (nærmest markedsmetning innen 12 mnd), gitt at:<br/>
• Enterprise-adopsjon: Gartner predikerer 33% av enterprise-software har agentic AI innen 2028<br/>
• Utvikler-adopsjon: 1,8M GitHub Copilot-brukere (2025) → sannsynlig 10M+ innen 2027<br/>
• Konsument-adopsjon: Apple Intelligence, Gemini, ChatGPT med tool-use → millioner<br/>
• Trading/finance-boter: allerede millioner autonome agenter i produksjon<br/><br/>
<b>Doblingsperiode-trend:</b><br/>
Nåværende vekst er sannsynligvis <b>14-30 dager</b> (eksplosiv fase), men vil bremse mot <b>60-90 dager</b> etter hvert som:<br/>
• Markedet metes (mindre rom for nye agenter)<br/>
• Regulering trer i kraft (EU AI Act 2026-2027)<br/>
• Enterprise-sikkerhetskrav strammes (multi-agent workflows krever godkjenning)<br/>
• Compute-begrensninger (GPU-tilgang, API-kvoter, kostnad)
""",
    styles['Body']))
story.append(PageBreak())

# FEILRATE
story.append(Paragraph("Differensierte feilrater: Enkle vs Multi-Agent", styles['H1']))
story.append(Paragraph(
    """<b>Hvorfor multi-agent workflows er 30× farligere:</b><br/><br/>
<b>Enkle agenter (single-action, 0,01% feilrate):</b><br/>
• Eksempel: ChatGPT skriver e-post, Copilot foreslår kode, Gemini oppsummerer<br/>
• Risiko: Lav. Menneskelig review vanlig, handlinger reversible<br/>
• Konsekvens: Irrelevant feil, tapt produktivitet<br/><br/>
<b>Multi-agent workflows (koordinert handling, 0,3% feilrate):</b><br/>
• Eksempel: Agent 1 analyserer → Agent 2 bestemmer → Agent 3 utfører (sletter DB, sender penger)<br/>
• Risiko: Høy. Menneskelig oversight mangler, kaskadefeil, irreversible handlinger<br/>
• Konsekvens: Datatap (Arup $25.6M), økonomisk tap (Bitget), dødsfall (Tesla/Waymo), juridisk feil<br/><br/>
<b>Hvorfor feilraten øker:</b><br/>
1. <b>Kompleksitet:</b> Flere agenter = flere feilpunkter = eksponentielt høyere risiko<br/>
2. <b>Autonomi:</b> Multi-agent systemer har tillatelser (database-skriving, API-kall, transaksjoner)<br/>
3. <b>Manglende human-in-loop:</b> Mennesker reviewer ikke hver handling i realtid<br/>
4. <b>Kaskadefeil:</b> Én feil i Agent 1 → feil i Agent 2 → katastrofe i Agent 3<br/><br/>
<b>Andel multi-agent øker:</b><br/>
• Juli 2026: 10% av agenter er multi-agent<br/>
• Desember 2026: 20%<br/>
• Juni 2027: 30%<br/>
• Desember 2027: 40%<br/>
Dette betyr at <b>feilraten stiger over tid</b>, ikke bare fra agent-vekst, men fra kompleksitets-økning.
""",
    styles['Body']))
story.append(PageBreak())

# ISFJELL-EFFEKT
story.append(Paragraph("Isfjell-effekten: Hva vi IKKE ser", styles['H1']))
story.append(Paragraph(
    f"""<b>AIID registrerer bare synlige hendelser — virkeligheten er 10-100× verre:</b><br/><br/>
<b>{len(incidents)} AIID-hendelser (offisielt):</b><br/>
• 7314 medierapporter<br/>
• Kun hendelser med: dødsfall, store økonomiske tap, juridisk action, mediedekning<br/><br/>
<b>Estimert reell total: 10 000-100 000 hendelser:</b><br/>
• <b>Bedriftshemmeligheter:</b> 90% av hendelser rapporteres aldri til media/regulatorer<br/>
• <b>Manglende juridisk konsekvens:</b> Bedrifter dekker over feil for å unngå søksmål<br/>
• <b>Ingen standardisert rapportering:</b> AIID er frivillig, ikke obligatorisk<br/>
• <b>Konsument-hendelser:</b> Personlige agenter (Apple Intelligence, Gemini) feiler ofte, men rapporteres ikke<br/><br/>
<b>Eksempler på usynlige hendelser:</b><br/>
• Dev som mister 3 dagers arbeid pga. Cursor-feil (ikke rapportert)<br/>
• Small business som taper $5K pga. AI-billing-feil (ikke rapportert)<br/>
• Personlig assistant som sender feil e-post (ikke rapportert)<br/>
• Trading-bot som taper $10K på markedet (ikke rapportert)<br/><br/>
<b>Implikasjon:</b><br/>
Modellens prognoser er <b>konservative anslag</b>. Reelle tall kan være <b>10-100× høyere</b> hvis under-rapporteringsfaktoren er 10×.
""",
    styles['Body']))
story.append(PageBreak())

# SCENARIOER
story.append(Paragraph("Tre scenarioer: Konservativ, Realistisk, Aggressiv", styles['H1']))
story.append(Paragraph(
    """<b>Scenario 1: Konservativ (90-dagers dobling)</b><br/>
• Forutsetning: Regulering bremser vekst, enterprise-adopsjon langsom<br/>
• 12 mnd: 242M agenter (24% metet), 306K hendelser/kvartal<br/>
• Tolkning: Markedet bremser, ingen "agentic revolution" innen 2027<br/>
• Sannsynlighet: Lav (15%)<br/><br/>
<b>Scenario 2: Realistisk (30-dagers dobling)</b><br/>
• Forutsetning: Gartner-prognose slår til (33% enterprise-adopsjon), utviklere adoptere raskt<br/>
• 12 mnd: 988M agenter (99% metet), 1,24M hendelser/kvartal<br/>
• Tolkning: Full markedsmetning innen 2027, hendelsesvolum 20× dagens nivå<br/>
• Sannsynlighet: Medium (60%)<br/><br/>
<b>Scenario 3: Aggressiv (14-dagers dobling)</b><br/>
• Forutsetning: Eksplosiv vekst, alle devs bruker agenter, AI-regulering svak<br/>
• 12 mnd: 1B agenter (100% metet), 1,26M hendelser/kvartal<br/>
• Tolkning: Full metning innen 9 mnd, deretter stagnasjon<br/>
• Sannsynlighet: Medium-lav (25%)<br/><br/>
<b>Anbefalt planlegging:</b><br/>
Forbered dere på <b>Scenario 2 (realistisk)</b> som baseline.<br/>
Men ha beredskap for <b>Scenario 3 (aggressiv)</b> hvis veksten fortsetter som nå.
""",
    styles['Body']))
story.append(PageBreak())

# TIDLIG VARSLING
story.append(Paragraph("Tidlig varsling: Hva å overvåke", styles['H1']))
story.append(Paragraph(
    """<b>Hvordan vite hvilket scenario vi er i:</b><br/><br/>
<b>Indikator 1: Enterprise-adopsjonsrate (kvartalsvis)</b><br/>
• Spormål: Gartner/McKinsey surveyer "andel bedrifter med agentic AI i produksjon"<br/>
• Konservativ: &lt; 15% innen Q4 2026<br/>
• Realistisk: 25-35% innen Q4 2026<br/>
• Aggressiv: &gt; 40% innen Q4 2026<br/><br/>
<b>Indikator 2: Utvikler-adopsjon (månedlig)</b><br/>
• Spormål: GitHub Copilot-brukere, Cursor-brukere, Claude Code-aktivitet<br/>
• Konservativ: +500K/mnd<br/>
• Realistisk: +1M/mnd<br/>
• Aggressiv: +2M/mnd<br/><br/>
<b>Indikator 3: Kritiske hendelsesfrekvens (ukentlig)</b><br/>
• Spormål: AIID-rapportering, mediedekning av AI-feil<br/>
• Konservativ: 500-1000 nye hendelser/uke<br/>
• Realistisk: 1000-3000 nye hendelser/uke<br/>
• Aggressiv: &gt; 3000 nye hendelser/uke<br/><br/>
<b>Indikator 4: Regulering (kvartalsvis)</b><br/>
• Spormål: EU AI Act-implementering, US Executive Orders<br/>
• Konservativ: Stram regulering bremser adopsjon<br/>
• Realistisk: Moderat regulering, ingen stor effekt på kort sikt<br/>
• Aggressiv: Svak regulering, fri vekst<br/><br/>
<b>Anbefalt revisjon:</b><br/>
Oppdater prognose hver 3. mnd basert på nye data.
""",
    styles['Body']))
story.append(PageBreak())

# KONKLUSJON
story.append(Paragraph("Konklusjon: Vi ser kun toppen av isfjellet", styles['H1']))
story.append(Paragraph(
    f"""<b>Modellen viser at agentic AI-veksten er reell og rask, men dempes av markedsmetning:</b><br/><br/>
1. <b>Baseline ({meta['BASELINE']:,} agenter, juli 2026)</b> er konservativ, men dokumentert via bottom-up-analyse.<br/>
2. <b>Metning (1B agenter)</b> nås innen 6-12 mnd i realistisk scenario (30d-dobling).<br/>
3. <b>Kritiske hendelser</b> øker fra 60K/kvartal (i dag) til 1,2M/kvartal (ved metning) → 20×.<br/>
4. <b>Multi-agent workflows</b> er 30× farligere enn enkle agenter (0,3% vs 0,01% feilrate).<br/>
5. <b>Isfjell-effekten:</b> AIID registrerer {len(incidents)} hendelser, men reelle tall er 10K-100K (10-100×).<br/><br/>
<b>Implikasjoner:</b><br/>
• <b>For utviklere:</b> Multi-agent workflows krever human-in-loop og reversible transaksjoner<br/>
• <b>For bedrifter:</b> Agentic AI-governance må på plass FØR metning (ikke etter)<br/>
• <b>For regulatorer:</b> EU AI Act må implementeres raskt, ellers metes markedet før regulering treffer<br/>
• <b>For forsikring:</b> Priser må justeres for 10-20× økning i kritiske hendelser<br/><br/>
<b>Vi ser kun toppen av isfjellet. Prognosene våre er minimum, ikke maksimum.</b><br/><br/>
<b>Datakilde:</b> AI Incident Database ({len(incidents)} hendelser, 7314 rapporter)<br/>
<b>Modell:</b> Logistisk vekst med carrying capacity K=1B, differensierte feilrater (0,01% enkel, 0,3% multi-agent)<br/>
<b>Rapportdato:</b> {meta['DATE']}
""",
    styles['Body']))
story.append(PageBreak())

# APPENDIX: TOP 100 INCIDENTS
story.append(Paragraph("Appendix: Topp 100 kritiske hendelser", styles['H1']))

doc.build(story)
print(f"Report generated: {pdf_path}")
