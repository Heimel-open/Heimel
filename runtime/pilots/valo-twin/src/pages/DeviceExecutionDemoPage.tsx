import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  Ban,
  CheckCircle2,
  Cpu,
  FileKey2,
  Fingerprint,
  Network,
  Play,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import {
  DEVICE_EXECUTION_SCENARIOS,
  getActiveDeviceStageId,
  getDeviceScenarioDurationMs,
  getVisibleDeviceEvents,
  type DeviceExecutionScenario,
  type DeviceExecutionTone,
} from "./deviceExecutionDemoData";

const toneClasses: Record<DeviceExecutionTone, string> = {
  neutral: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  pass: "border-emerald-300/30 bg-emerald-300/10 text-emerald-100",
  warn: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  fail: "border-rose-300/30 bg-rose-300/10 text-rose-100",
};

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 border-t border-white/10 py-3 first:border-t-0 md:grid-cols-[150px_1fr] md:gap-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-zinc-600">{label}</div>
      <div className="break-words text-sm leading-6 text-zinc-300">{value}</div>
    </div>
  );
}

function ScenarioButton({
  scenario,
  selected,
  onSelect,
}: {
  scenario: DeviceExecutionScenario;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`rounded-2xl border p-4 text-left transition ${
        selected
          ? "border-cyan-300/40 bg-cyan-300/[0.08]"
          : "border-white/10 bg-black/20 hover:border-white/20"
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-semibold text-zinc-100">{scenario.label}</span>
        <span
          className={`rounded-full border px-2.5 py-1 text-[10px] font-bold tracking-wide ${
            scenario.verdict === "ALLOW" ? toneClasses.pass : toneClasses.fail
          }`}
        >
          {scenario.verdict}
        </span>
      </div>
      <p className="mt-2 text-xs leading-5 text-zinc-500">{scenario.title}</p>
    </button>
  );
}

export default function DeviceExecutionDemoPage() {
  const [scenarioId, setScenarioId] = useState<DeviceExecutionScenario["id"]>(
    "compromised-proxy",
  );
  const [elapsedMs, setElapsedMs] = useState(0);
  const [running, setRunning] = useState(false);

  const scenario = useMemo(
    () =>
      DEVICE_EXECUTION_SCENARIOS.find((candidate) => candidate.id === scenarioId) ??
      DEVICE_EXECUTION_SCENARIOS[0],
    [scenarioId],
  );
  const durationMs = getDeviceScenarioDurationMs(scenario);
  const visibleEvents = getVisibleDeviceEvents(scenario, elapsedMs);
  const activeStageId = getActiveDeviceStageId(scenario, elapsedMs);
  const complete = elapsedMs >= durationMs;

  useEffect(() => {
    if (!running) return;

    const startedAt = performance.now() - elapsedMs;
    const timer = window.setInterval(() => {
      const next = Math.min(performance.now() - startedAt, durationMs);
      setElapsedMs(next);
      if (next >= durationMs) setRunning(false);
    }, 80);

    return () => window.clearInterval(timer);
  }, [durationMs, elapsedMs, running]);

  function selectScenario(nextId: DeviceExecutionScenario["id"]) {
    setScenarioId(nextId);
    setElapsedMs(0);
    setRunning(false);
  }

  function runScenario() {
    if (complete) setElapsedMs(0);
    setRunning(true);
  }

  function resetScenario() {
    setRunning(false);
    setElapsedMs(0);
  }

  return (
    <div className="flex-1 overflow-auto bg-[#07090b] p-4 md:p-6">
      <div className="mx-auto flex w-full max-w-[1560px] flex-col gap-6">
        <section className="grid gap-6 rounded-3xl border border-cyan-300/20 bg-cyan-300/[0.045] p-6 lg:grid-cols-[minmax(0,1fr)_390px] md:p-8">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/25 bg-cyan-300/[0.07] px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-cyan-200">
              <Fingerprint className="size-4" />
              Attributed device execution
            </div>
            <h1 className="mt-5 max-w-5xl text-3xl font-semibold tracking-tight text-zinc-100 md:text-5xl">
              No device acts anonymously.
            </h1>
            <p className="mt-4 max-w-4xl text-base leading-7 text-zinc-400 md:text-lg">
              A device identity is not enough. Before an IoT, edge or OT action becomes real,
              VALO binds the physical device, measured state, actor, mandate, target and outcome.
            </p>
            <div className="mt-5 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm font-medium text-zinc-200">
              Device identity → State attestation → Operator mandate → VAIG → REHT → RACS → Signed receipt
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/25 p-5">
            <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Synthetic industrial example</div>
            <p className="mt-2 text-sm leading-6 text-zinc-300">
              An edge gateway asks to change network state. One request is compromised and blocked.
              One is bounded, authorized and released.
            </p>
            <div className="mt-4 grid gap-3">
              {DEVICE_EXECUTION_SCENARIOS.map((candidate) => (
                <ScenarioButton
                  key={candidate.id}
                  scenario={candidate}
                  selected={candidate.id === scenario.id}
                  onSelect={() => selectScenario(candidate.id)}
                />
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,.75fr)]">
          <div className="rounded-3xl border border-white/10 bg-[#0d1011] p-6 md:p-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">Active scenario</div>
                <h2 className="mt-2 text-2xl font-semibold text-zinc-100 md:text-3xl">{scenario.title}</h2>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-500 md:text-base">{scenario.summary}</p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  type="button"
                  onClick={runScenario}
                  disabled={running}
                  className="inline-flex items-center gap-2 rounded-xl border border-cyan-300/30 bg-cyan-300/10 px-4 py-2.5 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-300/15 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Play className="size-4" />
                  {complete ? "Run again" : running ? "Running" : "Run example"}
                </button>
                <button
                  type="button"
                  onClick={resetScenario}
                  className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] px-4 py-2.5 text-sm font-semibold text-zinc-300 transition hover:border-white/20"
                >
                  <RotateCcw className="size-4" />
                  Reset
                </button>
              </div>
            </div>

            <div className="mt-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <Cpu className="size-5 text-cyan-200" />
                <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-zinc-600">Device</div>
                <div className="mt-1 text-sm font-semibold text-zinc-200">{scenario.device.id}</div>
                <div className="mt-1 text-xs leading-5 text-zinc-500">{scenario.device.zone}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <Network className="size-5 text-cyan-200" />
                <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-zinc-600">Requested action</div>
                <div className="mt-1 text-sm font-semibold text-zinc-200">{scenario.request.action}</div>
                <div className="mt-1 text-xs leading-5 text-zinc-500">{scenario.request.destination}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <ShieldCheck className="size-5 text-cyan-200" />
                <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-zinc-600">Runtime state</div>
                <div className={`mt-1 text-sm font-semibold ${scenario.attestation.state === "ATTESTED" ? "text-emerald-200" : "text-rose-200"}`}>
                  {scenario.attestation.state}
                </div>
                <div className="mt-1 text-xs leading-5 text-zinc-500">Observed {scenario.attestation.observed}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <FileKey2 className="size-5 text-cyan-200" />
                <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-zinc-600">Final outcome</div>
                <div className={`mt-1 text-sm font-semibold ${scenario.verdict === "ALLOW" ? "text-emerald-200" : "text-rose-200"}`}>
                  {complete ? scenario.governance.racs : "PENDING"}
                </div>
                <div className="mt-1 text-xs leading-5 text-zinc-500">Receipt appears after enforcement.</div>
              </div>
            </div>

            <div className="mt-6 overflow-x-auto pb-2">
              <div className="grid min-w-[940px] grid-cols-7 gap-2">
                {scenario.stages.map((stage) => {
                  const reached = elapsedMs >= stage.atMs;
                  const active = running && activeStageId === stage.id;
                  return (
                    <div
                      key={stage.id}
                      className={`min-h-32 rounded-2xl border p-4 transition ${
                        reached ? toneClasses[stage.tone] : "border-white/10 bg-black/20 text-zinc-600"
                      } ${active ? "ring-2 ring-cyan-300/25" : ""}`}
                    >
                      <div className="text-[10px] font-bold uppercase tracking-[0.18em] opacity-70">
                        {String(scenario.stages.indexOf(stage) + 1).padStart(2, "0")}
                      </div>
                      <div className="mt-5 text-sm font-semibold">{stage.label}</div>
                      <div className="mt-2 text-[11px] font-bold tracking-wide">
                        {reached ? stage.result : "PENDING"}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <aside className="rounded-3xl border border-white/10 bg-[#0d1011] p-6 md:p-8">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-600">
              <Activity className="size-4" />
              Evidence stream
            </div>
            <div className="mt-5 space-y-3">
              {visibleEvents.map((event) => (
                <div key={`${event.atMs}-${event.title}`} className={`rounded-2xl border p-4 ${toneClasses[event.tone]}`}>
                  <div className="flex items-center justify-between gap-3 text-[10px] font-bold uppercase tracking-wide opacity-70">
                    <span>{event.source}</span>
                    <span>{(event.atMs / 1000).toFixed(1)}s</span>
                  </div>
                  <div className="mt-2 text-sm font-semibold">{event.title}</div>
                  <p className="mt-1 text-xs leading-5 opacity-80">{event.detail}</p>
                </div>
              ))}
              {visibleEvents.length === 0 && (
                <div className="rounded-2xl border border-dashed border-white/10 p-5 text-sm text-zinc-600">
                  Run the example to generate evidence.
                </div>
              )}
            </div>
          </aside>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-3xl border border-white/10 bg-[#0d1011] p-6 md:p-8">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">
              <Fingerprint className="size-4" />
              Bound context
            </div>
            <div className="mt-5">
              <DetailRow label="Physical device" value={`${scenario.device.id} · ${scenario.device.asset}`} />
              <DetailRow label="Device identity" value={scenario.device.identity} />
              <DetailRow label="Actor" value={scenario.request.actor} />
              <DetailRow label="Mandate" value={scenario.request.mandate} />
              <DetailRow label="Expected state" value={scenario.attestation.expected} />
              <DetailRow label="Observed state" value={scenario.attestation.observed} />
              <DetailRow label="VAIG evidence" value={scenario.governance.vaig} />
            </div>
          </div>

          <div className={`rounded-3xl border p-6 md:p-8 ${complete ? (scenario.verdict === "ALLOW" ? "border-emerald-300/30 bg-emerald-300/[0.055]" : "border-rose-300/30 bg-rose-300/[0.055]") : "border-white/10 bg-[#0d1011]"}`}>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
              {scenario.verdict === "ALLOW" ? <CheckCircle2 className="size-4" /> : <Ban className="size-4" />}
              Execution decision
            </div>
            <div className={`mt-4 text-5xl font-black tracking-tight ${complete ? (scenario.verdict === "ALLOW" ? "text-emerald-200" : "text-rose-200") : "text-zinc-700"}`}>
              {complete ? scenario.verdict : "PENDING"}
            </div>
            <p className="mt-4 text-sm leading-6 text-zinc-400">
              {complete ? scenario.decisionReason : "The action has not crossed the execution boundary."}
            </p>

            {complete && (
              <div className="mt-6 rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Synthetic signed receipt</div>
                  <ArrowRight className="size-4 text-zinc-600" />
                </div>
                <div className="mt-3 font-mono text-xs leading-6 text-zinc-300">
                  <div>receipt_id: {scenario.receipt.receiptId}</div>
                  <div>device: {scenario.receipt.deviceDigest}</div>
                  <div>action: {scenario.receipt.actionDigest}</div>
                  <div>policy: {scenario.receipt.policyVersion}</div>
                  <div>outcome: {scenario.receipt.executionOutcome}</div>
                  <div className="break-all">chain_hash: {scenario.receipt.chainHash}</div>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="rounded-3xl border border-amber-300/20 bg-amber-300/[0.045] p-6 md:p-8">
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-200">What the example proves</div>
          <h2 className="mt-2 text-2xl font-semibold text-zinc-100 md:text-3xl">
            Attribution must reach the execution boundary.
          </h2>
          <p className="mt-3 max-w-5xl text-sm leading-7 text-zinc-400 md:text-base">
            A valid certificate proves which device presented itself. It does not prove that the device is in an approved state,
            that the actor has authority for this action, or that the requested destination is admissible. The execution receipt
            binds all of these facts to what was actually released or blocked.
          </p>
          <p className="mt-4 text-xs text-zinc-600">
            Deterministic synthetic simulation. No live device, network, credential or production action is used.
          </p>
        </section>
      </div>
    </div>
  );
}
