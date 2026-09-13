import { BadgeCheck, Clock3, MessageSquareQuote } from 'lucide-react'
import { PRESENTER_CONTRACT } from '@/lib/enablement'

export function PresenterContractPanel({ compact = false }: { compact?: boolean }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-[#0d1011] p-6 md:p-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">Presenter contract</div>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">One platform story, every time.</h2>
          <p className="mt-3 max-w-4xl text-sm leading-6 text-zinc-500 md:text-base">
            The script fixes component roles, product boundaries and sequence while allowing the business scenario to change.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-xs text-zinc-400">
            <BadgeCheck className="size-4 text-emerald-300" />
            {PRESENTER_CONTRACT.id} v{PRESENTER_CONTRACT.version}
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-xs text-zinc-400">
            <Clock3 className="size-4 text-cyan-300" />
            {PRESENTER_CONTRACT.targetDurationSeconds} seconds
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-cyan-300/25 bg-cyan-300/[0.055] p-5">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-cyan-200">
          <MessageSquareQuote className="size-4" />
          Opening line
        </div>
        <div className="mt-3 text-xl font-semibold text-zinc-100 md:text-2xl">{PRESENTER_CONTRACT.opening}</div>
      </div>

      <div className={`mt-6 grid gap-3 ${compact ? 'md:grid-cols-2' : 'md:grid-cols-2 xl:grid-cols-4'}`}>
        {PRESENTER_CONTRACT.steps.map((step, index) => (
          <article key={step.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex size-7 items-center justify-center rounded-full bg-white/5 text-xs font-semibold text-zinc-300">{index + 1}</div>
              <span className="text-xs font-medium text-zinc-600">{step.seconds}s</span>
            </div>
            <h3 className="mt-4 text-sm font-semibold text-zinc-200">{step.label}</h3>
            <p className="mt-2 text-sm leading-6 text-zinc-500">{step.script}</p>
          </article>
        ))}
      </div>

      <div className="mt-6 rounded-2xl border border-emerald-400/20 bg-emerald-400/[0.045] px-4 py-3 text-sm font-medium text-emerald-100">
        Close: {PRESENTER_CONTRACT.closing}
      </div>
    </section>
  )
}
