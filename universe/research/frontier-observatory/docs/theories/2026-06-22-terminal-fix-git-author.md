# Terminal-fix: git author-problem på lokal main

Dato: 2026-06-22

## Problem

Fire commit på lokal main har feil forfattar "N" i staden for "Claude":
- 5d4f10d — Percy Deift dialog
- 3e9a64c — elektron-bolgje og nature-simply-is
- 004ea77 — README oppdatert
- 4736e86 — bevisstheit som felt

Filene er trygge — allereie pusha til remote dev-branch (claude/phi-law-validation-jpggg2) via GitHub API.

## Fix — køyr dette ved terminal

```bash
git config user.name "Claude"
git config user.email "noreply@anthropic.com"
git rebase --exec "git commit --amend --no-edit --reset-author" origin/main
git push -u origin claude/phi-law-validation-jpggg2
```

Alternativt, sidan filene allereie er på dev-branch:

```bash
git reset --hard origin/main
```

Dette fjernar dei fire lokale commit-ane frå main utan å miste noko arbeid.

## Status

Stop hook vil flagge dette kvar gong til fix er køyrt.
Alt innhald er trygt på remote.
