import { useMemo, useState } from 'react'
import {
  ArrowRight,
  BrainCircuit,
  Check,
  Cpu,
  Database,
  LockKeyhole,
  RefreshCw,
  Route,
  ShieldCheck,
  Sparkles,
  X,
  Zap,
} from 'lucide-react'
import {
  ZERO_GPU_DEMO_INTENT,
  deriveZeroGpuDemoRun,
  type ZeroGpuDemoProvider,
  type ZeroGpuDemoStatus,
  type ZeroGpuDemoWorker,
} from '@/lib/peaceZeroGpuDemo'

const workers: ZeroGpuDemoWorker[] = ['Qwen', 'Claude', 'Gemini']
const providers: ZeroGpuDemoProvider[] = ['ZeroGPU', 'Local GPU', 'Cloud GPU']

const statusClass: Record<ZeroGpuDemoStatus, string> = {
  PASS: 'border-emerald-300/25 bg-emerald-300/[0.08] text-emerald-100',
  CANDIDATE: 'border-sky-300/25 bg-sky-300/[0.08] text-sky-100',
  DENY: 'border-rose-300/25 bg-rose-300/[0.08] text-rose-100',
  EFFECT: 'border-violet-300/25 bg-violet-300/[0.08] text-violet-100',
  RECEIPT: 'border-amber-300/25 bg-amber-300/[0.08] text-amber-100',
  REROUTE: 'border-cyan-300/25 bg-cyan-300/[0.08] text-cyan-100',
}

function nextOf<T>(items: T[], current: T): T {
  const index = items.indexOf(current)
  return items[(index + 1) % items.length]
}

