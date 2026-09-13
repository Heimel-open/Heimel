# AGENTS.md — valo-research-collaborations

## What this is

A private research institution in repo form: an independent-research
collaboration space shared by Margaret Stokes, Elsa and Njål Solland.
Separate IP owners meet here **without** their work automatically becoming
common IP.

This is **not** a VALO product repo. It does not hold runtime, and it does
not give anyone authority or admissibility inside VALO/REHT.

## Non-negotiable rules

- **Felles repo ≠ felles IP.** Every document carries explicit ownership,
  author, status and permitted use. Nothing in `common/` or `intersections/`
  re-owns another person's original work.
- **Originalt arbeid tilhører opphavspersonen.** Each person's track
  (`margaret-stokes/`, `elsa/`, `njal-solland/`) is their own. Do not edit
  another person's track without a visible diff and their approval.
- **No shared accounts.** Each researcher works through their own GitHub
  identity; signed commits where practical.
- **No rewrite without approval.** Changing another's work requires a PR
  with explicit diff and consent.
- **Felles syntese går via PR.** Shared synthesis is proposed as a PR
  (`shared/*`), approved by everyone whose work it describes, never pushed
  directly to `main`.
- **Git history is evidence, not the only legal proof.** Attribution is
  recorded per document (author/owner header), not inferred only from commits.
- **Nothing here creates VALO authority.** Ideas and synthesis are research
  input; REHT/VALO authority is decided in the canonical VALO repos.

## Layout

```
common/                 # shared questions, terminology, principles, synthesis, decision log
margaret-stokes/        # Margaret: standing, answerability, evidence admission, communication admissibility
elsa/                   # Elsa: authority instrumentation, mandate, temporal authority, revocation, human authority
njal-solland/           # Njål: tofoo, j-space, framleis, operational fixed points, execution governance
intersections/          # boundary surfaces between the three bodies of work
adr/                    # architecture decision records for shared conclusions
docs/                   # collaboration procedures + templates
```

## Conventions

- Every document uses the template in `docs/document-template.md` (Title,
  Author, Original IP owner, Contributors, Status, Based on, Changes,
  Permitted use, Related synthesis).
- Status values: `hypothesis` / `draft` / `reviewed` / `accepted`.
- Shared conclusions go in `adr/` with named approvers.
- Branch prefixes: `margaret/*`, `elsa/*`, `njal/*`, `shared/*`.
- No AI agent may commit to another person's track or to `main` directly.

## Commands

```bash
git clone git@github.com:nsolland/valo-research-collaborations.git
git checkout -b shared/<topic> && # work -> PR
```
