#!/usr/bin/env python3
"""Run SCALE-CROSSPROJECTOR-25."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np

from scale_crossprojector_falsifier import evaluate
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
FRESH_SEEDS=(117117,118118,119119,120120,121121,122122,123123,124124,125125,126126)
TARGET_BLOCKS={7:(6,7,8),13:(7,8,9,10,11)}
NULL_DRAWS=1000
NULL_SEED=250025
ROTATION_CHECK_SEED=250026


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
    return b,u,sigma,vt


def haar_subspace(rng,center_basis,dim):
    z=rng.normal(size=(center_basis.shape[1],dim))
    q,_=np.linalg.qr(z,mode="reduced")
    return center_basis@q


def cross_term(residual,mu,target,b,w):
    y_total=residual@b.T
    y_t=(residual@w)@(b@w).T
    y_r=y_total-y_t
    m=mu[:,None]*target[:,None]
    yt=y_t*target[:,None]
    yr=y_r*target[:,None]
    c_pp=float(np.mean(m+yt+yr>=0.0))
    c_pm=float(np.mean(m+yt-yr>=0.0))
    c_mp=float(np.mean(m-yt+yr>=0.0))
    c_mm=float(np.mean(m-yt-yr>=0.0))
    x=(c_pp+c_mm-c_pm-c_mp)/4.0
    return x,c_pp,y_t,y_r


def rankdata(x):
    order=np.argsort(x,kind="mergesort")
    ranks=np.empty(len(x),dtype=float)
    i=0
    while i<len(x):
        j=i+1
        while j<len(x) and x[order[j]]==x[order[i]]:
            j+=1
        ranks[order[i:j]]=(i+j-1)/2.0+1.0
        i=j
    return ranks


def spearman(a,b):
    ra=rankdata(np.asarray(a,dtype=float))
    rb=rankdata(np.asarray(b,dtype=float))
    ra-=ra.mean(); rb-=rb.mean()
    den=np.linalg.norm(ra)*np.linalg.norm(rb)
    return float(ra@rb/den) if den else 0.0


def bootstrap_ci(values,seed):
    rng=np.random.default_rng(seed)
    x=np.asarray(values,dtype=float)
    draws=np.empty(20000,dtype=float)
    for i in range(len(draws)):
        draws[i]=rng.choice(x,size=len(x),replace=True).mean()
    return [float(np.quantile(draws,0.025)),float(np.quantile(draws,0.975))]


def run_experiment():
    ops={s:decompose(s) for s in SCALES}
    qcenter=np.eye(NODES)-np.ones((NODES,NODES))/NODES
    evals,evecs=np.linalg.eigh(qcenter)
    center_basis=evecs[:,evals>0.5]

    target_w={}
    target_p={}
    max_projector_error=0.0
    for s in SCALES:
        w=ops[s][3].T[:,TARGET_BLOCKS[s]]
        p=w@w.T
        target_w[s]=w
        target_p[s]=p
        max_projector_error=max(
            max_projector_error,
            float(np.max(np.abs(p-p.T))),
            float(np.max(np.abs(p@p-p))),
        )

    rot_rng=np.random.default_rng(ROTATION_CHECK_SEED)
    max_rotation_error=0.0
    for s in SCALES:
        w=target_w[s]
        p=target_p[s]
        d=w.shape[1]
        for _ in range(1000):
            z=rot_rng.normal(size=(d,d))
            q,_=np.linalg.qr(z)
            pr=(w@q)@(w@q).T
            max_rotation_error=max(max_rotation_error,float(np.max(np.abs(pr-p))))

    xs_by_seed={seed:episodes(seed) for seed in FRESH_SEEDS}
    xs=np.vstack([xs_by_seed[s] for s in FRESH_SEEDS])
    mu=xs.mean(axis=1)
    target=np.where(mu>=0.0,1.0,-1.0)
    residual=xs-mu[:,None]

    target_cross={}
    native_cap={}
    target_gain={}
    max_decomp_error=0.0
    for s in SCALES:
        x,native,yt,yr=cross_term(residual,mu,target,ops[s][0],target_w[s])
        target_cross[s]=x
        native_cap[s]=native
        target_gain[s]=float(np.linalg.norm(ops[s][0]@target_w[s],"fro")**2)
        max_decomp_error=max(
            max_decomp_error,
            float(np.max(np.abs((yt+yr)-residual@ops[s][0].T))),
        )
    target_delta=target_cross[13]-target_cross[7]

    null_rng=np.random.default_rng(NULL_SEED)
    null_delta=np.empty(NULL_DRAWS,dtype=float)
    gains7=np.empty(NULL_DRAWS,dtype=float)
    gains13=np.empty(NULL_DRAWS,dtype=float)

    for qidx in range(NULL_DRAWS):
        w7=haar_subspace(null_rng,center_basis,3)
        w13=haar_subspace(null_rng,center_basis,5)
        x7,_,_,_=cross_term(residual,mu,target,ops[7][0],w7)
        x13,_,_,_=cross_term(residual,mu,target,ops[13][0],w13)
        null_delta[qidx]=x13-x7
        gains7[qidx]=float(np.linalg.norm(ops[7][0]@w7,"fro")**2)
        gains13[qidx]=float(np.linalg.norm(ops[13][0]@w13,"fro")**2)

    ge=int(np.sum(null_delta>=target_delta))
    p=(1+ge)/(NULL_DRAWS+1)

    gain_distance=np.sqrt(
        np.log(gains7/target_gain[7])**2
        + np.log(gains13/target_gain[13])**2
    )
    nearest=np.argsort(gain_distance)[:100]
    nearest_ge=int(np.sum(null_delta[nearest]>=target_delta))
    nearest_p=(1+nearest_ge)/101.0

    replicate_rows=[]
    for seed in FRESH_SEEDS:
        xarr=xs_by_seed[seed]
        m=xarr.mean(axis=1)
        t=np.where(m>=0.0,1.0,-1.0)
        r=xarr-m[:,None]
        row={"seed":seed}
        for s in SCALES:
            xc,native,_,_=cross_term(r,m,t,ops[s][0],target_w[s])
            row[f"cross_{s}"]=xc
            row[f"native_{s}"]=native
        row["delta_cross"]=row["cross_13"]-row["cross_7"]
        row["native_advantage"]=row["native_13"]-row["native_7"]
        replicate_rows.append(row)

    result={
        "protocol":"SCALE-CROSSPROJECTOR-25",
        "canonical_base":"25c79cd05b662d44ea6a919fdd47aede5d2e5fd7",
        "preregistration_sha":"65f65c19c856fd87b33c1c03396271466b0c2350",
        "fresh_seed_count":len(FRESH_SEEDS),
        "fresh_seeds":list(FRESH_SEEDS),
        "target_blocks":{"7":list(TARGET_BLOCKS[7]),"13":list(TARGET_BLOCKS[13])},
        "primary":{
            "target_cross_scale7":target_cross[7],
            "target_cross_scale13":target_cross[13],
            "target_delta_cross":target_delta,
            "target_sign_reversal":bool(target_cross[7]*target_cross[13]<0),
            "null_mean":float(null_delta.mean()),
            "null_std":float(null_delta.std()),
            "null_min":float(null_delta.min()),
            "null_max":float(null_delta.max()),
            "null_ge_target":ge,
            "empirical_p":p,
        },
        "gain_diagnostics":{
            "target_gain_scale7":target_gain[7],
            "target_gain_scale13":target_gain[13],
            "null_gain_scale7_mean":float(gains7.mean()),
            "null_gain_scale13_mean":float(gains13.mean()),
            "target_gain_scale7_percentile":float(np.mean(gains7<=target_gain[7])),
            "target_gain_scale13_percentile":float(np.mean(gains13<=target_gain[13])),
            "spearman_gain7_vs_delta_cross":spearman(gains7,null_delta),
            "spearman_gain13_vs_delta_cross":spearman(gains13,null_delta),
            "spearman_log_gain_ratio_vs_delta_cross":spearman(np.log(gains13/gains7),null_delta),
            "nearest_100_max_log_gain_distance":float(gain_distance[nearest].max()),
            "nearest_100_empirical_p":nearest_p,
            "nearest_100_ge_target":nearest_ge,
        },
        "native_context":{
            "native_scale7":native_cap[7],
            "native_scale13":native_cap[13],
            "native_advantage":native_cap[13]-native_cap[7],
        },
        "replicates":replicate_rows,
        "delta_cross_bootstrap_95_ci":bootstrap_ci([r["delta_cross"] for r in replicate_rows],250027),
        "native_advantage_bootstrap_95_ci":bootstrap_ci([r["native_advantage"] for r in replicate_rows],250028),
        "null":{"draws":NULL_DRAWS,"rng_seed":NULL_SEED},
        "integrity":{
            "max_projector_error":max_projector_error,
            "max_decomposition_error":max_decomp_error,
            "max_internal_rotation_projector_error":max_rotation_error,
        },
    }
    result["verdict"]=evaluate(result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="scale_crossprojector_25_result.json")
    args=parser.parse_args()
    result=run_experiment()
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(result["verdict"],indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
