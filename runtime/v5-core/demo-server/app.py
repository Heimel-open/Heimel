"""VALO V5.0 — Live Demo Server"""
import asyncio, importlib.util, json, os, pathlib, subprocess, sys, time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

ROOT      = pathlib.Path(__file__).parent
L1_BINARY = pathlib.Path(os.environ.get("L1_BINARY",
            ROOT.parent / "l1-guardian" / "target" / "debug" / "l1-guardian"))
TCP_ADDR  = "127.0.0.1"
TCP_PORT  = 7743


def _bootstrap_l2():
    l2_dir = ROOT.parent / "l2-orchestrator"
    if "l2_orchestrator" not in sys.modules:
        pkg_spec = importlib.util.spec_from_file_location(
            "l2_orchestrator", l2_dir / "__init__.py",
            submodule_search_locations=[str(l2_dir)])
        pkg = importlib.util.module_from_spec(pkg_spec)
        sys.modules["l2_orchestrator"] = pkg
    for sub in ("codec", "observability"):
        mod_name = f"l2_orchestrator.{sub}"
        if mod_name not in sys.modules:
            sub_spec = importlib.util.spec_from_file_location(mod_name, l2_dir / f"{sub}.py")
            sub_mod = importlib.util.module_from_spec(sub_spec)
            sys.modules[mod_name] = sub_mod
            sub_spec.loader.exec_module(sub_mod)


_bootstrap_l2()
from l2_orchestrator import BridgeFactory                       # noqa: E402
from l2_orchestrator.codec import TCPTransport                  # noqa: E402
from l2_orchestrator.observability import StructuredLogger      # noqa: E402

StructuredLogger.set_component("demo-server")

ValoBridge, Decision = BridgeFactory.load()

# (description, ai_conf, c0, syntax_valid, latency_ok, warmup_frames, expected)
# L1 is stateful — each test spawns a fresh process so ValoGuardrail
# starts at Active/context_age=0. HALT tests send 2 warmup frames first
# (context_age: 0→1→2) then a 3rd valid frame triggers DirectHalt.
INFRA_TESTS = [
    ("Coherent confidence · ALLOW",      0.80, 1.0, True,  True,  0, Decision.ALLOW),
    ("Below coherence zone · DEGRADED",  0.20, 1.0, True,  True,  0, Decision.DEGRADED),
    ("Above coherence zone · DEGRADED",  1.20, 1.0, True,  True,  0, Decision.DEGRADED),
    ("Syntax flag invalid · DEGRADED",   0.80, 1.0, False, True,  0, Decision.DEGRADED),
    ("Context-age overflow · HALT",      0.80, 1.0, True,  True,  2, Decision.HALT),
]

VAIG_TESTS = [
    ("High confidence 0.95 · ALLOW",    0.95, 1.0, True,  True,  0, Decision.ALLOW),
    ("Low confidence 0.05 · DEGRADED",  0.05, 1.0, True,  True,  0, Decision.DEGRADED),
    ("Latency too slow · DEGRADED",     0.80, 1.0, True,  False, 0, Decision.DEGRADED),
    ("Context-age overflow · HALT",     0.80, 1.0, True,  True,  2, Decision.HALT),
]

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

@app.on_event("startup")
async def startup():
    if not L1_BINARY.exists():
        subprocess.run(["cargo", "build", "--features", "simulation"],
                       cwd=ROOT.parent / "l1-guardian", check=True)

