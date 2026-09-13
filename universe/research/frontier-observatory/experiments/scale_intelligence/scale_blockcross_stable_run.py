#!/usr/bin/env python3
"""Run SCALE-BLOCKCROSS-27."""

from __future__ import annotations

import argparse
import itertools
import json
import random
from pathlib import Path

import numpy as np

from scale_blockcross_stable_falsifier import evaluate
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
FRESH_SEEDS=(
    167167,168168,169169,170170,171171,
    172172,173173,174174,175175,176176,
    177177,178178,179179,180180,181181,
    182182,183183,184184,185185,186186,
)
EPSILON=1e-12
ROTATION_SEED=270027
ROTATIONS=100


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


def maximal_blocks(sigma):
    out=[]
    start=0
    for i in range(1,len(sigma)+1):
        boundary=(
            i==len(sigma)
            or abs(sigma[i]-sigma[start])
            > 1e-12*max(1.0,abs(sigma[i]),abs(sigma[start]))
        )
        if boundary:
            out.append(tuple(range(start,i)))
            start=i
    return out


def stable_score(margin):
    return float(np.mean(np.where(
        margin>EPSILON,
        1.0,
        np.where(margin<-EPSILON,0.0,0.5),
    )))


def pair_interactions(xs,b,bases,pairs):
    mu=xs.mean(axis=1)
    target=np.where(mu>=0.0,1.0,-1.0)
    residual=xs-mu[:,None]
    native_margin=(
        mu[:,None]*target[:,None]
        +(residual@b.T)*target[:,None]
    )
    native=stable_score(native_margin)

    contributions=[
        ((residual@w)@(b@w).T)*target[:,None]
        for w in bases
    ]

    out=np.empty(len(pairs),dtype=float)
    for idx,(a,c) in enumerate(pairs):
        ya=contributions[a]
        yc=contributions[c]
        c_mp=stable_score(native_margin-2*ya)
        c_pm=stable_score(native_margin-2*yc)
        c_mm=stable_score(native_margin-2*ya-2*yc)
        out[idx]=(native+c_mm-c_pm-c_mp)/4.0
    return out,native


def exact_max_t_fwer(d):
    n,p=d.shape
    means=d.mean(axis=0)
    sds=d.std(axis=0,ddof=1)
    observed=np.divide(
        means,
        sds/np.sqrt(n),
        out=np.zeros_like(means),
        where=sds>0,
    )

    ss=np.sum(d*d,axis=0)
    patterns=1<<n
    max_t=np.empty(patterns,dtype=np.float64)
    batch=8192

    for start in range(0,patterns,batch):
        ints=np.arange(start,min(start+batch,patterns),dtype=np.uint32)
        bits=((ints[:,None]>>np.arange(n,dtype=np.uint32))&1).astype(float)
        signs=2.0*bits-1.0
        m=(signs@d)/n
        var=(ss[None,:]-n*m*m)/(n-1)
        var=np.maximum(var,1e-30)
        t=m/(np.sqrt(var)/np.sqrt(n))
        max_t[start:start+len(ints)]=np.max(t,axis=1)

    pvals=np.empty(p,dtype=float)
    for j,tobs in enumerate(observed):
        tol=1e-12*max(1.0,abs(float(tobs)))
        pvals[j]=np.mean(max_t>=tobs-tol)

    return means,observed,pvals,max_t


def minimum_threshold_distance(xs_by_seed,ops,bases,pairs):
    minimum=float("inf")
    for seed in FRESH_SEEDS:
        xs=xs_by_seed[seed]
        mu=xs.mean(axis=1)
        target=np.where(mu>=0.0,1.0,-1.0)
        residual=xs-mu[:,None]
        for scale in SCALES:
            b=ops[scale][0]
            native=(
                mu[:,None]*target[:,None]
                +(residual@b.T)*target[:,None]
            )
            contributions=[
                ((residual@w)@(b@w).T)*target[:,None]
                for w in bases
            ]
            states=[native]
            for a,c in pairs:
                ya=contributions[a]
                yc=contributions[c]
                states.extend((
                    native-2*ya,
                    native-2*yc,
                    native-2*ya-2*yc,
                ))
            for state in states:
                distance=np.minimum(
                    np.abs(state-EPSILON),
                    np.abs(state+EPSILON),
                )
                minimum=min(minimum,float(np.min(distance)))
    return minimum


def certify_basis_invariance(pooled,ops,bases):
    rng=np.random.default_rng(ROTATION_SEED)
    max_projector_abs=0.0
    max_projector_op=0.0

    for _ in range(ROTATIONS):
        for w in bases:
            z=rng.normal(size=(w.shape[1],w.shape[1]))
            q,_=np.linalg.qr(z)
            wr=w@q
            dp=wr@wr.T-w@w.T
            max_projector_abs=max(
                max_projector_abs,
                float(np.max(np.abs(dp))),
            )
            max_projector_op=max(
                max_projector_op,
                float(np.linalg.norm(dp,2)),
            )

    residual=pooled-pooled.mean(axis=1)[:,None]
    max_rnorm=float(np.max(np.linalg.norm(residual,axis=1)))
    max_bnorm=max(float(np.linalg.norm(ops[s][0],2)) for s in SCALES)

    # Pair state can contain two flipped projector contributions.
    margin_bound=4.0*max_rnorm*max_bnorm*max_projector_op
    return max_projector_abs,max_projector_op,margin_bound


