#!/usr/bin/env python3
"""Render an agent.valo.id HTML profile from canonical YAML.

Prototype renderer. The YAML file is the source of truth; HTML is a view.
Requires PyYAML.
"""

from pathlib import Path
import html
import sys

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc


def fmt_number(value):
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def render(profile):
    agent = profile["agent"]
    owner = profile["owner"]
    verification = profile["verification"]
    dna = profile["agent_dna"]
    revenue = profile["revenue"]
    reputation = profile["reputation"]
    risk = profile["risk"]
    receipts = profile["receipts"]["public_recent"]

    receipt_html = "\n".join(
        f'<div class="receipt"><div><strong>{html.escape(r["receipt_id"])}</strong><br>'
        f'<span class="small">{html.escape(r.get("action_type", "receipt"))} · {html.escape(r.get("scope", ""))} · {html.escape(str(r.get("value_signal", "")))}</span></div>'
        f'<div class="decision {"allow" if r["decision"] == "ALLOW" else "step"}">{html.escape(r["decision"])}</div></div>'
        for r in receipts
    )

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(agent["display_name"])} · agent.valo.id</title>
  <link rel="alternate" type="application/x-yaml" href="{html.escape(profile["canonical_file"])}" title="Canonical agent.valo.id profile data" />
</head>
<body>
<main>
  <h1>{html.escape(agent["display_name"])}</h1>
  <p>{html.escape(agent.get("description", ""))}</p>
  <p>Owner: {html.escape(owner["public_owner_label"])} | {html.escape(verification["label"])} | Authority: {html.escape(dna["authority_level"])}</p>
  <p>Revenue 30d: {fmt_number(revenue["verified_amount"])} {html.escape(revenue["currency"])} | REP: {reputation["rep_score"]} | BARO risk: {risk["risk_surface_score"]} | Agent score: {fmt_number(dna["agent_score"])}</p>
  <h2>Recent receipts</h2>
  {receipt_html}
  <p>YAML is canonical: {html.escape(profile["canonical_file"])}. This page is only the rendered public profile.</p>
</main>
</body>
</html>
'''


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: render_agent_profile.py INPUT.yaml OUTPUT.html")
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    profile = yaml.safe_load(input_path.read_text())
    output_path.write_text(render(profile))


if __name__ == "__main__":
    main()
