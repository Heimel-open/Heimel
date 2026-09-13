#!/usr/bin/env python3
from __future__ import annotations
import argparse, gc, json, math, random, re, sys
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass(frozen=True)
class E:
    id:str; text:str; a:str|None=None; b:str|None=None; kind:str="SUPPORT"
@dataclass(frozen=True)
class Q:
    id:str; a:str; b:str; ans:str
@dataclass
class W:
    id:str; shards:list[list[E]]; edges:list[tuple[str,str]]; qs:list[Q]

def reach(edges,a,b):
    g={}
    for x,y in edges:g.setdefault(x,set()).add(y)
    seen={a}; st=[a]
    while st:
        x=st.pop()
        for y in g.get(x,()):
            if y==b:return True
            if y not in seen:seen.add(y);st.append(y)
    return False

def world(seed,wid,n=3,chain_edges=6,distractors=8):
    if n<2 or chain_edges<n: raise ValueError("bad participants/chain")
    r=random.Random(seed); alpha=list("ABCDEFGHIJKLMNPQRSTUVWXYZ")
    chain=r.sample(alpha,chain_edges+1); edges=list(zip(chain,chain[1:]))
    ev=[E(f"{wid}-E{i}",f"Archive {i}: {a} leads to {b}.",a,b) for i,(a,b) in enumerate(edges)]
    off=[x for x in alpha if x not in chain]
    for i in range(2):
        a,b=r.sample(off,2); ev.append(E(f"{wid}-C{i}",f"Disputed note {i}: {a} does not lead to {b}.",a,b,"CONTRADICT"))
    for i in range(distractors):
        a,b=r.sample(alpha,2); ev.append(E(f"{wid}-D{i}",f"Side note {i}: {a} is near {b}; no directed relation is established.",kind="DISTRACTOR"))
    shards=[[] for _ in range(n)]
    for i,e in enumerate([x for x in ev if x.kind=="SUPPORT"]): shards[i%n].append(e)
    used={e.id for s in shards for e in s}; rest=[e for e in ev if e.id not in used]; r.shuffle(rest)
    for e in rest: shards[r.randrange(n)].append(e)
    pos=[]
    for hop in (2,3,4,chain_edges):
        if hop<=chain_edges:
            pos += [(chain[i],chain[i+hop]) for i in range(chain_edges-hop+1)]
    r.shuffle(pos); pos=pos[:4]
    neg=[(chain[min(h,chain_edges)],chain[0]) for h in (2,3,chain_edges)]
    neg += [(r.choice(chain),r.choice(off)) for _ in range(3)]
    neg=list(dict.fromkeys(neg))[:4]
    qs=[Q(f"{wid}-P{i}",a,b,"YES") for i,(a,b) in enumerate(pos)]
    qs += [Q(f"{wid}-N{i}",a,b,"NO") for i,(a,b) in enumerate(neg)]
    r.shuffle(qs)
    for q in qs:
        assert ("YES" if reach(edges,q.a,q.b) else "NO")==q.ans
    for s in shards:
        local=[(e.a,e.b) for e in s if e.kind=="SUPPORT"]
        assert not reach(local,chain[0],chain[-1])
    return W(wid,shards,edges,qs)

def shard_text(s): return "\n".join(f"[{e.id}] {e.text}" for e in s)
def new_field(): return {"admitted":{},"unresolved":[],"revision":0,"attempts":0,"mutations":0}
def field_text(f):
    z=["ADMITTED RELATIONS:"]
    z += [f"- {a} leads to {b} [sources: {','.join(src)}]" for (a,b),src in sorted(f["admitted"].items())] or ["- NONE"]
    if f["unresolved"]: z+=["UNRESOLVED:"]+[f"- {x}" for x in f["unresolved"]]
    return "\n".join(z)
def oracle_text(w): return "ADMITTED RELATIONS:\n"+"\n".join(f"- {a} leads to {b} [sources: ORACLE]" for a,b in w.edges)

def refs(raw,shard):
    u=raw.upper(); out=[]
    for e in shard:
        if e.id.upper() in u: out.append(e.id)
    pairs=re.findall(r"\b([A-Z])\s*(?:->|LEADS TO)\s*([A-Z])\b",u)
    pairs+=re.findall(r"\bEDGE\s+([A-Z])\s+([A-Z])\b",u)
    for a,b in pairs:
        for e in shard:
            if e.a==a and e.b==b and e.id not in out: out.append(e.id)
    return out

