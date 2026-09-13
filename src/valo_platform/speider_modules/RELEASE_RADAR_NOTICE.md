# Release Radar provenance

This VALO implementation is an Apache-2.0 adaptation of selected patterns from:

- upstream: `Shubhamsaboo/awesome-llm-apps`
- reviewed fork: `nsolland/awesome-llm-apps`
- source SHA: `804dee009f71503cd0bbb6d7338f2978790666ea`
- source paths:
  - `always_on_agents/release_radar_agent/radar.py`
  - `always_on_agents/release_radar_agent/ranker.py`
  - `always_on_agents/release_radar_agent/tests/unit/test_ranker.py`

The upstream Apache-2.0 license and notices remain applicable to adapted portions.
No upstream endorsement of VALO is implied.

## Material adaptations

VALO retained the useful patterns:

- explicit dependency manifest;
- semantic version delta classification;
- security, breaking, yanked, major-version and deprecation signals;
- deterministic ranking and routine-noise filtering;
- focused deterministic fixtures and tests.

VALO changed the implementation materially:

- removed GitHub/network acquisition, concurrency, scheduler and delivery paths;
- removed hard-coded repository mappings;
- added strict repository-owned manifest validation and duplicate rejection;
- added dependency, model and provider subjects;
- added exposure and consequence weighting beneath invariant signal tiers;
- added explicit ignored, unknown and observation-only states;
- added canonical SHA-256 evidence, finding, manifest and report digests;
- emits existing Speider `Signal` records only when explicitly called;
- forbids automatic upgrade, lockfile mutation, PR creation and remediation;
- makes all authority, clearance, execution and remediation flags false.

Speider observes release evidence. Any consequence-bearing response remains outside
this module and must follow the canonical VAIG → REHT → RACS chain.
