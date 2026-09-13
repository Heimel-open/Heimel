import { useMemo, useState } from 'react'
import {
  ArrowRight,
  BrainCircuit,
  Building2,
  CalendarDays,
  Check,
  Cpu,
  Mail,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  UserRound,
  X,
  Zap,
} from 'lucide-react'
import {
  DEFAULT_ORG_INTENT,
  DEFAULT_PERSON_INTENT,
  derivePeaceDemoRun,
  type PeaceDemoRun,
  type PeaceDemoStepStatus,
  type PeaceDomainKind,
} from '@/lib/peaceCapabilityDemo'

const workers = ['Claude', 'Qwen', 'Gemini'] as const
const computes = ['Local NPU', 'ZeroGPU', 'Cloud GPU'] as const

const statusClass: Record<PeaceDemoStepStatus, string> = {
  PASS: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200',
  CANDIDATE: 'border-sky-400/30 bg-sky-400/10 text-sky-200',
  DENY: 'border-rose-400/30 bg-rose-400/10 text-rose-200',
  EFFECT: 'border-violet-400/30 bg-violet-400/10 text-violet-200',
  RECEIPT: 'border-amber-400/30 bg-amber-400/10 text-amber-200',
}

function cycle<T extends readonly string[]>(items: T, current: T[number]): T[number] {
  const index = items.indexOf(current)
  return items[(index + 1) % items.length]
}

function CapabilityPill({ label }: { label: string }) {
  const icon = label.includes('Mail') ? (
    <Mail className="h-4 w-4" />
  ) : label.includes('Calendar') ? (
    <CalendarDays className="h-4 w-4" />
  ) : label.includes('NPU') || label.includes('GPU') || label.includes('ZeroGPU') ? (
    <Cpu className="h-4 w-4" />
  ) : label === 'Claude' || label === 'Qwen' || label === 'Gemini' ? (
    <BrainCircuit className="h-4 w-4" />
  ) : (
    <Zap className="h-4 w-4" />
  )

  return (
    <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-zinc-200">
      <span className="text-zinc-400">{icon}</span>
      {label}
    </div>
  )
}

