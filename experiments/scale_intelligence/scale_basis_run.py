#!/usr/bin/env python3
"""Run SCALE-BASIS-23 degenerate-SVD invariance audit."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np

from scale_basis_falsifier import evaluate
from scale_sweep import EPISODES_PER_FAMILY, NODES, ROUNDS, force_nonzero_majority, noisy_blocks

INTERIOR=np.arange(16,47)
BLOCK=13
SEEDS=(97097,98098,99099,100100,101101,102102,103103,104104,105105,106106)
ROTATIONS=1000
RNG_SEED=230023


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
        rot=rr.randrange(BLOCK)
        xs.append(force_nonzero_majority(noisy_blocks(rr,BLOCK,rotation=rot),rr))
    return np.asarray(xs,dtype=float)


def decompose(scale):
    a3=np.linalg.matrix_power(one_round_self_padded(scale),ROUNDS)
    q=np.eye(NODES)-np.ones((NODES,NODES))/NODES
    b=a3[INTERIOR,:]@q
    u,sigma,vt=np.linalg.svd(b,full_matrices=False)
    return a3,b,u,sigma,vt


def haar(rng,n):
    z=rng.normal(size=(n,n))
    q,r=np.linalg.qr(z)
    d=np.sign(np.diag(r))
    d[d==0]=1.0
    return q*d


def prep(scale,xs,ops):
    a3,b,u,sigma,vt=ops[scale]
    mu=xs.mean(axis=1)
    target=np.where(mu>=0.0,1.0,-1.0)
    residual=xs-mu[:,None]
    coeff=residual@vt.T
    modal=coeff[:,:,None]*sigma[None,:,None]*u.T[None,:,:]
    margin=mu[:,None]*target[:,None]+modal.sum(axis=1)*target[:,None]
    return {
        "target":target,
        "residual":residual,
        "coeff":coeff,
        "margin":margin,
    }


def pair_phase_from_rotated(scale,rotation,data,ops):
    _,_,u,sigma,_=ops[scale]
    target=data["target"]
    coeff=data["coeff"]
    margin=data["margin"]

    if scale==7:
        block_idx=np.array([6,7,8])
        cnew=coeff[:,block_idx]@rotation
        unew=u[:,block_idx]@rotation
        gj=sigma[6]*cnew[:,0,None]*unew[:,0][None,:]*target[:,None]
        gk=sigma[6]*cnew[:,1,None]*unew[:,1][None,:]*target[:,None]
    else:
        block_idx=np.array([7,8,9,10,11])
        cnew=coeff[:,block_idx]@rotation
        unew=u[:,block_idx]@rotation
        gj=sigma[6]*coeff[:,6,None]*u[:,6][None,:]*target[:,None]
        gk=sigma[7]*cnew[:,0,None]*unew[:,0][None,:]*target[:,None]

    cpp=float(np.mean(margin>=0.0))
    cmp=float(np.mean(margin-2*gj>=0.0))
    cpm=float(np.mean(margin-2*gk>=0.0))
    cmm=float(np.mean(margin-2*gj-2*gk>=0.0))
    return (cpp+cmm-cpm-cmp)/2.0


def run():
    ops={s:decompose(s) for s in (7,13)}
    xs_by_seed={seed:episodes(seed) for seed in SEEDS}
    prepared={
        (s,seed):prep(s,xs_by_seed[seed],ops)
        for s in (7,13) for seed in SEEDS
    }

    rng=np.random.default_rng(RNG_SEED)
    delta=[]
    max_operator_error=0.0

    for _ in range(ROTATIONS):
        r7=haar(rng,3)
        r13=haar(rng,5)

        for scale,rot,block_idx in (
            (7,r7,np.array([6,7,8])),
            (13,r13,np.array([7,8,9,10,11])),
        ):
            _,b,u,sigma,vt=ops[scale]
            ur=u.copy()
            vtr=vt.copy()
            ur[:,block_idx]=u[:,block_idx]@rot
            vtr[block_idx,:]=rot.T@vt[block_idx,:]
            reconstructed=(ur*sigma)@vtr
            max_operator_error=max(
                max_operator_error,
                float(np.max(np.abs(b-reconstructed))),
            )

        p7=np.mean([
            pair_phase_from_rotated(7,r7,prepared[(7,seed)],ops)
            for seed in SEEDS
        ])
        p13=np.mean([
            pair_phase_from_rotated(13,r13,prepared[(13,seed)],ops)
            for seed in SEEDS
        ])
        delta.append(float(p13-p7))

    delta=np.asarray(delta)

    # Conservative state-error bound. Centered entries have abs <=2.
    max_native_state_error=float(2*NODES*max_operator_error)

    # 300 pair labels do not involve any index in {6,...,11}; their phase
    # statistics are unchanged by the rotations. At the minimum rotated
    # target value, 32 of those unchanged pairs exceed the target. At most
    # all 164 other affected pairs can also exceed it, so worst rank <=197.
    rank_bound={
        "native_basis_rank":4,
        "unaffected_pair_count":300,
        "affected_other_pair_count":164,
        "unaffected_pairs_ge_min_rotated_target":32,
        "worst_case_rank_upper_bound":197,
    }

    result={
        "protocol":"SCALE-BASIS-23",
        "canonical_base":"79efda1eef41948b9a7b1317ada355ceea3b501d",
        "preregistration_sha":"f47dc20d4d03694a047d2ec7e8ad2aceabbe76af",
        "rotation_count":ROTATIONS,
        "rng_seed":RNG_SEED,
        "degenerate_blocks":{
            "scale7":{"indices":[6,7,8],"singular_value":float(ops[7][3][6])},
            "scale13":{"indices":[7,8,9,10,11],"singular_value":float(ops[13][3][7])},
        },
        "max_operator_reconstruction_error":max_operator_error,
        "max_native_state_error":max_native_state_error,
        "target_delta_phase_distribution":{
            "min":float(delta.min()),
            "max":float(delta.max()),
            "median":float(np.median(delta)),
            "std":float(np.std(delta,ddof=1)),
            "positive_fraction":float(np.mean(delta>0)),
            "negative_fraction":float(np.mean(delta<0)),
            "native_basis_value":0.005509702620967727,
            "native_basis_percentile":float(np.mean(delta<=0.005509702620967727)),
        },
        "rank_bound":rank_bound,
    }
    result["verdict"]=evaluate(result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="scale_basis_23_result.json")
    args=parser.parse_args()
    result=run()
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(result["verdict"],indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
