#!/usr/bin/env python3
"""Run SCALE-COPULA-28."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np

from scale_copula_falsifier import evaluate
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
FRESH_SEEDS=tuple(range(187187,206207,1001))
SCRAMBLE_DRAWS=256
EPSILON=1e-12
EXPECTED_BLOCKS=[
    (0,1,2,3),(4,),(5,),(6,),(7,8,9,10,11),
    (12,13,14,15,16),(17,),(18,19,20,21,22),
    (23,),(24,25,26,27),(28,29),(30,),
]


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
    return b,u,sigma,vt,q


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


def projectors_from_scale13(ops):
    blocks=maximal_blocks(ops[13][2])
    if blocks!=EXPECTED_BLOCKS:
        raise RuntimeError(f"block partition mismatch: {blocks}")
    vt=ops[13][3]
    ps=[]
    for block in blocks:
        w=vt.T[:,block]
        ps.append(w@w.T)
    q=ops[13][4]
    remainder=q-sum(ps)
    ps.append(remainder)
    return blocks,ps


def stable_score(margin):
    values=np.where(
        margin>EPSILON,
        1.0,
        np.where(margin<-EPSILON,0.0,0.5),
    )
    return float(np.mean(values))


def sha_seed(*parts):
    raw="|".join(str(x) for x in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],"little")


def groups_for(xs):
    signed_sum=np.rint(xs.sum(axis=1)).astype(int)
    groups=[]
    for value in sorted(set(signed_sum.tolist())):
        groups.append(np.flatnonzero(signed_sum==value))
    return signed_sum,groups


def permutation_index(seed,groups,n):
    rng=np.random.default_rng(seed)
    out=np.arange(n,dtype=int)
    for idx in groups:
        if len(idx)>1:
            out[idx]=rng.permutation(idx)
    return out


def verify_conditional_permutation(perm,groups):
    for idx in groups:
        if not np.array_equal(np.sort(perm[idx]),idx):
            return False
    return True


def component_contributions(xs,b,projectors):
    mu=xs.mean(axis=1)
    target=np.where(mu>=0.0,1.0,-1.0)
    residual=xs-mu[:,None]
    components=np.asarray([
        residual@p@b.T for p in projectors
    ])
    native_res=residual@b.T
    decomp=float(np.max(np.abs(components.sum(axis=0)-native_res)))
    margin=mu[:,None]*target[:,None]+native_res*target[:,None]
    native=stable_score(margin)
    return mu,target,components,native,decomp


def mean_abs_offdiag_corr(energies):
    x=np.asarray(energies,dtype=float)
    sd=x.std(axis=0)
    valid=np.flatnonzero(sd>1e-15)
    if len(valid)<2:
        return 0.0
    c=np.corrcoef(x[:,valid],rowvar=False)
    mask=~np.eye(len(valid),dtype=bool)
    return float(np.mean(np.abs(c[mask])))


def scramble_scale(xs,scale,replicate_seed,b,projectors):
    mu,target,components,native,decomp=component_contributions(
        xs,b,projectors
    )
    n=len(xs)
    _,groups=groups_for(xs)
    total=components.sum(axis=0)
    independent_caps=np.empty(SCRAMBLE_DRAWS,dtype=float)
    max_coupled_error=0.0
    checksum_ok=True

    energies=np.sum(components*components,axis=2).T
    native_corr=mean_abs_offdiag_corr(energies)
    scrambled_corr=np.empty(SCRAMBLE_DRAWS,dtype=float)

    for q in range(SCRAMBLE_DRAWS):
        coupled_perm=permutation_index(
            sha_seed("SCALE-COPULA-28","coupled",replicate_seed,scale,q),
            groups,n
        )
        checksum_ok &= verify_conditional_permutation(coupled_perm,groups)
        coupled_margin=(
            mu[:,None]*target[:,None]
            +total[coupled_perm]*target[:,None]
        )
        coupled_cap=stable_score(coupled_margin)
        max_coupled_error=max(max_coupled_error,abs(coupled_cap-native))

        summed=np.zeros_like(total)
        scrambled_energy=np.empty_like(energies)
        for component in range(len(projectors)):
            perm=permutation_index(
                sha_seed(
                    "SCALE-COPULA-28","independent",
                    replicate_seed,scale,q,component
                ),
                groups,n
            )
            checksum_ok &= verify_conditional_permutation(perm,groups)
            summed+=components[component,perm]
            scrambled_energy[:,component]=energies[perm,component]

        independent_margin=(
            mu[:,None]*target[:,None]
            +summed*target[:,None]
        )
        independent_caps[q]=stable_score(independent_margin)
        scrambled_corr[q]=mean_abs_offdiag_corr(scrambled_energy)

    non_singleton=sum(len(idx) for idx in groups if len(idx)>1)/n
    return {
        "native":native,
        "independent_caps":independent_caps,
        "decomposition_error":decomp,
        "max_coupled_error":max_coupled_error,
        "checksum_ok":bool(checksum_ok),
        "native_energy_correlation":native_corr,
        "scrambled_energy_correlation_mean":float(scrambled_corr.mean()),
        "stratum_sizes":[int(len(idx)) for idx in groups],
        "non_singleton_fraction":float(non_singleton),
    }


def exact_signflip_t(values):
    x=np.asarray(values,dtype=float)
    n=len(x)
    mean=float(x.mean())
    sd=float(x.std(ddof=1))
    observed=mean/(sd/np.sqrt(n)) if sd>0 else (float("inf") if mean>0 else 0.0)
    ss=float(np.sum(x*x))
    patterns=1<<n
    ge=0
    batch=8192
    for start in range(0,patterns,batch):
        ints=np.arange(start,min(start+batch,patterns),dtype=np.uint32)
        bits=((ints[:,None]>>np.arange(n,dtype=np.uint32))&1).astype(float)
        signs=2.0*bits-1.0
        m=(signs@x)/n
        var=np.maximum((ss-n*m*m)/(n-1),1e-30)
        t=m/(np.sqrt(var)/np.sqrt(n))
        tol=1e-12*max(1.0,abs(observed))
        ge+=int(np.sum(t>=observed-tol))
    return observed,ge/patterns,patterns,ge


def bootstrap_ci(values,seed):
    rng=np.random.default_rng(seed)
    x=np.asarray(values,dtype=float)
    draws=np.empty(20000,dtype=float)
    for i in range(len(draws)):
        draws[i]=rng.choice(x,size=len(x),replace=True).mean()
    return [float(np.quantile(draws,0.025)),float(np.quantile(draws,0.975))]


def projector_integrity(projectors,q):
    total=sum(projectors)
    maxerr=float(np.max(np.abs(total-q)))
    for i,p in enumerate(projectors):
        maxerr=max(
            maxerr,
            float(np.max(np.abs(p-p.T))),
            float(np.max(np.abs(p@p-p))),
        )
        for j in range(i):
            maxerr=max(
                maxerr,
                float(np.max(np.abs(p@projectors[j]))),
            )
    return maxerr


def run_experiment():
    ops={s:decompose(s) for s in SCALES}
    blocks,projectors=projectors_from_scale13(ops)
    proj_error=projector_integrity(projectors,ops[13][4])

    rows=[]
    max_decomp=0.0
    max_coupled=0.0
    checksum_ok=True
    all_scrambled_adv=[]
    below_native_count=0
    total_scramble_adv=0

    for seed in FRESH_SEEDS:
        xs=episodes(seed)
        by_scale={}
        for scale in SCALES:
            by_scale[scale]=scramble_scale(
                xs,scale,seed,ops[scale][0],projectors
            )
            max_decomp=max(
                max_decomp,
                by_scale[scale]["decomposition_error"],
            )
            max_coupled=max(
                max_coupled,
                by_scale[scale]["max_coupled_error"],
            )
            checksum_ok &= by_scale[scale]["checksum_ok"]

        native_adv=by_scale[13]["native"]-by_scale[7]["native"]
        scramble_adv=(
            by_scale[13]["independent_caps"]
            -by_scale[7]["independent_caps"]
        )
        mean_scramble_adv=float(scramble_adv.mean())
        collapse=native_adv-mean_scramble_adv
        below_native_count+=int(np.sum(scramble_adv<native_adv))
        total_scramble_adv+=len(scramble_adv)
        all_scrambled_adv.extend(float(v) for v in scramble_adv)

        rows.append({
            "seed":seed,
            "native_scale7":by_scale[7]["native"],
            "native_scale13":by_scale[13]["native"],
            "native_advantage":native_adv,
            "scrambled_scale7_mean":float(
                by_scale[7]["independent_caps"].mean()
            ),
            "scrambled_scale13_mean":float(
                by_scale[13]["independent_caps"].mean()
            ),
            "scrambled_advantage_mean":mean_scramble_adv,
            "collapse":collapse,
            "native_energy_correlation_scale7":by_scale[7]["native_energy_correlation"],
            "native_energy_correlation_scale13":by_scale[13]["native_energy_correlation"],
            "scrambled_energy_correlation_scale7":by_scale[7]["scrambled_energy_correlation_mean"],
            "scrambled_energy_correlation_scale13":by_scale[13]["scrambled_energy_correlation_mean"],
            "stratum_sizes":by_scale[7]["stratum_sizes"],
            "non_singleton_fraction":by_scale[7]["non_singleton_fraction"],
        })

    collapse=np.asarray([r["collapse"] for r in rows])
    native_adv=np.asarray([r["native_advantage"] for r in rows])
    scrambled_adv=np.asarray([r["scrambled_advantage_mean"] for r in rows])
    t,p,patterns,ge=exact_signflip_t(collapse)

    result={
        "protocol":"SCALE-COPULA-28",
        "canonical_base":"b2109e4f7298134a7c5ca35f4aeb6dbbaf17dd6e",
        "preregistration_sha":"0cbc1dd30d4d70e85875a52481b71b4d9b7b5e2a",
        "component_count":len(projectors),
        "spectral_block_count":len(blocks),
        "block_partition":[list(b) for b in blocks],
        "replicate_count":len(FRESH_SEEDS),
        "fresh_seeds":list(FRESH_SEEDS),
        "scramble_draws":SCRAMBLE_DRAWS,
        "replicates":rows,
        "primary":{
            "mean_native_advantage":float(native_adv.mean()),
            "mean_scrambled_advantage":float(scrambled_adv.mean()),
            "mean_collapse":float(collapse.mean()),
            "t":float(t),
            "exact_p":float(p),
            "null_exceedances":int(ge),
            "native_advantage_bootstrap_95_ci":bootstrap_ci(native_adv,280028),
            "scrambled_advantage_bootstrap_95_ci":bootstrap_ci(scrambled_adv,280029),
            "collapse_bootstrap_95_ci":bootstrap_ci(collapse,280030),
        },
        "primary_null":{
            "method":"exact paired sign-flip t",
            "sign_patterns":patterns,
        },
        "diagnostics":{
            "scramble_advantage_draws_below_native_fraction":below_native_count/total_scramble_adv,
            "native_energy_correlation_scale7_mean":float(np.mean([r["native_energy_correlation_scale7"] for r in rows])),
            "native_energy_correlation_scale13_mean":float(np.mean([r["native_energy_correlation_scale13"] for r in rows])),
            "scrambled_energy_correlation_scale7_mean":float(np.mean([r["scrambled_energy_correlation_scale7"] for r in rows])),
            "scrambled_energy_correlation_scale13_mean":float(np.mean([r["scrambled_energy_correlation_scale13"] for r in rows])),
            "non_singleton_episode_fraction_mean":float(np.mean([r["non_singleton_fraction"] for r in rows])),
        },
        "integrity":{
            "max_projector_partition_error":proj_error,
            "max_native_decomposition_error":max_decomp,
            "max_coupled_control_capability_error":max_coupled,
            "all_conditional_multiset_checks_pass":bool(checksum_ok),
        },
    }
    result["verdict"]=evaluate(result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="scale_copula_28_result.json")
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
