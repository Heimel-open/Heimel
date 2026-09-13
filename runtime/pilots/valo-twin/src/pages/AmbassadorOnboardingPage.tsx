import { Link } from 'react-router'
import {
  ArrowRight,
  BadgeCheck,
  Building2,
  CheckCircle2,
  CircleAlert,
  GraduationCap,
  MessageSquareText,
  ShieldCheck,
} from 'lucide-react'
import { GovernanceSpine } from '@/components/GovernanceSpine'
import { PresenterContractPanel } from '@/components/PresenterContractPanel'
import { AMBASSADOR_ONBOARDING } from '@/lib/enablement'
import { INDUSTRY_ENVELOPES } from '@/lib/enterpriseNarrative'

export default function AmbassadorOnboardingPage() {
  return (
    <div className="flex-1 overflow-auto bg-[#090b0c] p-4 md:p-6">
      <div className="mx-auto flex w-full max-w-[1560px] flex-col gap-6">
        <section className="grid gap-6 rounded-3xl border border-cyan-300/20 bg-cyan-300/[0.045] p-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-end md:p-8">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/25 bg-cyan-300/[0.07] px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-cyan-200">
              <GraduationCap className="size-4" />
              Ambassador onboarding
            </div>
            <h1 className="mt-5 max-w-5xl text-3xl font-semibold tracking-tight text-zinc-100 md:text-5xl">
              Explain VALO accurately. Preserve the architecture.
            </h1>
            <p className="mt-4 max-w-4xl text-base leading-7 text-zinc-400 md:text-lg">
              {AMBASSADOR_ONBOARDING.purpose}
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/25 p-5">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
              <BadgeCheck className="size-4 text-emerald-300" />
              {AMBASSADOR_ONBOARDING.id}
            </div>
            <div className="mt-2 text-xl font-semibold text-zinc-100">Version {AMBASSADOR_ONBOARDING.version}</div>
            <p className="mt-3 text-sm leading-6 text-zinc-500">
              Completion means the ambassador can explain the category, the runtime pipeline, the evidence model and the product boundaries without improvising component roles.
            </p>
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-[#0d1011] p-6 md:p-8">
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">Learning outcomes</div>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-100 md:text-3xl">What every VALO representative must be able to explain</h2>
          <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {AMBASSADOR_ONBOARDING.learningOutcomes.map((outcome, index) => (
              <div key={outcome} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex size-7 items-center justify-center rounded-full bg-cyan-300/10 text-xs font-semibold text-cyan-200">{index + 1}</div>
                <p className="mt-3 text-sm leading-6 text-zinc-400">{outcome}</p>
              </div>
            ))}
          </div>
        </section>

        <GovernanceSpine />
        <PresenterContractPanel compact />

        <section className="grid gap-5 lg:grid-cols-2">
          <div className="rounded-3xl border border-emerald-400/20 bg-emerald-400/[0.035] p-6 md:p-8">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">
              <MessageSquareText className="size-4" />
              Approved language
            </div>
            <h2 className="mt-2 text-2xl font-semibold text-zinc-100">Say this consistently</h2>
            <div className="mt-5 space-y-3">
              {AMBASSADOR_ONBOARDING.approvedLanguage.map((statement) => (
                <div key={statement} className="flex gap-3 rounded-2xl border border-white/10 bg-black/20 p-4 text-sm leading-6 text-zinc-300">
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-300" />
                  <span>{statement}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border border-amber-400/20 bg-amber-400/[0.035] p-6 md:p-8">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-amber-300">
              <CircleAlert className="size-4" />
              Claim boundaries
            </div>
            <h2 className="mt-2 text-2xl font-semibold text-zinc-100">Do not say this</h2>
            <div className="mt-5 space-y-3">
              {AMBASSADOR_ONBOARDING.prohibitedLanguage.map((statement) => (
                <div key={statement} className="flex gap-3 rounded-2xl border border-white/10 bg-black/20 p-4 text-sm leading-6 text-zinc-400">
                  <CircleAlert className="mt-0.5 size-4 shrink-0 text-amber-300" />
                  <span>{statement}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-[#0d1011] p-6 md:p-8">
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">Scenario transfer exercise</div>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-100 md:text-3xl">Keep the governance spine. Change only the business envelope.</h2>
          <p className="mt-3 max-w-4xl text-sm leading-6 text-zinc-500 md:text-base">
            Use each card to explain the proposed action, the governing authority and the real-world outcome without changing the roles of VAIG, REHT, Core or RACS.
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {INDUSTRY_ENVELOPES.map((envelope) => (
              <article key={envelope.id} className="rounded-2xl border border-white/10 bg-black/20 p-5">
                <div className="flex size-10 items-center justify-center rounded-xl bg-cyan-300/10 text-cyan-200">
                  <Building2 className="size-5" />
                </div>
                <h3 className="mt-5 text-lg font-semibold text-zinc-100">{envelope.domain}</h3>
                <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-zinc-600">Action</div>
                <p className="mt-1 text-sm leading-6 text-zinc-300">{envelope.proposedAction}</p>
                <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-zinc-600">Authority and evidence</div>
                <p className="mt-1 text-sm leading-6 text-zinc-500">{envelope.authority}</p>
                <div className="mt-4 border-t border-white/10 pt-4 text-sm font-medium text-zinc-300">{envelope.outcome}</div>
              </article>
            ))}
          </div>
        </section>

        <section className="grid gap-5 rounded-3xl border border-cyan-300/20 bg-cyan-300/[0.045] p-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-center md:p-8">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">
              <ShieldCheck className="size-4" />
              Completion check
            </div>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-100 md:text-3xl">Ready to represent VALO</h2>
            <div className="mt-5 space-y-3">
              {AMBASSADOR_ONBOARDING.completionChecklist.map((item) => (
                <div key={item} className="flex gap-3 text-sm leading-6 text-zinc-400">
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-cyan-300" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/25 p-5">
            <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Practical assessment</div>
            <p className="mt-3 text-sm leading-6 text-zinc-400">
              Deliver the healthcare scenario in 60 seconds, answer why STEP_UP is not DENY, and then transfer the same architecture to one other industry.
            </p>
            <Link
              to="/demo"
              className="mt-5 inline-flex items-center gap-2 rounded-xl border border-cyan-300/30 bg-cyan-300/10 px-4 py-2.5 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-300/15"
            >
              Open practical scenario
              <ArrowRight className="size-4" />
            </Link>
          </div>
        </section>
      </div>
    </div>
  )
}