def _run_single(desc, ai_conf, c0, syntax, latency, warmup, expected, category):
    proc = subprocess.Popen(
        [str(L1_BINARY), "--tcp", f"{TCP_ADDR}:{TCP_PORT}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.3)
        transport = TCPTransport()
        bridge = ValoBridge(transport=transport)
        bridge.connect({"host": TCP_ADDR, "port": TCP_PORT})
        for _ in range(warmup):
            bridge.send_frame(bridge.pack_telemetry_packet(0.80, 1.0, True, True))
        pkt = bridge.pack_telemetry_packet(ai_conf, c0, syntax, latency)
        decision, rtt_ns = bridge.send_frame(pkt)
        bridge.close()
    finally:
        proc.terminate()
        proc.wait()
    return {
        "category": category,
        "desc": desc,
        "decision": decision.name,
        "expected": expected.name,
        "pass": decision == expected,
        "rtt_us": round(rtt_ns / 1000, 1),
    }

def _run_all():
    results = []
    for args in INFRA_TESTS:
        results.append(_run_single(*args, "infra"))
    for args in VAIG_TESTS:
        results.append(_run_single(*args, "vaig"))
    return results

_lock = asyncio.Lock()

@app.get("/api/status")
async def status():
    return {"online": L1_BINARY.exists()}

@app.get("/api/run")
async def run_demo():
    async def stream():
        async with _lock:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, _run_all)
            for r in results:
                yield f"data: {json.dumps(r)}\n\n"
                await asyncio.sleep(0.18)
            yield 'data: "done"\n\n'
    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML

HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>VALO V5.0 — Live Demo</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500&family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;600&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0a0c0b;--bg2:#0f1211;--ink:#eef0ec;--dim:#8a8f88;--line:#1d201e;--line2:#2a2e2b;--accent:#c8ff3e;--warn:#ff6a3d;--ok:#c8ff3e}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--ink);font-family:Inter,system-ui,sans-serif;min-height:100vh;-webkit-font-smoothing:antialiased}
.mono{font-family:"JetBrains Mono",monospace}
header{display:flex;align-items:center;justify-content:space-between;padding:20px 32px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:12px;font-weight:700;font-size:14px;letter-spacing:.24em}
.mark{width:24px;height:24px;border-radius:6px;background:var(--accent);position:relative;box-shadow:0 0 20px rgba(200,255,62,.3);flex-shrink:0}
.mark::before,.mark::after{content:"";position:absolute;background:var(--bg)}
.mark::before{left:5px;right:5px;top:50%;height:2px;transform:translateY(-50%)}
.mark::after{top:5px;bottom:5px;left:50%;width:2px;transform:translateX(-50%)}
.status{display:flex;align-items:center;gap:8px;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--dim)}
.dot{width:6px;height:6px;border-radius:50%;background:var(--dim)}
.dot.online{background:var(--accent);box-shadow:0 0 8px var(--accent);animation:pulse 1.8s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
main{max-width:960px;margin:0 auto;padding:48px 32px 100px}
h1{font-family:Fraunces,serif;font-size:clamp(32px,5vw,56px);font-weight:500;letter-spacing:-.02em;line-height:1;margin-bottom:10px}
.sub{font-size:15px;color:var(--dim);margin-bottom:48px}
.section-label{font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--dim);margin-bottom:14px}
.section-label span{color:var(--accent);margin-right:8px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-bottom:36px}
.card{border:1px solid var(--line2);border-radius:12px;padding:16px 18px;background:var(--bg2);transition:border-color .3s,background .3s;min-height:90px}
.card.running{border-color:var(--accent);background:rgba(200,255,62,.04)}
.card.pass{border-color:var(--accent)}
.card.fail{border-color:var(--warn);background:rgba(255,106,61,.04)}
.card-desc{font-size:14px;font-weight:600;margin-bottom:8px;line-height:1.3}
.card-meta{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
.badge{font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;padding:3px 8px;border-radius:4px;border:1px solid var(--line2);color:var(--dim)}
.badge.ALLOW{color:var(--accent);border-color:var(--accent)}
.badge.HALT{color:var(--warn);border-color:var(--warn)}
.badge.DEGRADED{color:#f4d35e;border-color:#f4d35e}
.verdict{font-size:13px;font-weight:600;display:flex;align-items:center;gap:6px}
.verdict.pass{color:var(--accent)}
.verdict.fail{color:var(--warn)}
.rtt{font-size:10.5px;color:var(--dim);margin-top:4px}
.cta{display:flex;align-items:center;gap:20px;margin-top:40px;flex-wrap:wrap}
#run-btn{background:var(--accent);color:#0a0c0b;border:none;padding:16px 32px;border-radius:999px;font-family:inherit;font-size:14px;font-weight:700;letter-spacing:.04em;cursor:pointer;transition:filter .15s;display:flex;align-items:center;gap:10px}
#run-btn:hover{filter:brightness(1.08)}
#run-btn:disabled{opacity:.4;cursor:not-allowed;filter:none}
#score{font-size:18px;font-weight:600;color:var(--dim);transition:color .3s}
#score.done{color:var(--ink)}
.gridbg{position:fixed;inset:0;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,.018) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.018) 1px,transparent 1px);background-size:64px 64px;mask-image:radial-gradient(ellipse at 50% 0%,rgba(0,0,0,.5),transparent 60%);z-index:0}
main,header{position:relative;z-index:1}
</style>
</head>
<body>
<div class="gridbg"></div>
<header>
  <div class="brand"><div class="mark"></div>VALO</div>
  <div class="status mono"><div class="dot" id="dot"></div><span id="status-text">CHECKING</span></div>
