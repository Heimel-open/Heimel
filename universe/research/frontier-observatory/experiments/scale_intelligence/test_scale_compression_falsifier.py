from scale_compression_falsifier import evaluate


INV = {"frozen": "same"}
SCALES = (1, 2, 4, 8, 16)


def trials(values=None, invariant=INV):
    values = values or {
        1: (0.60, 0.20, 0.30),
        2: (0.66, 0.35, 0.46),
        4: (0.73, 0.50, 0.59),
        8: (0.82, 0.62, 0.71),
        16: (0.76, 0.70, 0.66),
    }
    out = []
    for scale in SCALES:
        d, c, s = values[scale]
        for replicate in range(5):
            out.append(
                {
                    "interaction_scale": scale,
                    "replicate": replicate,
                    "invariants": invariant,
                    "target_decodability": d,
                    "nuisance_compression": c,
                    "sufficient_compression": s,
                }
            )
    return out


def test_survives_when_scale8_has_joint_advantage():
    assert evaluate(trials())["status"] == "NOT_FALSIFIED_BY_DATA"


def test_falsifies_when_scale8_lacks_high_scale_decodability_advantage():
    values = {
        1: (0.60, 0.20, 0.30),
        2: (0.66, 0.35, 0.46),
        4: (0.73, 0.50, 0.59),
        8: (0.82, 0.62, 0.71),
        16: (0.80, 0.70, 0.66),
    }
    assert evaluate(trials(values))["status"] == "FALSIFIED_BY_DATA"


def test_falsifies_when_nuisance_compression_does_not_improve():
    values = {
        1: (0.60, 0.55, 0.30),
        2: (0.66, 0.56, 0.46),
        4: (0.73, 0.58, 0.59),
        8: (0.82, 0.62, 0.71),
        16: (0.76, 0.70, 0.66),
    }
    assert evaluate(trials(values))["status"] == "FALSIFIED_BY_DATA"


def test_invariant_drift_is_insufficient():
    data = trials()
    data[-1]["invariants"] = {"frozen": "drift"}
    assert evaluate(data)["status"] == "INSUFFICIENT_EVIDENCE"


def test_missing_scale_is_insufficient():
    data = [t for t in trials() if t["interaction_scale"] != 16]
    assert evaluate(data)["status"] == "INSUFFICIENT_EVIDENCE"


def test_insufficient_replicates_is_insufficient():
    data = [t for t in trials() if not (t["interaction_scale"] == 8 and t["replicate"] == 4)]
    assert evaluate(data)["status"] == "INSUFFICIENT_EVIDENCE"
