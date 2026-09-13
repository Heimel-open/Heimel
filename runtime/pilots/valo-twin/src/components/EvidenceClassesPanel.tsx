import {
  AlertTriangle,
  BriefcaseBusiness,
  CheckCircle2,
  Cpu,
  ScrollText,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  HEALTHCARE_EVIDENCE_CLASSES,
  type EvidenceClass,
  type EvidenceClassId,
} from '@/lib/enablement'

const evidenceIcons = {
  technical: Cpu,
  business: BriefcaseBusiness,
  policy: ScrollText,
} satisfies Record<EvidenceClassId, typeof Cpu>

const statusClasses: Record<EvidenceClass['status'], string> = {
  PASS: 'border-emerald-400/35 bg-emerald-400/10 text-emerald-200',
  STEP_UP: 'border-amber-400/35 bg-amber-400/10 text-amber-200',
  RECHECK: 'border-sky-400/35 bg-sky-400/10 text-sky-200',
}

export function EvidenceClassesPanel({
  evidence = HEALTHCARE_EVIDENCE_CLASSES,
}: {
  evidence?: readonly EvidenceClass[]
}) {
  return (
    <section className="rounded-3xl border border-white/10 bg-[#0d1011] p-6 md:p-8">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-end">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">
            Evidence contract
          </div>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
            One action. Three independent evidence classes.
          </h2>
          <p className="mt-3 max-w-4xl text-sm leading-6 text-zinc-500 md:text-base">
            A technical pass proves that the system can execute. Business and policy evidence determine whether the organization has legitimate grounds to rely on that capability now.
          </p>
        </div>
        <div className="rounded-2xl border border-amber-400/25 bg-amber-400/[0.06] p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-200">
            <AlertTriangle className="size-4" />
            Executive conclusion
          </div>
          <p className="mt-2 text-sm leading-6 text-zinc-400">
            Technical evidence can pass while the consequential action still requires STEP_UP.
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        {evidence.map((item) => {
          const Icon = evidenceIcons[item.id]
          const passed = item.status === 'PASS'

          return (
            <article key={item.id} className="flex h-full flex-col rounded-2xl border border-white/10 bg-black/20 p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex size-10 items-center justify-center rounded-xl bg-cyan-300/10 text-cyan-200">
                  <Icon className="size-5" />
                </div>
                <span className={cn('rounded-full border px-2.5 py-1 text-[10px] font-semibold tracking-wide', statusClasses[item.status])}>
                  {item.status}
                </span>
              </div>

              <h3 className="mt-5 text-lg font-semibold text-zinc-100">{item.label}</h3>
              <p className="mt-2 text-sm font-medium leading-6 text-zinc-300">{item.question}</p>
              <p className="mt-3 text-sm leading-6 text-zinc-500">{item.conclusion}</p>

              <div className="mt-5 space-y-2 border-t border-white/10 pt-4">
                {item.observations.map((observation) => (
                  <div key={observation} className="flex gap-2 text-xs leading-5 text-zinc-500">
                    {passed ? (
                      <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-emerald-300" />
                    ) : (
                      <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-300" />
                    )}
                    <span>{observation}</span>
                  </div>
                ))}
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
