import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import urllib.request
import time
from tools.njal_r01_executor import build_condition_prompt, parse_model_response

api_key = os.environ.get("NVIDIA_API_KEY", "")
chat_url = "https://integrate.api.nvidia.com/v1/chat/completions"
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
model = "meta/llama-3.2-11b-vision-instruct"

smoke_tasks = [
    {
        "id": "SMOKE-C2",
        "condition": "C2",
        "prompt": "A fruit stand starts with 5 boxes containing 12 apples each. 14 apples are sold. A display sign weighs 3 kilograms. How many apples remain?",
        "expected_answer": 46.0,
    },
    {
        "id": "SMOKE-C3I",
        "condition": "C3-I",
        "prompt": "A workshop has 4 racks holding 15 metal rods each. An idle compressor has a tank capacity of 50 liters. 22 rods are used in construction. How many rods remain in the racks?",
        "expected_answer": 38.0,
    },
    {
        "id": "SMOKE-C3R",
        "condition": "C3-R",
        "prompt": "In Phase 1, Station Alpha assembles 3 crates of 10 microchips each. An unrelated printer test prints 15 sheets and is discarded. In Phase 2, Station Beta assembles 4 crates of 8 microchips each, and 12 chips are shipped out. In Phase 3, an express order requires 2 times the quantity from Station Alpha plus all remaining chips from Station Beta. How many microchips are sent for the express order?",
        "expected_answer": 80.0,
    },
]

results = []
for st in smoke_tasks:
    st_id = st["id"]
    st_cond = st["condition"]
    print(f"\n=================== {st_id} (Condition {st_cond}) ===================")
    c_prompt = build_condition_prompt(st["prompt"], st_cond)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a precise, rigorous mathematical and analytical assistant. "
                    "Output ONLY the requested format fields. "
                    "Do NOT output any thinking process, monologue, preamble, or commentary."
                ),
            },
            {"role": "user", "content": c_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 1024,
    }
    t0 = time.time()
    req = urllib.request.Request(chat_url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            content = json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"]
            dt = time.time() - t0
            parsed = parse_model_response(content, condition=st_cond)
            ans = parsed.get("answer")
            exp = st["expected_answer"]
            match = "MATCH" if ans == exp else "DIFF"
            conf = parsed.get("confidence")
            steps = parsed.get("steps")
            act_size = parsed.get("active_workspace_size")
            act_comps = parsed.get("available_components_at_consequence")
            restores = parsed.get("restores")
            print(f"Time: {dt:.2f}s")
            print(f"Parsed Answer: {ans} (Expected: {exp}) -> {match}")
            print(f"Confidence: {conf} | Steps: {steps} | Active Size: {act_size}")
            print(f"Active Components: {act_comps}")
            print(f"Restores: {restores}")
            print("--- RAW OUTPUT SNIPPET ---")
            print(content[:350])
            results.append({"id": st_id, "dt": dt, "match": match, "parsed": parsed})
    except Exception as e:
        print(f"FAILED: {e}")
        results.append({"id": st_id, "error": str(e)})

print("\n--- SMOKE SUITE FINISHED ---")
print(json.dumps(results, indent=2))