</header>
<main>
  <div class="mono" style="font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--dim);margin-bottom:16px">V5.0 · Live System Test</div>
  <h1>L1 Guardian<br><span style="color:var(--accent)">in the room.</span></h1>
  <p class="sub">9 frames sent to the real Rust binary. Every result is live.</p>

  <div class="section-label mono"><span>01</span>Infrastructure Tests</div>
  <div class="cards" id="infra-cards"></div>

  <div class="section-label mono"><span>02</span>VAIG Token Guard</div>
  <div class="cards" id="vaig-cards"></div>

  <div class="cta">
    <button id="run-btn" onclick="runDemo()">&#9654; Run Demo</button>
    <div id="score" class="mono">— / 9 passed</div>
  </div>
</main>
<script>
const INFRA = [
  {desc:"Coherent confidence · ALLOW",     expected:"ALLOW"},
  {desc:"Below coherence zone · DEGRADED", expected:"DEGRADED"},
  {desc:"Above coherence zone · DEGRADED", expected:"DEGRADED"},
  {desc:"Syntax flag invalid · DEGRADED",  expected:"DEGRADED"},
  {desc:"Context-age overflow · HALT",     expected:"HALT"},
];
const VAIG = [
  {desc:"High confidence 0.95 · ALLOW",   expected:"ALLOW"},
  {desc:"Low confidence 0.05 · DEGRADED", expected:"DEGRADED"},
  {desc:"Latency too slow · DEGRADED",    expected:"DEGRADED"},
  {desc:"Context-age overflow · HALT",    expected:"HALT"},
];

function renderCards(tests, containerId) {
  const el = document.getElementById(containerId);
  el.innerHTML = tests.map((t,i) => `
    <div class="card" id="card-${containerId}-${i}">
      <div class="card-desc">${t.desc}</div>
      <div class="card-meta">
        <span class="badge mono ${t.expected}">${t.expected}</span>
        <span class="verdict mono" id="v-${containerId}-${i}">—</span>
      </div>
      <div class="rtt mono" id="rtt-${containerId}-${i}"></div>
    </div>`).join("");
}

function updateCard(category, idx, data) {
  const id = `card-${category}-cards-${idx}`;
  const card = document.getElementById(id);
  const verdict = document.getElementById(`v-${category}-cards-${idx}`);
  const rtt = document.getElementById(`rtt-${category}-cards-${idx}`);
  if (!card) return;
  card.className = "card " + (data.pass ? "pass" : "fail");
  verdict.className = "verdict mono " + (data.pass ? "pass" : "fail");
  verdict.innerHTML = data.pass
    ? `<span>&#10003;</span> ${data.decision}`
    : `<span>&#10007;</span> ${data.decision}`;
  rtt.textContent = `RTT ${data.rtt_us} µs`;
}

async function checkStatus() {
  try {
    const r = await fetch("/api/status");
    const d = await r.json();
    document.getElementById("dot").className = "dot " + (d.online ? "online" : "");
    document.getElementById("status-text").textContent = d.online ? "L1 ONLINE" : "L1 OFFLINE";
  } catch(e) {
    document.getElementById("status-text").textContent = "UNREACHABLE";
  }
}

function runDemo() {
  const btn = document.getElementById("run-btn");
  const score = document.getElementById("score");
  btn.disabled = true;
  score.className = "mono";
  renderCards(INFRA, "infra-cards");
  renderCards(VAIG, "vaig-cards");

  let passed = 0, total = 0;
  let ii = 0, vi = 0;

  const es = new EventSource("/api/run");
  es.onmessage = (e) => {
    if (e.data === '"done"') {
      es.close();
      btn.disabled = false;
      score.className = "mono done";
      score.textContent = `${passed} / 9 passed`;
      return;
    }
    const d = JSON.parse(e.data);
    if (d.pass) passed++;
    total++;
    score.textContent = `${passed} / ${total} passed`;
    if (d.category === "infra") updateCard("infra", ii++, d);
    else                        updateCard("vaig",  vi++, d);
  };
  es.onerror = () => { es.close(); btn.disabled = false; };
}

renderCards(INFRA, "infra-cards");
renderCards(VAIG, "vaig-cards");
checkStatus();
setInterval(checkStatus, 5000);
</script>
</body>
</html>"""