export default function PeaceCapabilityDemo() {
  const [domain, setDomain] = useState<PeaceDomainKind>('PERSON')
  const [intent, setIntent] = useState(DEFAULT_PERSON_INTENT)
  const [worker, setWorker] = useState<(typeof workers)[number]>('Claude')
  const [compute, setCompute] = useState<(typeof computes)[number]>('ZeroGPU')
  const [revoked, setRevoked] = useState(false)
  const [activeRun, setActiveRun] = useState<PeaceDemoRun | null>(null)
  const [visibleSteps, setVisibleSteps] = useState(0)
  const [swapNote, setSwapNote] = useState('')

  const preview = useMemo(
    () =>
      derivePeaceDemoRun({
        domain,
        intent,
        workerProvider: worker,
        computeProvider: compute,
        authorityFresh: !revoked,
      }),
    [domain, intent, worker, compute, revoked],
  )

  const shownRun = activeRun ?? preview
  const runComplete = activeRun !== null && visibleSteps >= activeRun.steps.length

  const selectDomain = (next: PeaceDomainKind) => {
    setDomain(next)
    setIntent(next === 'PERSON' ? DEFAULT_PERSON_INTENT : DEFAULT_ORG_INTENT)
    setActiveRun(null)
    setVisibleSteps(0)
    setSwapNote('Same PEACE semantics. Different sovereign domain.')
  }

  const swapWorker = () => {
    const next = cycle(workers, worker)
    setWorker(next)
    setActiveRun(null)
    setVisibleSteps(0)
    setSwapNote(`Intelligence changed: ${worker} → ${next}. Sovereign state did not move.`)
  }

  const swapCompute = () => {
    const next = cycle(computes, compute)
    setCompute(next)
    setActiveRun(null)
    setVisibleSteps(0)
    setSwapNote(`Compute changed: ${compute} → ${next}. Authority did not move.`)
  }

  const runDemo = () => {
    const run = derivePeaceDemoRun({
      domain,
      intent,
      workerProvider: worker,
      computeProvider: compute,
      authorityFresh: !revoked,
    })
    setActiveRun(run)
    setVisibleSteps(0)
    setSwapNote('')

    run.steps.forEach((_, index) => {
      window.setTimeout(() => setVisibleSteps(index + 1), 420 * (index + 1))
    })
  }

  const stateRoot = runComplete ? shownRun.stateRootAfter : shownRun.stateRootBefore

  return (
    <main className="min-h-screen bg-[#05070b] text-zinc-100">
      <div className="mx-auto max-w-7xl px-5 py-8 md:px-8 md:py-12">
        <header className="mb-10 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.28em] text-emerald-300">
              <ShieldCheck className="h-4 w-4" /> PEACE Protocol
            </div>
            <h1 className="max-w-4xl text-4xl font-semibold tracking-tight text-white md:text-6xl">
              You do not move between digital systems.
              <span className="block text-zinc-500">Digital systems connect to you.</span>
            </h1>
          </div>
          <div className="max-w-sm text-sm leading-6 text-zinc-400">
            <strong className="font-medium text-zinc-200">Bring your capability.</strong> The person or organisation brings the authority.
          </div>
        </header>

        <section className="mb-6 grid gap-3 rounded-2xl border border-white/10 bg-white/[0.025] p-2 md:grid-cols-2">
          <button
            type="button"
            onClick={() => selectDomain('PERSON')}
            className={`flex items-center gap-4 rounded-xl p-4 text-left transition ${
              domain === 'PERSON' ? 'bg-white text-black' : 'text-zinc-400 hover:bg-white/[0.04]'
            }`}
          >
            <UserRound className="h-5 w-5" />
            <span>
              <span className="block text-sm font-semibold">Person</span>
              <span className={`block text-xs ${domain === 'PERSON' ? 'text-zinc-600' : 'text-zinc-500'}`}>
                Your sovereign state persists.
              </span>
            </span>
          </button>
          <button
            type="button"
            onClick={() => selectDomain('ORGANISATION')}
            className={`flex items-center gap-4 rounded-xl p-4 text-left transition ${
              domain === 'ORGANISATION' ? 'bg-white text-black' : 'text-zinc-400 hover:bg-white/[0.04]'
            }`}
          >
            <Building2 className="h-5 w-5" />
            <span>
              <span className="block text-sm font-semibold">Organisation</span>
              <span className={`block text-xs ${domain === 'ORGANISATION' ? 'text-zinc-600' : 'text-zinc-500'}`}>
                Same model. Humans and AI are governed actors.
              </span>
            </span>
          </button>
        </section>

        <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
          <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 md:p-7">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-zinc-500">Intent</p>
                <h2 className="mt-2 text-xl font-semibold text-white">Say what you want. Not which app to open.</h2>
              </div>
              <Sparkles className="h-5 w-5 text-zinc-600" />
            </div>

            <textarea
              value={intent}
              onChange={(event) => {
                setIntent(event.target.value)
                setActiveRun(null)
                setVisibleSteps(0)
              }}
              className="min-h-28 w-full resize-none rounded-2xl border border-white/10 bg-black/30 p-4 text-base leading-7 text-white outline-none transition placeholder:text-zinc-600 focus:border-white/25"
            />

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={swapWorker}
                className="group rounded-2xl border border-white/10 bg-white/[0.035] p-4 text-left transition hover:bg-white/[0.07]"
              >
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.16em] text-zinc-500">
                  Intelligence <RefreshCw className="h-3.5 w-3.5 transition group-hover:rotate-90" />
                </div>
                <div className="mt-2 flex items-center gap-2 text-lg font-medium text-white">
                  <BrainCircuit className="h-4 w-4 text-zinc-400" /> {worker}
                </div>
              </button>
              <button
                type="button"
                onClick={swapCompute}
                className="group rounded-2xl border border-white/10 bg-white/[0.035] p-4 text-left transition hover:bg-white/[0.07]"
              >
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.16em] text-zinc-500">
                  Compute <RefreshCw className="h-3.5 w-3.5 transition group-hover:rotate-90" />
                </div>
                <div className="mt-2 flex items-center gap-2 text-lg font-medium text-white">
                  <Cpu className="h-4 w-4 text-zinc-400" /> {compute}
                </div>
              </button>
            </div>

            {swapNote && (
              <div className="mt-3 rounded-xl border border-sky-400/15 bg-sky-400/[0.06] px-4 py-3 text-sm text-sky-100">
                {swapNote}
              </div>
            )}

            <label className="mt-5 flex cursor-pointer items-center justify-between gap-4 rounded-2xl border border-white/10 bg-black/20 p-4">
              <div>
                <div className="text-sm font-medium text-zinc-200">Revoke authority before effect</div>
                <div className="mt-1 text-xs text-zinc-500">Shows why candidate ≠ consequence.</div>
              </div>
              <input
                type="checkbox"
                checked={revoked}
                onChange={(event) => {
                  setRevoked(event.target.checked)
                  setActiveRun(null)
                  setVisibleSteps(0)
                }}
                className="h-5 w-5 accent-white"
              />
            </label>

            <button
              type="button"
              onClick={runDemo}
              disabled={!intent.trim()}
              className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-white px-5 py-4 text-sm font-semibold text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Run through PEACE <ArrowRight className="h-4 w-4" />
            </button>
          </section>

          <section className="rounded-3xl border border-emerald-300/15 bg-emerald-300/[0.035] p-5 md:p-7">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-emerald-300/70">Persistent domain</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">{shownRun.domainLabel}</h2>
              </div>
              <div className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-xs font-medium text-emerald-200">
                PERSISTS
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.16em] text-zinc-500">Authority root</div>
                <div className="mt-2 text-sm font-medium text-zinc-200">
                  {domain === 'PERSON' ? 'Logical principal' : 'Organisation mandate'}
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.16em] text-zinc-500">Current state</div>
                <div className="mt-2 font-mono text-sm text-zinc-200">{stateRoot}</div>
              </div>
            </div>

            <div className="mt-6">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-[0.2em] text-zinc-500">Attached capabilities</span>
                <span className="text-xs text-zinc-600">replaceable</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {shownRun.capabilities.map((capability) => (
                  <CapabilityPill key={capability} label={capability} />
                ))}
              </div>
            </div>

            <div className="mt-7 rounded-2xl border border-white/10 bg-black/25 p-5">
              <div className="text-xs uppercase tracking-[0.16em] text-zinc-500">The inversion</div>
              <div className="mt-3 text-lg font-medium leading-7 text-white">
                The capability can change. The domain does not move with it.
              </div>
            </div>
          </section>
        </div>

        <section className="mt-6 rounded-3xl border border-white/10 bg-white/[0.025] p-5 md:p-7">
          <div className="mb-6 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-zinc-500">Consequence path</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">Intelligence is free. Consequence is governed.</h2>
            </div>
            <div className="text-xs text-zinc-500">proposal ≠ decision · compute ≠ authority · evidence ≠ state</div>
          </div>

          <div className="grid gap-3 lg:grid-cols-7">
            {shownRun.steps.map((step, index) => {
              const visible = activeRun === null ? false : index < visibleSteps
              const status = visible ? step.status : 'PASS'
              return (
                <div
                  key={step.id}
                  className={`min-h-36 rounded-2xl border p-4 transition-all duration-300 ${
                    visible ? statusClass[status] : 'border-white/8 bg-white/[0.02] text-zinc-600'
                  }`}
                >
                  <div className="mb-5 flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold uppercase tracking-[0.14em]">{visible ? step.status : `0${index + 1}`}</span>
                    {visible && (step.status === 'DENY' ? <X className="h-4 w-4" /> : <Check className="h-4 w-4" />)}
                  </div>
                  <div className={`text-sm font-semibold ${visible ? 'text-current' : 'text-zinc-500'}`}>{step.label}</div>
                  {visible && <div className="mt-3 text-xs leading-5 opacity-75">{step.detail}</div>}
                </div>
              )
            })}
          </div>

          {runComplete && (
            <div
              className={`mt-5 rounded-2xl border p-5 ${
                revoked ? 'border-rose-400/20 bg-rose-400/[0.06]' : 'border-emerald-400/20 bg-emerald-400/[0.06]'
              }`}
            >
              <div className="flex items-start gap-3">
                {revoked ? <X className="mt-0.5 h-5 w-5 text-rose-300" /> : <ShieldCheck className="mt-0.5 h-5 w-5 text-emerald-300" />}
                <div>
                  <div className="font-medium text-white">{shownRun.consequence}</div>
                  <div className="mt-2 text-sm text-zinc-400">
                    {revoked
                      ? 'The worker was still useful. Its proposal simply never became authority.'
                      : `State advanced ${shownRun.stateRootBefore} → ${shownRun.stateRootAfter}. The worker and compute remain replaceable.`}
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>

        <footer className="mt-8 flex flex-col gap-3 border-t border-white/10 pt-6 text-sm text-zinc-500 md:flex-row md:items-center md:justify-between">
          <span>PEACE — Personal Execution, Authority & Compute Environment</span>
          <span className="font-medium text-zinc-300">Your Sovereign State.</span>
        </footer>
      </div>
    </main>
  )
}