def bootstrap_ci(values,seed):
    rng=np.random.default_rng(seed)
    x=np.asarray(values,dtype=float)
    draws=np.empty(20000,dtype=float)
    for i in range(len(draws)):
        draws[i]=rng.choice(x,size=len(x),replace=True).mean()
    return [float(np.quantile(draws,0.025)),float(np.quantile(draws,0.975))]


def run_experiment():
    ops={s:decompose(s) for s in SCALES}
    blocks=maximal_blocks(ops[13][2])
    expected=[
        (0,1,2,3),(4,),(5,),(6,),(7,8,9,10,11),
        (12,13,14,15,16),(17,),(18,19,20,21,22),
        (23,),(24,25,26,27),(28,29),(30,),
    ]
    if blocks!=expected:
        raise RuntimeError(f"block partition mismatch: {blocks}")

    bases=[ops[13][3].T[:,block] for block in blocks]
    pairs=list(itertools.combinations(range(len(blocks)),2))
    xs_by_seed={seed:episodes(seed) for seed in FRESH_SEEDS}

    x7=[]
    x13=[]
    native_adv=[]
    for seed in FRESH_SEEDS:
        a,n7=pair_interactions(xs_by_seed[seed],ops[7][0],bases,pairs)
        b,n13=pair_interactions(xs_by_seed[seed],ops[13][0],bases,pairs)
        x7.append(a)
        x13.append(b)
        native_adv.append(n13-n7)

    x7=np.asarray(x7)
    x13=np.asarray(x13)
    d=x13-x7
    means,tobs,pvals,max_t=exact_max_t_fwer(d)

    pair_rows=[]
    for idx,pair in enumerate(pairs):
        mean7=float(x7[:,idx].mean())
        mean13=float(x13[:,idx].mean())
        pair_rows.append({
            "pair":list(pair),
            "mean_X7":mean7,
            "mean_X13":mean13,
            "mean_D":float(means[idx]),
            "t":float(tobs[idx]),
            "fwer_p":float(pvals[idx]),
            "sign_reversal":bool(mean7*mean13<0.0),
            "replicate_D":[float(v) for v in d[:,idx]],
        })
    pair_rows.sort(key=lambda row:row["t"],reverse=True)

    pooled=np.vstack([xs_by_seed[s] for s in FRESH_SEEDS])
    min_gap=minimum_threshold_distance(xs_by_seed,ops,bases,pairs)
    max_proj_abs,max_proj_op,margin_bound=certify_basis_invariance(
        pooled,ops,bases
    )
    certified=bool(margin_bound<min_gap)

    block_rows=[]
    residual=pooled-pooled.mean(axis=1)[:,None]
    denom=float(np.sum(residual*residual))
    for idx,(block,w) in enumerate(zip(blocks,bases)):
        block_rows.append({
            "block":idx,
            "indices":list(block),
            "dimension":len(block),
            "singular_value":float(ops[13][2][block[0]]),
            "residual_overlap":float(np.sum((residual@w)**2)/denom),
            "gain_scale7":float(np.linalg.norm(ops[7][0]@w,"fro")**2),
            "gain_scale13":float(np.linalg.norm(ops[13][0]@w,"fro")**2),
        })

    positive=np.array([max(0.0,row["mean_D"]) for row in pair_rows])
    total=float(positive.sum())
    concentration={}
    for k in (1,3,5):
        concentration[str(k)]=(
            float(np.sort(positive)[::-1][:k].sum()/total)
            if total>0 else 0.0
        )

    result={
        "protocol":"SCALE-BLOCKCROSS-27",
        "canonical_base":"6b163b43c01b1c736b49241bd1aae6fd18430db0",
        "preregistration_sha":"11c0774dd06dc973e743f6549622c387a1fb53eb",
        "epsilon":EPSILON,
        "block_count":len(blocks),
        "pair_count":len(pairs),
        "replicate_count":len(FRESH_SEEDS),
        "fresh_seeds":list(FRESH_SEEDS),
        "block_partition":[list(b) for b in blocks],
        "pair_results":pair_rows,
        "block_diagnostics":block_rows,
        "network_concentration_positive_D":concentration,
        "native_context":{
            "replicate_advantages":[float(v) for v in native_adv],
            "mean_advantage":float(np.mean(native_adv)),
            "bootstrap_95_ci":bootstrap_ci(native_adv,270028),
        },
        "familywise_null":{
            "method":"exact paired sign-flip max-T",
            "sign_patterns":1<<len(FRESH_SEEDS),
            "max_t_95":float(np.quantile(max_t,0.95)),
            "max_t_99":float(np.quantile(max_t,0.99)),
        },
        "integrity":{
            "rotations":ROTATIONS,
            "rotation_seed":ROTATION_SEED,
            "max_internal_rotation_projector_error":max_proj_abs,
            "max_internal_rotation_projector_operator_norm":max_proj_op,
            "certified_max_margin_perturbation":margin_bound,
            "minimum_distance_to_score_threshold":min_gap,
            "basis_invariance_certified":certified,
        },
    }
    result["verdict"]=evaluate(result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="scale_blockcross_27_result.json")
    args=parser.parse_args()
    result=run_experiment()
    Path(args.output).write_text(
        json.dumps(result,indent=2,sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(result["verdict"],indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
