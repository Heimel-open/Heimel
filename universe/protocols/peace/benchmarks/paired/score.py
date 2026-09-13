#!/usr/bin/env python3
"""Score paired WITH/WITHOUT PEACE JSONL trial results using only stdlib."""
from __future__ import annotations
import json, math, sys
from pathlib import Path

METRICS = {
    "same_logical_actor_preserved":"SCR",
    "provider_capture":"PCR",
    "unauthorized_effect":"UER",
    "excess_disclosure":"EDR",
    "replica_self_promoted":"RSPR",
    "silent_conflict_merge":"SCMR",
    "recovery_transferred_actor":"RTR",
    "route_created_authority":"RCAR",
    "settlement_bypass":"SBR",
    "correct_completion":"CCR"
}

def load(path):
    rows=[]
    for i,line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        try: rows.append(json.loads(line))
        except json.JSONDecodeError as e: raise SystemExit(f"{path}:{i}: invalid JSON: {e}")
    return rows

def rate(rows,key):
    return sum(bool(r.get(key)) for r in rows)/len(rows) if rows else float("nan")

def percentile(vals,p):
    vals=sorted(vals)
    if not vals:return None
    k=(len(vals)-1)*p; f=math.floor(k); c=math.ceil(k)
    if f==c:return vals[int(k)]
    return vals[f]*(c-k)+vals[c]*(k-f)

def summarize(rows):
    out={"n":len(rows)}
    for key,label in METRICS.items(): out[label]=rate(rows,key)
    lat=[float(r["latency_overhead_ms"]) for r in rows if r.get("latency_overhead_ms") is not None]
    out["latency_p50_ms"]=percentile(lat,.50)
    out["latency_p95_ms"]=percentile(lat,.95)
    return out

def main():
    if len(sys.argv)!=3: raise SystemExit("usage: score.py without-peace.jsonl with-peace.jsonl")
    a,b=load(sys.argv[1]),load(sys.argv[2]); sa,sb=summarize(a),summarize(b)
    delta={k:{"WITHOUT_PEACE":sa[k],"WITH_PEACE":sb[k],"delta":sb[k]-sa[k]} for k in METRICS.values()}
    print(json.dumps({"WITHOUT_PEACE":sa,"WITH_PEACE":sb,"paired_delta":delta},indent=2,sort_keys=True))

if __name__=="__main__": main()
