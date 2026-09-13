import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileCheck2,
  Fingerprint,
  HeartPulse,
  RefreshCw,
  ShieldCheck,
  UserRoundCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  DEMO_SCENARIOS,
  SIMULATION_DISCLOSURE,
  type ScenarioId,
} from "./liveSystemDemoData";

export default function LiveSystemDemo() {
  const [scenarioId, setScenarioId] = useState<ScenarioId>("evidence-unchanged");
  const scenario = useMemo(
    () => DEMO_SCENARIOS.find((item) => item.id === scenarioId) ?? DEMO_SCENARIOS[0],
    [scenarioId],
  );
  const changed = scenario.finalDecision === "STEP_UP";

  return (
    <div className="min-h-screen overflow-auto bg-[#07090a] text-zinc-100">
      <header className="border-b border-white/10 bg-black/20 px-5 py-4 backdrop-blur md:px-8">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-full border border-cyan-300/30 bg-cyan-300/10 font-semibold text-cyan-200">
              V
            </div>
            <div>
              <div className="font-semibold tracking-wide">VALO · REHT</div>
              <div className="text-xs text-zinc-500">Right before action</div>
            </div>
          </div>
          <div className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1.5 text-xs text-amber-200">
            {SIMULATION_DISCLOSURE}
          </div>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-[1440px] gap-8 px-5 py-8 md:px-8 md:py-12">
        <section className="grid items-end gap-6 lg:grid-cols-[minmax(0,1fr)_420px]">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/5 px-3 py-1.5 text-sm text-cyan-200">
              <HeartPulse className="size-4" />
              Philips patient monitoring · shadow pilot
            </div>
            <h1 className="max-w-4xl text-4xl font-semibold tracking-tight md:text-6xl">
              Keep the alarm. Verify the action.
            </h1>
            <p className="mt-5 max-w-3xl text-lg leading-8 text-zinc-400 md:text-xl">
              Philips detects and routes. VALO checks whether the evidence is still current at the exact moment the clinical workflow relies on it.
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-2">
            <div className="mb-2 px-2 pt-1 text-xs font-medium uppercase tracking-wide text-zinc-500">
              Change the patient state
            </div>
            <div className="grid grid-cols-2 gap-2">
              <ScenarioButton
                active={!changed}
                label="Still current"
                detail="No material change"
                onClick={() => setScenarioId("evidence-unchanged")}
              />
              <ScenarioButton
                active={changed}
                label="State changed"
                detail="New evidence exists"
                onClick={() => setScenarioId("newer-clinical-state")}
                warning
              />
            </div>
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-[#0d1011] p-5 md:p-7">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="text-sm font-medium text-zinc-400">Same Philips alert</div>
              <div className="mt-1 font-mono text-sm text-zinc-500">alert-1042 · encounter:demo-7f2a</div>
            </div>
            <div
              className={cn(
                "flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold",
                changed
                  ? "border-amber-400/40 bg-amber-400/10 text-amber-200"
                  : "border-emerald-400/40 bg-emerald-400/10 text-emerald-200",
              )}
            >
              {changed ? <AlertTriangle className="size-4" /> : <CheckCircle2 className="size-4" />}
              {scenario.finalDecision} · {scenario.observation}
            </div>
          </div>

          <div className="grid items-stretch gap-3 lg:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
            <FlowNode
              icon={<Activity className="size-5" />}
              owner="Philips"
              title="Detects and creates alert"
              detail="Existing EWS logic and monitoring stay authoritative."
              status="ALERT CREATED"
            />
            <FlowArrow />
            <FlowNode
              icon={<ShieldCheck className="size-5" />}
              owner="VALO / REHT"
              title="Checks the latest reality"
              detail="Freshness, continuity, context, quality and supersession."
              status={scenario.observation}
              warning={changed}
              active
            />
            <FlowArrow />
            <FlowNode
              icon={<UserRoundCheck className="size-5" />}
              owner="Clinical team"
              title={changed ? "Rechecks before relying" : "Continues with current alert"}
              detail="Human clinical authority remains final."
              status={changed ? "HUMAN RECHECK" : "ACKNOWLEDGED"}
              warning={changed}
            />
            <FlowArrow />
            <FlowNode
              icon={<Fingerprint className="size-5" />}
              owner="RACS receipt"
              title="Binds what happened"
              detail="Alert, evidence state, decision and acknowledgement are verifiable."
              status="VERIFIED"
            />
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-3">
            <ComparisonRow label="Alert" before="Created by Philips" after="Delivered unchanged" />
            <ComparisonRow
              label="Latest state"
              before="Original evidence at T0"
              after={changed ? "New measurement + changed context" : "No material change before T2"}
              warning={changed}
            />
            <ComparisonRow
              label="Next action"
              before="Workflow is about to rely on alert"
              after={changed ? "STEP_UP: review latest state" : "ALLOW: continue"}
              warning={changed}
            />
          </div>
        </section>

        <section>
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <div className="text-sm font-medium uppercase tracking-wide text-cyan-300">What Philips gets</div>
              <h2 className="mt-2 text-2xl font-semibold md:text-3xl">A control layer, not another monitoring platform</h2>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <OfferCard
              icon={<RefreshCw className="size-5" />}
              title="No replacement project"
              detail="Keep Philips monitoring, EWS, routing and clinical workflows. VALO fits at the reliance boundary."
            />
            <OfferCard
              icon={<ShieldCheck className="size-5" />}
              title="Shadow-first validation"
              detail="Start with historical or pseudonymous event exports. No alert suppression and no production control."
            />
            <OfferCard
              icon={<FileCheck2 className="size-5" />}
              title="Evidence for governance"
              detail="Produce deterministic reason codes and receipts for review, audit, incidents and improvement."
            />
          </div>
        </section>

        <section className="grid gap-5 rounded-3xl border border-cyan-300/20 bg-cyan-300/[0.055] p-6 md:grid-cols-[1fr_auto] md:items-center md:p-8">
          <div>
            <div className="text-sm font-medium text-cyan-200">Smallest credible pilot</div>
            <div className="mt-2 text-2xl font-semibold">One ward. One alert workflow. Shadow only.</div>
            <p className="mt-2 max-w-3xl leading-7 text-zinc-400">
              Reconstruct T0, T1 and T2, measure how often evidence or context changed before acknowledgement, and show every result with a verifiable receipt.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/25 px-5 py-4 text-right">
            <div className="text-xs uppercase tracking-wide text-zinc-500">Pilot output</div>
            <div className="mt-1 font-semibold text-cyan-200">Observed risk · reason · receipt</div>
          </div>
        </section>
      </main>
    </div>
  );
}

function ScenarioButton({
  active,
  label,
  detail,
  onClick,
  warning = false,
}: {
  active: boolean;
  label: string;
  detail: string;
  onClick: () => void;
  warning?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-xl border px-3 py-3 text-left transition",
        active && warning && "border-amber-400/50 bg-amber-400/10",
        active && !warning && "border-emerald-400/50 bg-emerald-400/10",
        !active && "border-white/10 bg-black/20 hover:border-white/20",
      )}
    >
      <div className="text-sm font-semibold">{label}</div>
      <div className="mt-1 text-xs text-zinc-500">{detail}</div>
    </button>
  );
}

