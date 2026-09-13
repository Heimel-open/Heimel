import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BadgeCheck,
  Ban,
  CheckCircle2,
  Clock3,
  Maximize2,
  Pause,
  Play,
  ReceiptText,
  RotateCcw,
  ShieldCheck,
  Square,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import {
  DEMO_SCENARIOS,
  PIPELINE_STAGES,
  SIMULATION_DISCLOSURE,
  getActiveStageId,
  getScenarioDurationMs,
  getStageVerdict,
  getVisibleEvents,
  type DemoScenario,
  type DemoVerdict,
  type PipelineStageId,
  type ScenarioId,
} from "./valoLiveDemoData";

const FRAME_MS = 250;

const accentClasses: Record<DemoScenario["accent"], string> = {
  green: "border-emerald-500/50 bg-emerald-500/10 text-emerald-200",
  red: "border-red-500/50 bg-red-500/10 text-red-200",
  amber: "border-amber-500/50 bg-amber-500/10 text-amber-200",
};

const verdictClasses: Record<DemoVerdict | "PENDING", string> = {
  ALLOW: "border-emerald-500/50 bg-emerald-500/15 text-emerald-200",
  DENY: "border-red-500/50 bg-red-500/15 text-red-200",
  PENDING: "border-zinc-700 bg-zinc-900 text-zinc-500",
};

const evidenceClasses = {
  neutral: "border-zinc-700 bg-zinc-900 text-zinc-200",
  pass: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
  warn: "border-amber-500/40 bg-amber-500/10 text-amber-200",
  fail: "border-red-500/40 bg-red-500/10 text-red-200",
};

function VerdictIcon({ verdict }: { verdict: DemoVerdict | "PENDING" }) {
  if (verdict === "ALLOW") {
    return <CheckCircle2 className="size-4" />;
  }
  if (verdict === "DENY") {
    return <Ban className="size-4" />;
  }
  return <Clock3 className="size-4" />;
}

