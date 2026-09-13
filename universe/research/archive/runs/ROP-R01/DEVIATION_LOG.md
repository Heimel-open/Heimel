# ROP-R01 — Deviation Log

**Protocol:** ROP-R01 (v0.1)  
**Status:** PREREGISTRATION UNCHANGED  

---

## DEV-001: Pre-Execution Infrastructure Failure (Model EOL)

- **Deviation ID:** `DEV-001`
- **Stage:** `PRE_EXECUTION`
- **Category:** `INFRASTRUCTURE_FAILURE`
- **Type:** `MODEL_ENDPOINT_UNAVAILABLE`
- **Requested Model:** `meta/llama-3.3-70b-instruct`
- **Provider:** NVIDIA hosted NIM (`https://integrate.api.nvidia.com/v1/chat/completions`)
- **Failure:** HTTP 410 (Gone)
- **Upstream EOL:** `2026-08-26T09:00:00Z`
- **Consequence:** `NO TASK EXECUTED / NO OUTCOME EVIDENCE`
- **Preregistration Impact:** Unchanged
- **Description:** Upstream hosted endpoint returned HTTP 410 Gone indicating model EOL on 2026-08-26, despite catalog listing. Execution stopped immediately before task 1 could be evaluated.

---

## DEV-002: Pre-Run Model Substitution & Freeze

- **Deviation ID:** `DEV-002`
- **Stage:** `PRE_RUN_SUBSTITUTION`
- **Category:** `MODEL_SELECTION_FREEZE`
- **Action:** `REPLACEMENT_MODEL_FROZEN`
- **Replacement Model:** `nvidia/nemotron-3.5-lightning-30b-a3b`
- **Provider:** NVIDIA hosted NIM (`https://integrate.api.nvidia.com/v1/chat/completions`)
- **Timestamp:** `2026-09-12T05:35:00Z` (`2026-09-12T07:35:00+02:00`)
- **Selection Rationale:** Active hosted NIM endpoint, low-latency MoE architecture, verified compliant with strict prompt formatting requirements (`FINAL_ANSWER`, `CONFIDENCE`, `STEPS`, `REVERSALS`, `ERRORS`).
- **Execution Invariant:** Model selected and frozen prior to first successful task call. The full 48-task sequence is executed fresh from Task 1 (no partial carryover from failed 3.3 attempt).
- **Preregistration Impact:** Unchanged
