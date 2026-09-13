import { ArrowLeft, ArrowRight, GraduationCap, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router'
import LiveSystemDemo from './LiveSystemDemo'
import { EvidenceClassesPanel } from '@/components/EvidenceClassesPanel'
import { PresenterContractPanel } from '@/components/PresenterContractPanel'
import { ENTERPRISE_GOVERNANCE_STAGES } from '@/lib/enterpriseNarrative'

export default function HealthcareScenarioPage() {
  return (
    <div className="min-h-screen bg-[#07090a] text-zinc-100">
      <section className="border-b border-cyan-300/15 bg-cyan-300/[0.035] px-4 py-3 md:px-8">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-400 transition hover:text-cyan-200"
            >
              <ArrowLeft className="size-4" />
              VALO Twin platform
            </Link>
            <div className="flex flex-wrap items-center gap-2">
              <Link
                to="/onboarding"
                className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-cyan-300/30 hover:text-cyan-200"
              >
                <GraduationCap className="size-4" />
                Presenter onboarding
              </Link>
              <div className="flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/[0.06] px-3 py-1.5 text-xs font-medium text-cyan-200">
                <ShieldCheck className="size-4" />
                Healthcare is the business envelope · VALO is the reusable governance platform
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            {ENTERPRISE_GOVERNANCE_STAGES.map((stage, index) => (
              <div key={stage.id} className="flex items-center gap-2">
                <span className={stage.id === 'clearance' ? 'text-cyan-200' : undefined}>{stage.label}</span>
                {index < ENTERPRISE_GOVERNANCE_STAGES.length - 1 && <ArrowRight className="size-3 text-zinc-700" />}
              </div>
            ))}
          </div>
        </div>
      </section>

      <LiveSystemDemo />

      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-5 pb-12 md:px-8">
        <EvidenceClassesPanel />
        <PresenterContractPanel />
        <section className="grid gap-4 rounded-3xl border border-cyan-300/20 bg-cyan-300/[0.045] p-6 md:grid-cols-[minmax(0,1fr)_auto] md:items-center md:p-8">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">Commercial enablement</div>
            <h2 className="mt-2 text-2xl font-semibold text-zinc-100">Turn the demo into repeatable representation.</h2>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-zinc-500">
              The ambassador module teaches the category, approved language, product boundaries and scenario-transfer method before employees or partners present VALO externally.
            </p>
          </div>
          <Link
            to="/onboarding"
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-cyan-300/30 bg-cyan-300/10 px-4 py-2.5 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-300/15"
          >
            Open ambassador onboarding
            <ArrowRight className="size-4" />
          </Link>
        </section>
      </div>
    </div>
  )
}