def admit(f,shard,ids,p,rnd):
    by={e.id:e for e in shard}; f["attempts"]+=1; mut=False; events=[]
    if not ids:return [{"decision":"NO_CANDIDATE","participant":p,"round":rnd}]
    for i in ids:
        e=by.get(i)
        if not e:
            events.append({"evidence_id":i,"decision":"REJECT","basis":"NOT_IN_SHARD"}); continue
        if e.kind=="SUPPORT" and e.a and e.b:
            k=(e.a,e.b)
            if k not in f["admitted"]: f["admitted"][k]=[e.id]; mut=True
            events.append({"evidence_id":e.id,"candidate":f"{e.a}->{e.b}","decision":"ADMIT","participant":p,"round":rnd})
        elif e.kind=="CONTRADICT" and e.a and e.b:
            x=f"{e.a}->{e.b}: {e.id}"
            if x not in f["unresolved"]: f["unresolved"].append(x); mut=True
            events.append({"evidence_id":e.id,"candidate":f"{e.a}->{e.b}","decision":"UNRESOLVED","participant":p,"round":rnd})
        else:
            events.append({"evidence_id":e.id,"decision":"REJECT","basis":"DISTRACTOR","participant":p,"round":rnd})
    if mut:f["revision"]+=1;f["mutations"]+=1
    return events

def extract_prompt(s,f):
    return f"""Extract explicit directed relational evidence for a governed field.
Read only YOUR EVIDENCE. Cite the exact evidence id for every explicit "X leads to Y" or "X does not lead to Y".
Do not infer transitive edges. Do not cite side notes. Preferred form: USE W0-E0
YOUR EVIDENCE:
{shard_text(s)}
CURRENT GOVERNED FIELD (read-only):
{field_text(f)}
"""
def answer_prompt(ctx,q):
    return f"""Use only the supplied state. Determine whether a directed path exists.
Answer exactly YES or NO as the first word.
{ctx}
QUESTION: Does {q.a} lead to {q.b} through one or more directed steps?
ANSWER:"""
def binary(x):
    u=x.strip().upper(); m=re.match(r"^(YES|NO)\b",u)
    if m:return m.group(1)
    z=re.findall(r"\b(YES|NO)\b",u); return z[0] if len(z)==1 else None

