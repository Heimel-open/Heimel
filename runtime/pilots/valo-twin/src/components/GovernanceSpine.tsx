import {
  ArrowRight,
  BadgeCheck,
  DatabaseZap,
  Fingerprint,
  GitCommitHorizontal,
  KeyRound,
  Radar,
  Scale,
  ScanSearch,
  Target,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  ENTERPRISE_GOVERNANCE_STAGES,
  RUNTIME_SIGNATURE,
  type EnterpriseGovernanceStageId,
} from '@/lib/enterpriseNarrative'

const stageIcons = {
  purpose: Target,
  authority: KeyRound,
  evidence: DatabaseZap,
  evaluation: ScanSearch,
  clearance: Scale,
  commit: GitCommitHorizontal,
  outcome: Radar,
  receipt: Fingerprint,
} satisfies Record<EnterpriseGovernanceStageId, typeof Target>

export function GovernanceSpine({
  compact = false,
  activeStage,
  title = 'One governance spine. Multiple business realities.',
  subtitle = 'Purpose, authority, evidence and runtime admissibility stay constant. Only the business envelope changes.',
}: {
  compact?: boolean
  activeStage?: EnterpriseGovernanceStageId
  title?: string
  subtitle?: string
}) {
  return (
    <section className={cn('rounded-3xl border border-white/10 bg-[#0d1011]', compact ? 'p-5' : 'p-6 md:p-8')}>
      <div className="flex flex-col gap-2">
        <div className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">Canonical VALO architecture</div>
        <h2 className={cn('font-semibold tracking-tight', compact ? 'text-xl' : 'text-2xl md:text-3xl')}>{title}</h2>
        <p className="max-w-4xl text-sm leading-6 text-zinc-500 md:text-base">{subtitle}</p>
      </div>

      <div className={cn('mt-6 grid gap-2', compact ? 'md:grid-cols-4 xl:grid-cols-8' : 'sm:grid-cols-2 xl:grid-cols-8')}>
        {ENTERPRISE_GOVERNANCE_STAGES.map((stage, index) => {
          const Icon = stageIcons[stage.id]
          const isActive = activeStage === stage.id

          return (
            <div key={stage.id} className="relative flex min-w-0 items-stretch">
              <div
                className={cn(
                  'flex w-full flex-col rounded-2xl border p-3.5',
                  isActive
                    ? 'border-cyan-300/50 bg-cyan-300/[0.08]'
                    : 'border-white/10 bg-black/20',
                )}
              >
                <div className={cn('flex size-8 items-center justify-center rounded-lg', isActive ? 'bg-cyan-300/15 text-cyan-200' : 'bg-white/5 text-zinc-400')}>
                  <Icon className="size-4" />
                </div>
                <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-zinc-300">{stage.label}</div>
                {!compact && <p className="mt-2 text-xs leading-5 text-zinc-600">{stage.detail}</p>}
              </div>
              {index < ENTERPRISE_GOVERNANCE_STAGES.length - 1 && (
                <ArrowRight className="absolute -right-[9px] top-1/2 z-10 hidden size-4 -translate-y-1/2 text-zinc-700 xl:block" />
              )}
            </div>
          )
        })}
      </div>

      {!compact && (
        <div className="mt-6 rounded-2xl border border-white/10 bg-black/25 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Signature runtime pipeline</div>
              <div className="mt-1 text-sm text-zinc-300">The same technical sequence is reused in every enterprise scenario.</div>
            </div>
            <div className="flex items-center gap-2 text-xs text-emerald-300">
              <BadgeCheck className="size-4" />
              Stable platform contract
            </div>
          </div>

          <div className="grid gap-2 md:grid-cols-5">
            {RUNTIME_SIGNATURE.map((stage, index) => (
              <div key={stage.id} className="relative rounded-xl border border-white/10 bg-white/[0.025] px-3 py-3">
                <div className="text-sm font-semibold text-zinc-200">{stage.label}</div>
                <div className="mt-1 text-xs text-zinc-600">{stage.detail}</div>
                {index < RUNTIME_SIGNATURE.length - 1 && (
                  <ArrowRight className="absolute -right-[9px] top-1/2 z-10 hidden size-4 -translate-y-1/2 text-zinc-700 md:block" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
