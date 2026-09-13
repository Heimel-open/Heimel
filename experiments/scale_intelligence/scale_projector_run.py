#!/usr/bin/env python3
"""Run SCALE-PROJECTOR-24."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np

from scale_projector_falsifier import evaluate
from scale_sweep import (
    EPISODES_PER_FAMILY,
    NODES,
    ROUNDS,
    force_nonzero_majority,
    noisy_blocks,
)

INTERIOR=np.arange(16,47)
BLOCK=13
SCALES=(7,13)
FRESH_SEEDS=(107107,108108,109109,110110,111111,112112,113113,114114,115115,116116)
TARGET_BLOCKS={7:(6,7,8),13:(7,8,9,10,11)}
NULL_DRAWS=1000
NULL_SEED=240024
ROTATION_CHECK_SEED=240027


def one_round_self_padded(scale):
    a=np.zeros((NODES,NODES),dtype=float)
    for i in range(NODES):
        a[i,i]+=0.2
        for offset in (-2*scale,-scale,scale,2*scale):
            j=i+offset
            if not 0<=j<NODES:
                j=i
            a[i,j]+=0.2
    return a


def episodes(seed):
    base=seed+BLOCK*100000
    ur=random.Random(base+3000000)
    rr=random.Random(base+4000000)
    xs=[]
    for _ in range(EPISODES_PER_FAMILY):
        xs.append(force_nonzero_majority(noisy_blocks(ur,BLOCK),ur))
    for _ in range(EPISODES_PER_FAMILY):
        rotation=rr.randrange(BLOCK)
        xs.append(force_nonzero_majority(noisy_blocks(rr,BLOCK,rotation=rotation),rr))
    return np.asarray(xs,dtype=float)


def decompose(scale):
    a3=np.linalg.matrix_power(one_round_self_padded(scale),ROUNDS)
    q=np.eye(NODES)-np.ones((NODES,NODES))/NODES
    b=a3[INTERIOR,:]@q
    u,sigma,vt=np.linalg.svd(b,full_matrices=False)
    err=float(np.max(np.abs(b-(u*sigma)@vt)))
    return a3,b,u,sigma,vt,err


def effect_for_subspace(residual,mu,target,b,W):
    native_res=residual@b.T
    native_margin=mu[:,None]*target[:,None]+native_res*target[:,None]
    native_cap=float(np.mean(native_margin>=0.0))
    contribution=(residual@W)@(b@W).T
    flip_margin=native_margin-2*contribution*target[:,None]
    flip_cap=float(np.mean(flip_margin>=0.0))
    return native_cap-flip_cap,native_cap,flip_cap


def overlap_for_subspace(residual,W):
    return float(np.sum((residual@W)**2)/np.sum(residual**2))


def haar_subspace(rng,center_basis,dim):
    z=rng.normal(size=(center_basis.shape[1],dim))
    q,_=np.linalg.qr(z,mode="reduced")
    return center_basis@q


def bootstrap_ci(values,seed):
    rng=np.random.default_rng(seed)
    x=np.asarray(values,dtype=float)
    draws=np.empty(20000,dtype=float)
    for i in range(len(draws)):
        draws[i]=rng.choice(x,size=len(x),replace=True).mean()
    return [float(np.quantile(draws,0.025)),float(np.quantile(draws,0.975))]


def run_experiment():
    ops={s:decompose(s) for s in SCALES}

    xs_by_seed={seed:episodes(seed) for seed in FRESH_SEEDS}
    xs=np.vstack([xs_by_seed[seed] for seed in FRESH_SEEDS])
    mu=xs.mean(axis=1)
    target=np.where(mu>=0.0,1.0,-1.0)
    residual=xs-mu[:,None]

    target_w={}
    target_projectors={}
    max_projector_error=0.0
    max_operator_error=max(ops[s][5] for s in SCALES)

    for s in SCALES:
        vt=ops[s][4]
        w=vt.T[:,TARGET_BLOCKS[s]]
        p=w@w.T
        target_w[s]=w
        target_projectors[s]=p
        max_projector_error=max(
            max_projector_error,
            float(np.max(np.abs(p-p.T))),
            float(np.max(np.abs(p@p-p))),
        )

    # Internal basis rotation must not change the projector.
    rot_rng=np.random.default_rng(ROTATION_CHECK_SEED)
    max_rotation_error=0.0
    for s in SCALES:
        w=target_w[s]
        p=target_projectors[s]
        dim=w.shape[1]
        for _ in range(1000):
            z=rot_rng.normal(size=(dim,dim))
            q,_=np.linalg.qr(z)
            pr=(w@q)@(w@q).T
            max_rotation_error=max(
                max_rotation_error,
                float(np.max(np.abs(pr-p))),
            )

    target_effect={}
    target_overlap={}
    target_native={}
    target_flip={}
    for s in SCALES:
        eff,native,flip=effect_for_subspace(
            residual,mu,target,ops[s][1],target_w[s]
        )
        target_effect[s]=eff
        target_native[s]=native
        target_flip[s]=flip
        target_overlap[s]=overlap_for_subspace(residual,target_w[s])

    target_delta=target_effect[13]-target_effect[7]

    # Deterministic centered-space basis.
    qcenter=np.eye(NODES)-np.ones((NODES,NODES))/NODES
    evals,evecs=np.linalg.eigh(qcenter)
    center_basis=evecs[:,evals>0.5]

    null_rng=np.random.default_rng(NULL_SEED)
    null_delta=[]
    null_effect={7:[],13:[]}
    null_overlap={7:[],13:[]}

    for _ in range(NULL_DRAWS):
        w7=haar_subspace(null_rng,center_basis,3)
        w13=haar_subspace(null_rng,center_basis,5)
        e7,_,_=effect_for_subspace(residual,mu,target,ops[7][1],w7)
        e13,_,_=effect_for_subspace(residual,mu,target,ops[13][1],w13)
        null_effect[7].append(e7)
        null_effect[13].append(e13)
        null_delta.append(e13-e7)
        null_overlap[7].append(overlap_for_subspace(residual,w7))
        null_overlap[13].append(overlap_for_subspace(residual,w13))

    null_delta=np.asarray(null_delta)
    upper_count=int(np.sum(null_delta>=target_delta))
    primary_p=(1+upper_count)/(NULL_DRAWS+1)
    lower_p=(1+int(np.sum(null_delta<=target_delta)))/(NULL_DRAWS+1)

    # Fresh replicate context for target intervention only.
    replicate_rows=[]
    for seed in FRESH_SEEDS:
        x=xs_by_seed[seed]
        m=x.mean(axis=1)
        t=np.where(m>=0.0,1.0,-1.0)
        r=x-m[:,None]
        row={"seed":seed}
        for s in SCALES:
            eff,native,flip=effect_for_subspace(r,m,t,ops[s][1],target_w[s])
            row[f"effect_{s}"]=eff
            row[f"native_{s}"]=native
            row[f"flip_{s}"]=flip
        row["delta_effect"]=row["effect_13"]-row["effect_7"]
        row["native_advantage"]=row["native_13"]-row["native_7"]
        replicate_rows.append(row)

    overlap_diag={}
    for s in SCALES:
        arr=np.asarray(null_overlap[s])
        val=target_overlap[s]
        overlap_diag[str(s)]={
            "target_overlap":val,
            "null_mean":float(arr.mean()),
            "null_std":float(arr.std()),
            "empirical_percentile":float(np.mean(arr<=val)),
            "upper_tail_p":(1+int(np.sum(arr>=val)))/(NULL_DRAWS+1),
            "lower_tail_p":(1+int(np.sum(arr<=val)))/(NULL_DRAWS+1),
        }

    result={
        "protocol":"SCALE-PROJECTOR-24",
        "canonical_base":"4d39c18f9b446f469d15458de02d0dcdd80fd623",
        "preregistration_sha":"82d816a5d53677445443a1f0b71b6edee1d88e41",
        "fresh_seed_count":len(FRESH_SEEDS),
        "fresh_seeds":list(FRESH_SEEDS),
        "target_blocks":{"7":list(TARGET_BLOCKS[7]),"13":list(TARGET_BLOCKS[13])},
        "primary":{
            "target_effect_scale7":target_effect[7],
            "target_effect_scale13":target_effect[13],
            "target_delta_effect":target_delta,
            "null_delta_mean":float(null_delta.mean()),
            "null_delta_std":float(null_delta.std()),
            "null_delta_min":float(null_delta.min()),
            "null_delta_max":float(null_delta.max()),
            "null_ge_target":upper_count,
            "empirical_p":primary_p,
            "lower_tail_p":lower_p,
        },
        "native_context":{
            "native_scale7":target_native[7],
            "native_scale13":target_native[13],
            "native_advantage":target_native[13]-target_native[7],
        },
        "target_overlap":overlap_diag,
        "replicates":replicate_rows,
        "replicate_delta_effect_bootstrap_95_ci":bootstrap_ci(
            [r["delta_effect"] for r in replicate_rows],240025
        ),
        "native_advantage_bootstrap_95_ci":bootstrap_ci(
            [r["native_advantage"] for r in replicate_rows],240026
        ),
        "null":{
            "draws":NULL_DRAWS,
            "rng_seed":NULL_SEED,
        },
        "integrity":{
            "max_projector_error":max_projector_error,
            "max_operator_error":max_operator_error,
            "max_internal_rotation_projector_error":max_rotation_error,
        },
    }
    result["verdict"]=evaluate(result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="scale_projector_24_result.json")
    args=parser.parse_args()
    result=run_experiment()
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(result["verdict"],indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