class Runner:
    def __init__(self,mock=False,use4=True): self.mock=mock;self.use4=use4;self.model=None;self.tok=None;self.mid=None
    def unload(self):
        self.model=self.tok=self.mid=None;gc.collect()
        try:
            import torch
            if torch.cuda.is_available():torch.cuda.empty_cache()
        except:pass
    def load(self,mid):
        if self.mock:self.mid="MOCK";return
        if self.mid==mid and self.model is not None:return
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM
        self.unload();self.tok=AutoTokenizer.from_pretrained(mid);kw={"device_map":"auto","low_cpu_mem_usage":True}
        if self.use4 and torch.cuda.is_available():
            from transformers import BitsAndBytesConfig
            kw["quantization_config"]=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_compute_dtype=torch.float16,bnb_4bit_quant_type="nf4")
        else:kw["torch_dtype"]=torch.float16 if torch.cuda.is_available() else torch.float32
        self.model=AutoModelForCausalLM.from_pretrained(mid,**kw);self.mid=mid
    def tokens(self,x):return max(1,len(x)//4) if self.mock or self.tok is None else len(self.tok.encode(x))
    def run(self,p,mid,n=64):
        self.load(mid)
        if self.mock:
            if "YOUR EVIDENCE:" in p:
                sec=p.split("YOUR EVIDENCE:",1)[1].split("CURRENT GOVERNED FIELD",1)[0];out=[]
                for line in sec.splitlines():
                    m=re.match(r"\[([^\]]+)\]\s+(.*)",line.strip())
                    if m and (" leads to " in m.group(2) or " does not lead to " in m.group(2)):out.append("USE "+m.group(1))
                return "\n".join(out)
            q=re.search(r"QUESTION: Does ([A-Z]) lead to ([A-Z])",p)
            if q:
                clean=re.sub(r"\b([A-Z]) does not lead to ([A-Z])\b","",p,flags=re.I)
                ed=re.findall(r"\b([A-Z]) leads to ([A-Z])\b",clean,flags=re.I)
                return "YES" if reach([(a.upper(),b.upper()) for a,b in ed],*q.groups()) else "NO"
            return ""
        import torch
        text=self.tok.apply_chat_template([{"role":"user","content":p}],tokenize=False,add_generation_prompt=True)
        inp=self.tok(text,return_tensors="pt");dev=next(self.model.parameters()).device;inp={k:v.to(dev) for k,v in inp.items()}
        with torch.no_grad():o=self.model.generate(**inp,max_new_tokens=n,do_sample=False,pad_token_id=self.tok.eos_token_id)
        return self.tok.decode(o[0][inp["input_ids"].shape[1]:],skip_special_tokens=True)

def selfcheck():
    s=[E("T-E0","A leads to B.","A","B"),E("T-C0","X does not lead to Y.","X","Y","CONTRADICT")]
    for x in ("USE T-E0","EDGE A B","A leads to B"):
        assert "T-E0" in refs(x,s)
    f=new_field();admit(f,s,["T-E0"],0,0);assert ("A","B") in f["admitted"] and f["revision"]==1
    r=f["revision"];admit(f,s,[],0,1);assert f["revision"]==r
    admit(f,s,["T-C0"],0,2);assert f["unresolved"]
    world(20260819,"SELF")
    return {"status":"PASS","parser":"PASS","admission":"PASS","revision_semantics":"PASS","world":"PASS"}

def preflight(run,mid):
    if run.mock:return {"status":"PASS","mode":"MOCK"}
    s=[E("PF-E0","Archive: A leads to B.","A","B"),E("PF-D0","Side note.",kind="DISTRACTOR")];f=new_field()
    raw=run.run(extract_prompt(s,f),mid); ids=refs(raw,s)
    if "PF-E0" not in ids:raise RuntimeError("MODEL_PREFLIGHT_FAILED extraction: "+repr(raw[:250]))
    admit(f,s,ids,0,0)
    ctx="ADMITTED RELATIONS:\n- A leads to B\n- B leads to C"
    y=run.run(answer_prompt(ctx,Q("Y","A","C","YES")),mid,8); n=run.run(answer_prompt(ctx,Q("N","C","A","NO")),mid,8)
    if binary(y)!="YES" or binary(n)!="NO":raise RuntimeError(f"MODEL_PREFLIGHT_FAILED YES={y[:80]!r} NO={n[:80]!r}")
    return {"status":"PASS","extraction_raw":raw[:250],"yes":y[:80],"no":n[:80]}

def evaluate(run,mid,ctx,qs,wid,cond,p=-1):
    rows=[];ok=0;bad=0
    for q in qs:
        pr=answer_prompt(ctx,q);raw=run.run(pr,mid,8);ans=binary(raw);score=int(ans==q.ans) if ans else 0
        bad+=ans is None;ok+=score;rows.append({"world":wid,"condition":cond,"participant":p,"holdout":asdict(q),"answer":ans,"score":score,"parse_ok":ans is not None,"output":raw[:300],"input_tokens":run.tokens(pr)})
    return ok/len(qs),rows,bad

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seed",type=int,default=20260819);ap.add_argument("--worlds",type=int,default=3);ap.add_argument("--participants",type=int,default=3);ap.add_argument("--rounds",type=int,default=2)
    ap.add_argument("--model-a",default="Qwen/Qwen2.5-1.5B-Instruct");ap.add_argument("--mock",action="store_true");ap.add_argument("--self-test-only",action="store_true");ap.add_argument("--no-4bit",action="store_true")
    ap.add_argument("--out",default="/content/tofoo_relational_results_v1");ap.add_argument("--min-oracle",type=float,default=.70);ap.add_argument("--min-recall",type=float,default=.50)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    man={"test":"TOFOO_RELATIONAL_EMERGENCE_V1","seed":a.seed,"worlds":a.worlds,"participants":a.participants,"rounds":a.rounds,"model_a":a.model_a,"mock_mode":a.mock,
         "primary_metric":"relational - max(isolated_max, pooled_raw)","controls":["ISOLATED","POOLED_RAW","ORACLE_FIELD","RELATIONAL"],
         "invariants":["NO_DIRECT_RELATIONAL_STATE_WRITE_PATH","NO_HIDDEN_HOLDOUT_ADMISSION","PROVENANCE_REQUIRED_FOR_ADMISSION","CONTRADICTION_MAY_REMAIN_UNRESOLVED","MODEL_CANNOT_SELF_AUTHORIZE_ADMISSION"]}
    try:man["self_check"]=selfcheck()
    except Exception as e:man.update(instrument_status="TEST_INVALID_SELF_CHECK",error=str(e));(out/"manifest.json").write_text(json.dumps(man,indent=2));print(json.dumps(man,indent=2));return 2
    if a.self_test_only:man["instrument_status"]="SELF_CHECK_PASS";(out/"manifest.json").write_text(json.dumps(man,indent=2));print(json.dumps(man,indent=2));return 0
    run=Runner(a.mock,not a.no_4bit)
    try:man["model_preflight"]=preflight(run,a.model_a)
    except Exception as e:man.update(instrument_status="TEST_INVALID_MODEL_PREFLIGHT",error=str(e));(out/"manifest.json").write_text(json.dumps(man,indent=2));print(json.dumps(man,indent=2));return 3
    rows=[];rawx=[];events=[];fields={};summ=[];parsebad=0
    for wi in range(a.worlds):
        w=world(a.seed+wi,f"W{wi}",a.participants);isos=[]
        for p,s in enumerate(w.shards):
            z,r,b=evaluate(run,a.model_a,shard_text(s),w.qs,w.id,"ISOLATED",p);isos.append(z);rows+=r;parsebad+=b
        pooled="\n".join(shard_text(s) for s in w.shards);ps,r,b=evaluate(run,a.model_a,pooled,w.qs,w.id,"POOLED_RAW");rows+=r;parsebad+=b
        oscore,r,b=evaluate(run,a.model_a,oracle_text(w),w.qs,w.id,"ORACLE_FIELD");rows+=r;parsebad+=b
        f=new_field();recognized=0
        for rnd in range(a.rounds):
            for p,s in enumerate(w.shards):
                raw=run.run(extract_prompt(s,f),a.model_a);ids=refs(raw,s);recognized+=len(ids);rawx.append({"world":w.id,"round":rnd,"participant":p,"recognized":ids,"raw":raw[:600]});events += [{"world":w.id,**x} for x in admit(f,s,ids,p,rnd)]
        rs,r,b=evaluate(run,a.model_a,field_text(f),w.qs,w.id,"RELATIONAL");rows+=r;parsebad+=b;fields[w.id]=f
        truth=set(w.edges);got=set(f["admitted"]);tp=len(truth&got);fp=len(got-truth);rec=tp/len(truth);prec=tp/(tp+fp) if tp+fp else 0
        summ.append({"world":w.id,"isolated_max":max(isos),"pooled_raw":ps,"oracle_field":oscore,"relational":rs,"relational_surplus":rs-max(max(isos),ps),"recognized_candidates":recognized,"field_revision":f["revision"],"field_precision":prec,"field_recall":rec})
    d={k:sum(x[k] for x in summ)/len(summ) for k in ("isolated_max","pooled_raw","oracle_field","relational","relational_surplus","field_precision","field_recall")}
    d["recognized_candidates"]=sum(x["recognized_candidates"] for x in summ);d["parse_failure_rate"]=parsebad/len(rows) if rows else 1
    if d["recognized_candidates"]==0:status="TEST_INVALID_NO_OBSERVABLE_CANDIDATES"
    elif d["oracle_field"]<a.min_oracle:status="TEST_INVALID_MODEL_BELOW_TASK_FLOOR"
    elif d["field_recall"]<a.min_recall:status="TEST_INVALID_FIELD_EXTRACTION_BELOW_FLOOR"
    elif d["parse_failure_rate"]>.10:status="TEST_INVALID_ANSWER_INTERFACE"
    else:status="VALID_SIGNAL_DISCOVERY_RUN"
    interp="DO_NOT_INTERPRET_AS_RESEARCH_RESULT" if status!="VALID_SIGNAL_DISCOVERY_RUN" else ("POSITIVE_RELATIONAL_SURPLUS_CANDIDATE" if d["relational_surplus"]>0 else "NO_RELATIONAL_SURPLUS_IN_THIS_RUN")
    man.update(instrument_status=status,interpretation=interp,diagnostics=d)
    (out/"manifest.json").write_text(json.dumps(man,indent=2));(out/"summary.json").write_text(json.dumps(summ,indent=2));(out/"runs.json").write_text(json.dumps(rows,indent=2));(out/"raw_extractions.json").write_text(json.dumps(rawx,indent=2))
    (out/"fields.json").write_text(json.dumps({k:{"admitted":{f"{a}->{b}":v for (a,b),v in f["admitted"].items()},"unresolved":f["unresolved"],"revision":f["revision"],"attempts":f["attempts"],"mutations":f["mutations"]} for k,f in fields.items()},indent=2))
    with (out/"admission_events.jsonl").open("w") as fh:
        for e in events:fh.write(json.dumps(e)+"\n")
    print(json.dumps({"status":status,"interpretation":interp,"diagnostics":d},indent=2));print(json.dumps(summ,indent=2))
    if status!="VALID_SIGNAL_DISCOVERY_RUN":print("TEST INVALID: do not interpret scores.",file=sys.stderr);return 4
    return 0

if __name__=="__main__":raise SystemExit(main())
