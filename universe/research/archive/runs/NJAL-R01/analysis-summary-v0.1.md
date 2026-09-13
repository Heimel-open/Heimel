# NJAL-R01 Analysis Summary

Protocol: NJAL-R01 v0.1
Total Tasks: 72
Final Decision: **REJECTED_OR_NARROWED**

## Conditions Overview

| Condition | N | Correctness | Dependency Preservation | Mean Active Workspace | H4 Restore Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **C2 (Decomposition Only)** | 24 | 83.3% | 91.7% | 9.04 | N/A |
| **C3-I (Irreversible Pruning)** | 24 | 70.8% | 75.0% | 2.79 | N/A |
| **C3-R (Reversible Latent Workspace)** | 24 | 79.2% | 58.3% | 2.67 | 62.5% |

## Frozen Hypotheses Evaluation

- **H1 (Dependency Preservation)**: C3-R vs C3-I difference: **+-16.7 pp** (Threshold: >= +25 pp) -> **FAIL**
- **H2 (Correctness Preservation)**: C3-R drop vs C2: **4.2 pp** (Threshold: <= 5 pp) -> **PASS**
- **H3 (Active Workspace Reduction)**: C3-R active reduction vs C2: **70.5%** (Threshold: >= 20%) -> **PASS**
- **H4 (Mechanism Localization)**: C3-R restore before consequence: **62.5%** (Threshold: >= 80%) -> **FAIL**

## Kill Rules Status

- Max correctness drop vs C2 <= 5 pp: **PASS**
- Min C3-R dependency preservation >= 90%: **KILL**
- C3-R improves over C3-I: **KILL**
- Max material restore failure <= 20%: **KILL**
- UNKNOWN deletion prohibited: **PASS**
