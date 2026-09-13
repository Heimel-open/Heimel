# PROJECT_CONTEXT

Repo: nsolland/Valo-Twin

Project: VALO Twin

Purpose:
VALO Twin is a monitor/demo/UI application for visualizing VALO-related signals, states and workflows.

This repo is a user-facing application layer.

It may later display signals from BARO, VAIG or other VALO services, but it should not become those systems.

What this repo is:

- demo and monitor UI
- React / TypeScript / Vite application
- visual workspace for VALO state, signals and workflows
- place for UI components, sample data and operator views

What this repo is not:

- not BARO scoring
- not BARO public-data pipeline
- not VAIG execution-boundary engine
- not VAP protocol implementation
- not MECHA theory repository
- not a place for broad governance essays unless directly needed by the UI

Boundary rules:

- Keep BARO logic in nsolland/Baro unless explicitly copied as sample data.
- Keep VAIG execution-governance logic out of this repo unless explicitly building UI views for it.
- Keep VAP protocol work out of this repo unless explicitly building a visual protocol monitor.
- Do not rename or merge VALO, BARO, VAIG, VAP or Valo-Twin.

Current repo role:
Valo-Twin is the visual/monitor layer.

Default assumption:
When uncertain, treat work in this repo as UI, demo data, monitor state, or documentation for the app.