function formatTime(ms: number) {
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function LiveSystemDemo() {
  const [scenarioId, setScenarioId] = useState<ScenarioId>(DEMO_SCENARIOS[1].id);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [mediaMode, setMediaMode] = useState(false);

  const scenario = useMemo(
    () => DEMO_SCENARIOS.find((candidate) => candidate.id === scenarioId) ?? DEMO_SCENARIOS[0],
    [scenarioId],
  );
  const durationMs = getScenarioDurationMs(scenario);
  const visibleEvents = getVisibleEvents(scenario, elapsedMs);
  const activeStageId = getActiveStageId(scenario, elapsedMs);
  const progress = Math.min(100, Math.round((elapsedMs / durationMs) * 100));

  useEffect(() => {
    if (!isPlaying) {
      return;
    }

    const interval = window.setInterval(() => {
      setElapsedMs((current) => {
        if (current >= durationMs) {
          setIsPlaying(false);
          return durationMs;
        }
        return Math.min(durationMs, current + FRAME_MS);
      });
    }, FRAME_MS);

    return () => window.clearInterval(interval);
  }, [durationMs, isPlaying]);

  function resetPlayback() {
    setElapsedMs(0);
    setIsPlaying(true);
  }

  function selectScenario(value: string) {
    setScenarioId(value as ScenarioId);
    setElapsedMs(0);
    setIsPlaying(true);
  }

  function toggleMediaMode() {
    setMediaMode((current) => !current);
  }

  function requestFullscreen() {
    const root = document.documentElement;
    if (!document.fullscreenElement && root.requestFullscreen) {
      void root.requestFullscreen();
      return;
    }
    if (document.fullscreenElement && document.exitFullscreen) {
      void document.exitFullscreen();
    }
  }

  return (
    <div
      className={cn(
        "min-h-full overflow-auto bg-[#0b0d0e] text-zinc-100",
        mediaMode && "fixed inset-0 z-50 min-h-screen",
      )}
    >
      <header className="sticky top-0 z-20 border-b border-zinc-800 bg-[#0b0d0e]/95 px-4 py-3 backdrop-blur md:px-6">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <Badge className="rounded-md border-amber-500/40 bg-amber-500/10 px-2 py-1 text-amber-200">
              {SIMULATION_DISCLOSURE}
            </Badge>
            <div>
              <h1 className="text-xl font-semibold tracking-normal md:text-2xl">
                VALO live system simulation
              </h1>
              <p className="max-w-4xl text-sm text-zinc-400">
                Deterministic demo for showing how Validator, VAIG, REHT, Core, and RACS handle consequential actions.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-md border-zinc-700 bg-zinc-900 text-zinc-100 hover:bg-zinc-800"
              onClick={() => setIsPlaying((current) => !current)}
            >
              {isPlaying ? <Pause className="size-4" /> : <Play className="size-4" />}
              {isPlaying ? "Pause" : "Play"}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-md border-zinc-700 bg-zinc-900 text-zinc-100 hover:bg-zinc-800"
              onClick={resetPlayback}
            >
              <RotateCcw className="size-4" />
              Reset
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-md border-zinc-700 bg-zinc-900 text-zinc-100 hover:bg-zinc-800"
              onClick={toggleMediaMode}
            >
              <Square className="size-4" />
              Media
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-md border-zinc-700 bg-zinc-900 text-zinc-100 hover:bg-zinc-800"
              onClick={requestFullscreen}
            >
              <Maximize2 className="size-4" />
              Fullscreen
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-[1760px] flex-col gap-4 p-4 md:p-6">
        <section className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)]">
          <div className="rounded-lg border border-zinc-800 bg-[#111415] p-4">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <Tabs value={scenario.id} onValueChange={selectScenario}>
                    <TabsList className="h-auto w-full flex-wrap rounded-md border border-zinc-800 bg-zinc-950 p-1 lg:w-fit">
                      {DEMO_SCENARIOS.map((item) => (
                        <TabsTrigger
                          key={item.id}
                          value={item.id}
                          className="rounded-md px-3 py-2 text-xs data-[state=active]:bg-zinc-800 data-[state=active]:text-white"
                        >
                          {item.shortTitle}
                        </TabsTrigger>
                      ))}
                    </TabsList>
                  </Tabs>
                  <h2 className="mt-4 text-2xl font-semibold tracking-normal md:text-4xl">
                    {scenario.title}
                  </h2>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-400">
                    {scenario.operatorIntent}
                  </p>
                </div>
                <div className={cn("flex min-w-[180px] items-center gap-2 rounded-lg border px-3 py-2", accentClasses[scenario.accent])}>
                  <VerdictIcon verdict={scenario.finalVerdict} />
                  <div>
                    <div className="text-xs uppercase text-current/70">Final verdict</div>
                    <div className="text-lg font-semibold">{scenario.finalVerdict}</div>
                  </div>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-6">
                {PIPELINE_STAGES.map((stage, index) => (
                  <PipelineNode
                    key={stage.id}
                    elapsedMs={elapsedMs}
                    isActive={activeStageId === stage.id}
                    scenario={scenario}
                    stageId={stage.id}
                    stageLabel={stage.label}
                    step={index + 1}
                  />
                ))}
              </div>

              <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
                <div className="mb-3 flex items-center justify-between gap-4">
                  <div className="text-sm font-medium text-zinc-200">Timeline</div>
                  <div className="font-mono text-xs text-zinc-500">
                    {formatTime(elapsedMs)} / {formatTime(durationMs)}
                  </div>
                </div>
                <Slider
                  value={[elapsedMs]}
                  min={0}
                  max={durationMs}
                  step={FRAME_MS}
                  onValueChange={([value]) => {
                    setElapsedMs(value ?? 0);
                    setIsPlaying(false);
                  }}
                />
                <div className="mt-3 h-1 rounded-full bg-zinc-800">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      scenario.finalVerdict === "ALLOW" ? "bg-emerald-400" : "bg-red-400",
                    )}
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <section className="rounded-lg border border-zinc-800 bg-[#111415]">
            <div className="border-b border-zinc-800 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <ReceiptText className="size-4 text-cyan-300" />
                RACS receipt
              </div>
              <p className="mt-1 text-sm text-zinc-400">{scenario.finalMessage}</p>
            </div>
            <div className="grid gap-3 p-4 text-sm">
              <ReceiptRow label="Receipt ID" value={scenario.receipt.id} />
              <ReceiptRow label="Bound action" value={scenario.receipt.boundAction} />
              <ReceiptRow label="Commit" value={scenario.receipt.commitSha} />
              <ReceiptRow label="State hash" value={scenario.receipt.stateHash} />
              <ReceiptRow label="Policy" value={scenario.receipt.policyVersion} />
              <div className={cn("flex items-center justify-between rounded-md border px-3 py-2", verdictClasses[scenario.receipt.decision])}>
                <span>Decision</span>
                <span className="font-semibold">{scenario.receipt.decision}</span>
              </div>
            </div>
          </section>
        </section>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(340px,0.6fr)]">
          <section className="rounded-lg border border-zinc-800 bg-[#111415]">
            <div className="border-b border-zinc-800 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <ShieldCheck className="size-4 text-emerald-300" />
                Event stream
              </div>
            </div>
            <ScrollArea className="h-[330px]">
              <div className="grid gap-3 p-4">
                {visibleEvents.map((event) => (
                  <div key={`${event.atMs}-${event.stage}`} className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="rounded-md border-zinc-700 font-mono text-zinc-400">
                          {formatTime(event.atMs)}
                        </Badge>
                        <span className="text-sm font-medium text-zinc-100">{event.title}</span>
                      </div>
                      {event.verdict ? (
                        <Badge className={cn("rounded-md border", verdictClasses[event.verdict])}>
                          {event.verdict}
                        </Badge>
                      ) : null}
                    </div>
                    <p className="mt-2 text-sm leading-6 text-zinc-400">{event.detail}</p>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </section>

          <section className="rounded-lg border border-zinc-800 bg-[#111415]">
            <div className="border-b border-zinc-800 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <AlertTriangle className="size-4 text-amber-300" />
                Evidence
              </div>
            </div>
            <div className="grid gap-3 p-4">
              {scenario.evidence.map((item) => (
                <div key={item.label} className={cn("rounded-md border px-3 py-2 text-sm", evidenceClasses[item.tone])}>
                  <div className="text-xs uppercase text-current/70">{item.label}</div>
                  <div className="mt-1 font-medium">{item.value}</div>
                </div>
              ))}
            </div>
          </section>
        </section>

        <section className="rounded-lg border border-zinc-800 bg-[#111415] p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <BadgeCheck className="size-4 text-cyan-300" />
            60-90 sec presenter script
          </div>
          <div className="grid gap-2 md:grid-cols-4">
            {scenario.presenterScript.map((line, index) => (
              <div key={line} className="rounded-md border border-zinc-800 bg-zinc-950 p-3 text-sm leading-6 text-zinc-300">
                <div className="mb-2 font-mono text-xs text-zinc-600">0{index + 1}</div>
                {line}
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function PipelineNode({
  elapsedMs,
  isActive,
  scenario,
  stageId,
  stageLabel,
  step,
}: {
  elapsedMs: number;
  isActive: boolean;
  scenario: DemoScenario;
  stageId: PipelineStageId;
  stageLabel: string;
  step: number;
}) {
  const verdict = getStageVerdict(scenario, stageId, elapsedMs);

  return (
    <div
      className={cn(
        "min-h-[126px] rounded-lg border p-3 transition-all",
        verdictClasses[verdict],
        isActive && "ring-2 ring-cyan-300/70",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs opacity-70">0{step}</span>
        <VerdictIcon verdict={verdict} />
      </div>
      <div className="mt-5 text-sm font-semibold">{stageLabel}</div>
      <div className="mt-2 text-xs uppercase opacity-70">{verdict}</div>
    </div>
  );
}

function ReceiptRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2">
      <div className="text-xs uppercase text-zinc-500">{label}</div>
      <div className="mt-1 break-all font-mono text-sm text-zinc-200">{value}</div>
    </div>
  );
}