export default function PeaceZeroGpuDemo() {
  const [worker, setWorker] = useState<ZeroGpuDemoWorker>('Qwen')
  const [provider, setProvider] = useState<ZeroGpuDemoProvider>('ZeroGPU')
  const [providerAvailable, setProviderAvailable] = useState(true)
  const [authorityFresh, setAuthorityFresh] = useState(true)
  const [visibleSteps, setVisibleSteps] = useState(0)
  const [running, setRunning] = useState(false)
  const [swapMessage, setSwapMessage] = useState('')

  const run = useMemo(
    () =>
      deriveZeroGpuDemoRun({
        requestedProvider: provider,
        worker,
        providerAvailable,
        authorityFresh,
      }),
    [provider, worker, providerAvailable, authorityFresh],
  )

  const runDemo = () => {
    setVisibleSteps(0)
    setRunning(true)
    setSwapMessage('')
    run.steps.forEach((_, index) => {
      window.setTimeout(() => {
        setVisibleSteps(index + 1)
        if (index === run.steps.length - 1) setRunning(false)
      }, 460 * (index + 1))
    })
  }

  const swapWorker = () => {
    const next = nextOf(workers, worker)
    setWorker(next)
    setVisibleSteps(0)
    setRunning(false)
    setSwapMessage(`Intelligence changed: ${worker} → ${next}. Authority did not move.`)
  }

  const swapProvider = () => {
    const next = nextOf(providers, provider)
    setProvider(next)
    setProviderAvailable(true)
    setVisibleSteps(0)
    setRunning(false)
    setSwapMessage(`Compute changed: ${provider} → ${next}. Sovereign state did not move.`)
  }

  const complete = visibleSteps >= run.steps.length

  return (
    <main className="min-h-screen bg-[#080807] text-[#f4efe6]">
      <div className="mx-auto max-w-7xl px-5 py-8 md:px-8 md:py-12">
        <header className="mb-10 border-b border-[#d9c8a7]/15 pb-8">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div className="rounded-full border border-[#d9c8a7]/25 bg-[#d9c8a7]/[0.07] px-3 py-1.5 text-xs font-medium uppercase tracking-[0.18em] text-[#e8dcc4]">
              Private first look for Maddy
            </div>
            <div className="flex items-center gap-2 text-xs text-[#9d9588]">
              <LockKeyhole className="h-3.5 w-3.5" /> Architecture demo · simulated capability adapter
            </div>
          </div>

          <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
            <div>
              <div className="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-[#bda77c]">PEACE × open compute</div>
              <h1 className="max-w-4xl text-4xl font-semibold tracking-[-0.04em] text-white md:text-6xl">
                ZeroGPU brings compute.
                <span className="block text-[#8e887e]">You keep the state and authority.</span>
              </h1>
            </div>
            <div className="rounded-2xl border border-[#d9c8a7]/15 bg-[#d9c8a7]/[0.04] p-5 text-sm leading-6 text-[#b9b1a4]">
              <strong className="text-[#f4efe6]">The thesis:</strong> open compute becomes genuinely replaceable when identity, continuity and consequence authority do not live with the compute provider.
            </div>
          </div>
        </header>

        <section className="mb-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-[#d9c8a7]/15 bg-[#d9c8a7]/[0.03] p-5">
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-[#8e887e]">
              <Database className="h-4 w-4" /> Sovereign domain
            </div>
            <div className="mt-3 font-mono text-sm text-[#f4efe6]">{run.stateRootBefore}</div>
            <div className="mt-2 text-xs text-[#777168]">Persists across worker and compute swaps</div>
          </div>
          <div className="rounded-2xl border border-[#d9c8a7]/15 bg-[#d9c8a7]/[0.03] p-5">
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-[#8e887e]">
              <ShieldCheck className="h-4 w-4" /> Authority root
            </div>
            <div className="mt-3 font-mono text-sm text-[#f4efe6]">{run.authorityRoot}</div>
            <div className="mt-2 text-xs text-[#777168]">Never supplied by the compute route</div>
          </div>
          <div className="rounded-2xl border border-[#bda77c]/25 bg-[#bda77c]/[0.07] p-5">
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-[#bda77c]">
              <Cpu className="h-4 w-4" /> Attached capability
            </div>
            <div className="mt-3 text-xl font-semibold text-white">{run.effectiveProvider}</div>
            <div className="mt-2 text-xs text-[#9d9588]">Capacity, not constitutional control</div>
          </div>
        </section>

        <div className="grid gap-6 lg:grid-cols-[0.92fr_1.08fr]">
          <section className="rounded-3xl border border-white/10 bg-white/[0.025] p-5 md:p-7">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <div className="text-xs font-medium uppercase tracking-[0.18em] text-[#8e887e]">One intent</div>
                <h2 className="mt-2 text-2xl font-semibold text-white">The user asks for an outcome, not a provider.</h2>
              </div>
              <Sparkles className="h-5 w-5 text-[#8e887e]" />
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/25 p-4 text-sm leading-6 text-[#ddd5c8]">
              “{ZERO_GPU_DEMO_INTENT}”
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={swapWorker}
                className="group rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-left transition hover:bg-white/[0.06]"
              >
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.15em] text-[#777168]">
                  Intelligence <RefreshCw className="h-3.5 w-3.5 transition group-hover:rotate-90" />
                </div>
                <div className="mt-2 flex items-center gap-2 text-lg font-medium text-white">
                  <BrainCircuit className="h-4 w-4 text-[#9d9588]" /> {worker}
                </div>
              </button>
              <button
                type="button"
                onClick={swapProvider}
                className="group rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-left transition hover:bg-white/[0.06]"
              >
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.15em] text-[#777168]">
                  Compute <RefreshCw className="h-3.5 w-3.5 transition group-hover:rotate-90" />
                </div>
                <div className="mt-2 flex items-center gap-2 text-lg font-medium text-white">
                  <Cpu className="h-4 w-4 text-[#9d9588]" /> {provider}
                </div>
              </button>
            </div>

            {swapMessage && (
              <div className="mt-3 rounded-xl border border-cyan-300/15 bg-cyan-300/[0.05] px-4 py-3 text-sm text-cyan-100">
                {swapMessage}
              </div>
            )}

            <div className="mt-5 space-y-3">
              <label className="flex cursor-pointer items-center justify-between gap-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                <div>
                  <div className="text-sm font-medium text-[#e8e0d3]">Make compute provider disappear</div>
                  <div className="mt-1 text-xs text-[#777168]">PEACE reroutes without moving the sovereign roots.</div>
                </div>
                <input
                  type="checkbox"
                  checked={!providerAvailable}
                  onChange={(event) => {
                    setProviderAvailable(!event.target.checked)
                    setVisibleSteps(0)
                  }}
                  className="h-5 w-5 accent-[#d9c8a7]"
                />
              </label>

              <label className="flex cursor-pointer items-center justify-between gap-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                <div>
                  <div className="text-sm font-medium text-[#e8e0d3]">Revoke authority before publish</div>
                  <div className="mt-1 text-xs text-[#777168]">The compute result remains useful, but never becomes a decision.</div>
                </div>
                <input
                  type="checkbox"
                  checked={!authorityFresh}
                  onChange={(event) => {
                    setAuthorityFresh(!event.target.checked)
                    setVisibleSteps(0)
                  }}
                  className="h-5 w-5 accent-[#d9c8a7]"
                />
              </label>
            </div>

            <button
              type="button"
              onClick={runDemo}
              disabled={running}
              className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-[#eadfc9] px-5 py-4 text-sm font-semibold text-[#17130e] transition hover:bg-[#f5ead5] disabled:opacity-60"
            >
              {running ? 'Running…' : 'Run through PEACE'} <ArrowRight className="h-4 w-4" />
            </button>
          </section>

          <section className="rounded-3xl border border-[#d9c8a7]/15 bg-[#d9c8a7]/[0.025] p-5 md:p-7">
            <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <div className="text-xs font-medium uppercase tracking-[0.18em] text-[#8e887e]">Capability path</div>
                <h2 className="mt-2 text-2xl font-semibold text-white">Compute can move. Authority cannot.</h2>
              </div>
              <div className="text-xs text-[#777168]">candidate ≠ decision · route ≠ authority</div>
            </div>

            <div className="space-y-3">
              {run.steps.map((step, index) => {
                const visible = index < visibleSteps
                return (
                  <div
                    key={step.id}
                    className={`grid min-h-20 grid-cols-[40px_1fr_auto] items-start gap-3 rounded-2xl border p-4 transition-all duration-300 ${
                      visible ? statusClass[step.status] : 'border-white/[0.07] bg-white/[0.015] text-[#635e56]'
                    }`}
                  >
                    <div className="flex h-8 w-8 items-center justify-center rounded-full border border-current/20 text-xs font-semibold">
                      {visible ? (step.status === 'DENY' ? <X className="h-4 w-4" /> : <Check className="h-4 w-4" />) : index + 1}
                    </div>
                    <div>
                      <div className="text-sm font-semibold">{step.label}</div>
                      {visible && <div className="mt-1.5 text-xs leading-5 opacity-75">{step.detail}</div>}
                    </div>
                    {visible && <div className="text-[10px] font-semibold uppercase tracking-[0.12em] opacity-70">{step.status}</div>}
                  </div>
                )
              })}
            </div>

            {complete && (
              <div className={`mt-5 rounded-2xl border p-5 ${authorityFresh ? 'border-emerald-300/20 bg-emerald-300/[0.05]' : 'border-rose-300/20 bg-rose-300/[0.05]'}`}>
                <div className="flex items-start gap-3">
                  {authorityFresh ? <ShieldCheck className="mt-0.5 h-5 w-5 text-emerald-200" /> : <X className="mt-0.5 h-5 w-5 text-rose-200" />}
                  <div>
                    <div className="font-medium text-white">{run.consequence}</div>
                    <div className="mt-2 text-sm text-[#9d9588]">
                      {authorityFresh
                        ? `${run.stateRootBefore} → ${run.stateRootAfter}. ${run.effectiveProvider} remains a replaceable capability.`
                        : `${run.stateRootBefore} unchanged. The worker produced output; PEACE refused consequence.`}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>

        <section className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
            <Route className="h-5 w-5 text-[#bda77c]" />
            <div className="mt-4 font-semibold text-white">Bring your capability.</div>
            <div className="mt-2 text-sm leading-6 text-[#8e887e]">ZeroGPU can supply capacity without becoming the user’s platform.</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
            <ShieldCheck className="h-5 w-5 text-[#bda77c]" />
            <div className="mt-4 font-semibold text-white">The domain brings authority.</div>
            <div className="mt-2 text-sm leading-6 text-[#8e887e]">Standing and authority remain external to the worker and compute substrate.</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
            <Zap className="h-5 w-5 text-[#bda77c]" />
            <div className="mt-4 font-semibold text-white">Open compute becomes easier to trust.</div>
            <div className="mt-2 text-sm leading-6 text-[#8e887e]">A provider can disappear, change or be compromised without inheriting constitutional control.</div>
          </div>
        </section>

        <footer className="mt-8 flex flex-col gap-3 border-t border-[#d9c8a7]/15 pt-6 text-xs text-[#777168] md:flex-row md:items-center md:justify-between">
          <span>PEACE — Personal Execution, Authority & Compute Environment</span>
          <span>Private architecture exploration · no ZeroGPU integration or partnership implied</span>
        </footer>
      </div>
    </main>
  )
}