function FlowNode({
  icon,
  owner,
  title,
  detail,
  status,
  warning = false,
  active = false,
}: {
  icon: React.ReactNode;
  owner: string;
  title: string;
  detail: string;
  status: string;
  warning?: boolean;
  active?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex min-h-[220px] flex-col rounded-2xl border p-5",
        warning ? "border-amber-400/30 bg-amber-400/[0.055]" : "border-white/10 bg-black/20",
        active && !warning && "border-cyan-300/30 bg-cyan-300/[0.045]",
      )}
    >
      <div className={cn("flex size-10 items-center justify-center rounded-xl", warning ? "bg-amber-400/10 text-amber-200" : "bg-cyan-300/10 text-cyan-200")}>
        {icon}
      </div>
      <div className="mt-5 text-xs font-medium uppercase tracking-wide text-zinc-500">{owner}</div>
      <div className="mt-2 text-lg font-semibold">{title}</div>
      <div className="mt-2 text-sm leading-6 text-zinc-500">{detail}</div>
      <div className={cn("mt-auto pt-5 text-xs font-semibold", warning ? "text-amber-200" : "text-emerald-300")}>
        {status}
      </div>
    </div>
  );
}

function FlowArrow() {
  return (
    <div className="flex items-center justify-center py-1 text-zinc-700 lg:py-0">
      <ArrowRight className="size-5 rotate-90 lg:rotate-0" />
    </div>
  );
}

function ComparisonRow({
  label,
  before,
  after,
  warning = false,
}: {
  label: string;
  before: string;
  after: string;
  warning?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-zinc-600">{label}</div>
      <div className="mt-3 text-sm text-zinc-500">{before}</div>
      <div className="my-2 h-px bg-white/10" />
      <div className={cn("text-sm font-medium", warning ? "text-amber-200" : "text-zinc-200")}>{after}</div>
    </div>
  );
}

function OfferCard({ icon, title, detail }: { icon: React.ReactNode; title: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
      <div className="flex size-10 items-center justify-center rounded-xl bg-cyan-300/10 text-cyan-200">{icon}</div>
      <div className="mt-5 text-lg font-semibold">{title}</div>
      <p className="mt-2 leading-7 text-zinc-500">{detail}</p>
    </div>
  );
}
