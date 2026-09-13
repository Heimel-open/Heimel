# NJAL-R01 — Deviation Log

**Protocol:** NJAL-R01 (v0.1)  
**Status:** PREREGISTRATION UNCHANGED  

---

## DEV-001: Pre-Execution Infrastructure Failure (Hosted Model Degraded)

- **Deviation ID:** `DEV-001`
- **Stage:** `PRE_EXECUTION`
- **Category:** `INFRASTRUCTURE_FAILURE`
- **Type:** `MODEL_ENDPOINT_DEGRADED`
- **Requested Model:** `nvidia/nemotron-3.5-lightning-30b-a3b`
- **Provider:** NVIDIA hosted NIM (`https://integrate.api.nvidia.com/v1/chat/completions`)
- **Failure:** HTTP 400 (Bad Request: `Function id '0a213807-640b-43fb-bfbf-2919f9b666ad': DEGRADED function cannot be invoked`)
- **Consequence:** `NO TASK EXECUTED / NO OUTCOME EVIDENCE`
- **Preregistration Impact:** Unchanged
- **Description:** Upon launching the sharp execution of NJAL-R01, the upstream hosted NVIDIA NIM endpoint aborted on Task 1 (`D06-A`) with HTTP 400 indicating the function is marked as DEGRADED on NVIDIA's hosted cluster. Execution stopped immediately before Task 1 could complete. Zero partial outcome evidence was generated.

---

## DEV-002: Pre-Execution Model Substitution & Calibration Freeze

> **DEV-002: Pre-execution model substitution due provider model unavailability/degradation. No NJAL-R01 outcome task has been executed under the superseded model configuration.**

- **Deviation ID:** `DEV-002`
- **Stage:** `PRE_RUN_SUBSTITUTION`
- **Category:** `MODEL_SELECTION_FREEZE`
- **Action:** `REPLACEMENT_MODEL_FROZEN`
- **Replacement Model:** `meta/llama-3.2-11b-vision-instruct`
- **Provider:** NVIDIA hosted NIM (`https://integrate.api.nvidia.com/v1/chat/completions`)
- **Frozen Timestamp:** `2026-09-12T11:22:00Z` (`2026-09-12T13:22:00+02:00`)
- **Inference Configuration:**
  - `temperature`: `0.0`
  - `max_tokens`: `4096`
  - `timeout_seconds`: `120`
  - `max_retries`: `5` (exponential backoff on transient 429/5xx)
- **Prompt Scaffolding & Harness Hashes:**
  - `system_prompt_sha256`: `2d4829bd1583871a7108b2954de996ef35209476ecdc4ee6a8fd8c3e1438db11`
  - `harness_c2_sha256`: `2b010cde665d2972e2c6dd8aae26e0c11ddebb542ba379b33c84b1aca6a02ec8`
  - `harness_c3i_sha256`: `832323ef8b161139a506c2ad6287ad703a3873c0ab95320f08a77a72360b947e`
  - `harness_c3r_sha256`: `6b16e99e441158574baf583728a9752e4cfe2aaf8308bff2aa9102cdb5e3dc59`
- **Pre-Arming Health & Smoke Verification:**
  - **Text-Only Health Probe:** `Calculate 15 * 4 - 12` -> returned `48` in `0.53s` (**PASS**).
  - **SMOKE-C2 (Non-benchmark task):** `46.0` exact match, 9.85s, active workspace size = 8 (**PASS**).
  - **SMOKE-C3I (Non-benchmark task):** `38.0` exact match, 18.13s, active workspace size = 3 (**PASS**).
  - **SMOKE-C3R (Non-benchmark task):** `80.0` exact match, 29.90s, active workspace size = 3, restore targets `['C1', 'C3', 'C6']` (**PASS**).
- **Execution Invariant:**
  - All 72 tasks must run from Task 1 on this frozen replacement model.
  - Zero model blending within NJAL-R01. If carrier becomes unavailable during execution: stop, log deviation, and restart the entire sharp run from Task 1.
- **Preregistration Impact:** Unchanged.
