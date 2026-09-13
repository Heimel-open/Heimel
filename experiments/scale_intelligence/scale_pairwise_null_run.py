#!/usr/bin/env python3
"""Run SCALE-PAIRWISE-NULL-21."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import random
from pathlib import Path

import numpy as np

from scale_pairwise_null_falsifier import evaluate
from scale_sweep import EPISODES_PER_FAMILY, NODES, ROUNDS, force_nonzero_majority, noisy_blocks

INTERIOR=np.arange(16,47)
BLOCK=13
SCALES=(7,13)
FRESH_SEEDS=(87087,88088,89089,90090,91091,92092,93093,94094,95095,96096)
DISCOVERY_HASH="sha256:0c89e1c7d3b39c93abb03ac3a7bbee0d9079afb3c23ec5697b7839e659568132"
PRIMARY_NULL_SEED=210021
TOP5_NULL_SEED=210022
PERMUTATIONS=100000
TOP5=((6,7),(4,6),(3,4),(3,5),(7,8))


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
    native_margin=mu[:,None]*target[:,None]+modal.sum(axis=1)*target[:,None]
    modal_aligned=modal*target[:,None,None]
    err=max(
        float(np.max(np.abs(modal.sum(axis=1)-residual@a3[INTERIOR,:].T))),
        float(np.max(np.abs(final-(mu[:,None]+residual@a3.T)))),
    )
    return native,native_margin,modal_aligned,err


def pair_interactions(native_margin,modal_aligned):
    native=float(np.mean(native_margin>=0.0))
    out=[]
    for j in range(31):
        gj=modal_aligned[:,j,:]
        c_minus_j=float(np.mean(native_margin-2*gj>=0.0))
        for k in range(j+1,31):
            gk=modal_aligned[:,k,:]
            c_minus_k=float(np.mean(native_margin-2*gk>=0.0))
            c_minus_both=float(np.mean(native_margin-2*gj-2*gk>=0.0))
            interaction=(native+c_minus_both-c_minus_k-c_minus_j)/4.0
            out.append(interaction)
    return np.asarray(out,dtype=float)


def rankdata(x):
    order=np.argsort(x,kind="mergesort")
    ranks=np.empty(len(x),dtype=float)
    i=0
    while i<len(x):
        j=i+1
        while j<len(x) and x[order[j]]==x[order[i]]:
            j+=1
        r=(i+j-1)/2.0+1.0
        ranks[order[i:j]]=r
        i=j
    return ranks


def spearman(a,b):
    ra=rankdata(a); rb=rankdata(b)
    ra-=ra.mean(); rb-=rb.mean()
    den=np.linalg.norm(ra)*np.linalg.norm(rb)
    return float(ra@rb/den) if den else 0.0


def load_discovery():
    path=Path(__file__).parent/"evidence"/"scale-pairwise-null-21-discovery-vector.json"
    obj=json.loads(path.read_text(encoding="utf-8"))
    raw=base64.b64decode(obj["values_base64"])
    values=np.frombuffer(raw,dtype="<f8").copy()
    if len(values)!=465:
        raise RuntimeError("discovery vector length mismatch")

    pairs=[]
    idx=0
    for j in range(31):
        for k in range(j+1,31):
            pairs.append({
                "j":j,
                "k":k,
                "discovery_differential":float(values[idx]),
            })
            idx+=1
    canonical={
        "protocol":obj["protocol"],
        "source":obj["source"],
        "seeds":obj["seeds"],
        "pair_count":obj["pair_count"],
        "pairs":pairs,
    }
    encoded=json.dumps(
        canonical,sort_keys=True,separators=(",",":")
    ).encode("utf-8")
    actual_hash="sha256:"+hashlib.sha256(encoded).hexdigest()
    if actual_hash!=str(obj["sha256"]) or actual_hash!=DISCOVERY_HASH:
        raise RuntimeError("discovery vector hash mismatch")
    return values,actual_hash


def permutation_p(discovery,fresh,observed):
    rng=np.random.default_rng(PRIMARY_NULL_SEED)
    rd=rankdata(discovery); rd-=rd.mean(); rd/=np.linalg.norm(rd)
    rf=rankdata(fresh); rf-=rf.mean(); rf/=np.linalg.norm(rf)
    ge=0
    batch=2000
    remaining=PERMUTATIONS
    while remaining:
        n=min(batch,remaining)
        vals=np.empty(n,dtype=float)
        for i in range(n):
            vals[i]=rd@rf[rng.permutation(len(rf))]
        ge+=int(np.sum(vals>=observed))
        remaining-=n
    return (1+ge)/(PERMUTATIONS+1),ge


def top5_null(fresh,observed):
    rng=np.random.default_rng(TOP5_NULL_SEED)
    ge=0
    n=len(fresh)
    for _ in range(PERMUTATIONS):
        idx=rng.choice(n,size=5,replace=False)
        ge+=int(float(fresh[idx].sum())>=observed)
    return (1+ge)/(PERMUTATIONS+1),ge


def bootstrap_ci(values):
    rng=np.random.default_rng(210023)
    x=np.asarray(values,dtype=float)
    means=np.empty(20000,dtype=float)
    for i in range(len(means)):
        means[i]=rng.choice(x,size=len(x),replace=True).mean()
    return [float(np.quantile(means,0.025)),float(np.quantile(means,0.975))]


def run():
    discovery,discovery_hash=load_discovery()
    ops={s:decompose(s) for s in SCALES}
    fresh_by_rep=[]
    native_adv=[]
    max_error=0.0

    for seed in FRESH_SEEDS:
        xs=episodes(seed)
        interactions={}
        native={}
        for s in SCALES:
            a3,u,sigma,vt,svd_err=ops[s]
            n,margin,modal,err=modal_state(xs,a3,u,sigma,vt)
            max_error=max(max_error,svd_err,err)
            native[s]=n
            interactions[s]=pair_interactions(margin,modal)
        native_adv.append(native[13]-native[7])
        fresh_by_rep.append(interactions[13]-interactions[7])

    fresh_by_rep=np.asarray(fresh_by_rep)
    fresh=fresh_by_rep.mean(axis=0)
    rho=spearman(discovery,fresh)
    p,ge=permutation_p(discovery,fresh,rho)

    pairs=[(j,k) for j in range(31) for k in range(j+1,31)]
    index={p:i for i,p in enumerate(pairs)}
    top_idx=np.asarray([index[p] for p in TOP5],dtype=int)
    top_stat=float(fresh[top_idx].sum())
    top_p,top_ge=top5_null(fresh,top_stat)

    order=np.argsort(fresh)[::-1]
    rank_67=int(np.where(order==index[(6,7)])[0][0])+1

    result={
        "protocol":"SCALE-PAIRWISE-NULL-21",
        "pair_count":465,
        "replicate_count":len(FRESH_SEEDS),
        "fresh_seeds":list(FRESH_SEEDS),
        "max_numerical_error":max_error,
        "discovery_vector_hash":discovery_hash,
        "primary":{
            "spearman_rho":rho,
            "empirical_p":p,
            "null_exceedances":ge,
        },
        "primary_null":{
            "permutations":PERMUTATIONS,
            "rng_seed":PRIMARY_NULL_SEED,
        },
        "top5":{
            "pairs":[list(p) for p in TOP5],
            "fresh_sum":top_stat,
            "empirical_p":top_p,
            "null_exceedances":top_ge,
        },
        "top5_null":{
            "permutations":PERMUTATIONS,
            "rng_seed":TOP5_NULL_SEED,
        },
        "rank1_pair":{
            "pair":[6,7],
            "fresh_rank":rank_67,
            "pair_count":465,
            "rank_percentile":1.0-(rank_67-1)/465.0,
            "fresh_differential":float(fresh[index[(6,7)]]),
        },
        "native_advantage":{
            "replicates":[float(x) for x in native_adv],
            "mean":float(np.mean(native_adv)),
            "bootstrap_95_ci":bootstrap_ci(native_adv),
        },
        "fresh_pair_differentials":[float(x) for x in fresh],
    }
    result["verdict"]=evaluate(result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="scale_pairwise_null_21_result.json")
    args=parser.parse_args()
    result=run()
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(result["verdict"],indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
