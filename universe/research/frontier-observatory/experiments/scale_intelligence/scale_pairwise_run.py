#!/usr/bin/env python3
"""Run SCALE-PAIRWISE-20 fresh pairwise attribution."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np

from scale_pairwise_falsifier import evaluate
from scale_sweep import EPISODES_PER_FAMILY, NODES, ROUNDS, force_nonzero_majority, noisy_blocks

INTERIOR=np.arange(16,47)
FRESH_SEEDS=(82082,83083,84084,85085,86086)
SCALES=(7,13)
BLOCK=13


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
    a=one_round_self_padded(scale)
    a3=np.linalg.matrix_power(a,ROUNDS)
    q=np.eye(NODES)-np.ones((NODES,NODES))/NODES
    b=a3[INTERIOR,:]@q
    u,sigma,vt=np.linalg.svd(b,full_matrices=False)
    err=float(np.max(np.abs(b-(u*sigma)@vt)))
    return a3,u,sigma,vt,err


def modal_state(xs,a3,u,sigma,vt):
    mu=xs.mean(axis=1)
    target=np.where(mu>=0,1.0,-1.0)
    residual=xs-mu[:,None]
    coeff=residual@vt.T
    modal=coeff[:,:,None]*sigma[None,:,None]*u.T[None,:,:]
    final=xs@a3.T
    native=float(np.mean(final[:,INTERIOR]*target[:,None]>=0.0))
    modal_err=float(np.max(np.abs(modal.sum(axis=1)-residual@a3[INTERIOR,:].T)))
    state_err=float(np.max(np.abs(final-(mu[:,None]+residual@a3.T))))
    aligned_mu=mu*target
    aligned_modal=modal*target[:,None,None]
    return native,aligned_mu,aligned_modal,max(modal_err,state_err)


def pair_interactions(aligned_mu,aligned_modal):
    native_margin=aligned_mu[:,None]+aligned_modal.sum(axis=1)
    out={}
    native_cap=float(np.mean(native_margin>=0.0))
    for j in range(aligned_modal.shape[1]):
        gj=aligned_modal[:,j,:]
        for k in range(j+1,aligned_modal.shape[1]):
            gk=aligned_modal[:,k,:]
            cpp=native_cap
            cmm=float(np.mean(native_margin-2*gj-2*gk>=0.0))
            cpm=float(np.mean(native_margin-2*gk>=0.0))
            cmp=float(np.mean(native_margin-2*gj>=0.0))
            out[(j,k)]=(cpp+cmm-cpm-cmp)/4.0
    return out


def run_experiment():
    ops={s:decompose(s) for s in SCALES}
    pair_trials=[]
    native_advantages=[]
    max_err=0.0

    for replicate,seed in enumerate(FRESH_SEEDS):
        xs=episodes(seed)
        native={}
        interactions={}
        for scale in SCALES:
            a3,u,sigma,vt,svd_err=ops[scale]
            n,mu,modal,err=modal_state(xs,a3,u,sigma,vt)
            max_err=max(max_err,svd_err,err)
            native[scale]=n
            interactions[scale]=pair_interactions(mu,modal)
        native_advantages.append(native[13]-native[7])
        for j in range(31):
            for k in range(j+1,31):
                pair_trials.append({
                    "replicate":replicate,
                    "seed":seed,
                    "j":j,
                    "k":k,
                    "interaction_scale7":interactions[7][(j,k)],
                    "interaction_scale13":interactions[13][(j,k)],
                    "differential":interactions[13][(j,k)]-interactions[7][(j,k)],
                })

    payload={
        "protocol":"SCALE-PAIRWISE-20",
        "canonical_base":"f82df8d651f8b486deaaeb776b80caad6aaa17b3",
        "preregistration_sha":"9e08a6e4dc0c0b32e57b18593a3e19c0f3bd4b14",
        "fresh_seeds":list(FRESH_SEEDS),
        "native_advantages":native_advantages,
        "pair_trials":pair_trials,
        "max_numerical_error":max_err,
    }
    payload["verdict"]=evaluate(payload)
    return payload


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="scale_pairwise_20_result.json")
    args=parser.parse_args()
    result=run_experiment()
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(result["verdict"],indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
