import { Link } from 'react-router'
import type { LucideIcon } from 'lucide-react'
import {
  Activity,
  ArrowRight,
  CheckCircle,
  Clock,
  Eye,
  Factory,
  FileText,
  FlaskConical,
  GraduationCap,
  HeartPulse,
  Landmark,
  Send,
  Shield,
  ShieldCheck,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { GovernanceSpine } from '@/components/GovernanceSpine'
import { trpc } from '@/providers/trpc'
import {
  ENTERPRISE_POSITIONING,
  INDUSTRY_ENVELOPES,
} from '@/lib/enterpriseNarrative'

const domainIcons: Record<(typeof INDUSTRY_ENVELOPES)[number]['id'], LucideIcon> = {
  healthcare: HeartPulse,
  finance: Landmark,
  manufacturing: Factory,
  'public-sector': ShieldCheck,
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: LucideIcon
  label: string
  value: number | string
  color: string
}) {
  return (
    <Card className="border-[#222] bg-[#141414]">
      <CardContent className="flex items-center gap-3 p-4">
        <div className={`rounded-lg p-2 ${color}`}>
          <Icon size={18} className="text-white" />
        </div>
        <div>
          <p className="text-2xl font-bold text-[#e8e8e8]">{value}</p>
          <p className="text-xs text-[#666]">{label}</p>
        </div>
      </CardContent>
    </Card>
  )
}

export default function Dashboard() {
  const { data: stats } = trpc.analytics.stats.useQuery()
  const { data: activity } = trpc.analytics.activity.useQuery({ limit: 10 })

  return (
    <div className="flex-1 overflow-auto bg-[#090b0c] p-4 md:p-6">
      <div className="mx-auto flex w-full max-w-[1560px] flex-col gap-6">
        <section className="grid gap-6 rounded-3xl border border-cyan-300/20 bg-cyan-300/[0.045] p-6 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-end md:p-8">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/25 bg-cyan-300/[0.07] px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-cyan-200">
              <Shield className="size-4" />
              {ENTERPRISE_POSITIONING.category}
            </div>
            <h1 className="mt-5 max-w-5xl text-3xl font-semibold tracking-tight text-zinc-100 md:text-5xl">
              {ENTERPRISE_POSITIONING.headline}
            </h1>
            <p className="mt-4 max-w-4xl text-base leading-7 text-zinc-400 md:text-lg">
              {ENTERPRISE_POSITIONING.explanation}
            </p>
            <div className="mt-5 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm font-medium text-zinc-200">
              {ENTERPRISE_POSITIONING.signature}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/25 p-5">
            <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Executive demo principle</div>
            <div className="mt-2 text-xl font-semibold text-zinc-100">The software can execute.</div>
            <div className="mt-1 text-xl font-semibold text-amber-200">The organization may not have authorized the action.</div>
            <p className="mt-3 text-sm leading-6 text-zinc-500">
              Twin demonstrates the difference between technical capability, delegated authority and present-state admissibility.
            </p>
            <div className="mt-5 flex flex-col gap-2 sm:flex-row lg:flex-col xl:flex-row">
              <Link
                to="/demo"
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-cyan-300/30 bg-cyan-300/10 px-4 py-2.5 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-300/15"
              >
                Open scenario
                <ArrowRight className="size-4" />
              </Link>
              <a
                href={`${import.meta.env.BASE_URL}hugging-face/`}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-amber-300/30 bg-amber-300/10 px-4 py-2.5 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/15"
              >
                Hugging Face incident
                <ArrowRight className="size-4" />
              </a>
              <a
                href={`${import.meta.env.BASE_URL}devops-boundary/`}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-violet-300/30 bg-violet-300/10 px-4 py-2.5 text-sm font-semibold text-violet-100 transition hover:bg-violet-300/15"
              >
                Shared DevOps test
                <ArrowRight className="size-4" />
              </a>
              <Link
                to="/onboarding"
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] px-4 py-2.5 text-sm font-semibold text-zinc-200 transition hover:border-cyan-300/25 hover:text-cyan-100"
              >
                <GraduationCap className="size-4" />
                Onboard presenter
              </Link>
            </div>
          </div>
        </section>

        <GovernanceSpine />

        <section className="rounded-3xl border border-white/10 bg-[#0d1011] p-6 md:p-8">
          <div className="flex flex-col gap-2">
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">Reusable enterprise narrative</div>
            <h2 className="text-2xl font-semibold tracking-tight text-zinc-100 md:text-3xl">The platform stays fixed. The business envelope changes.</h2>
            <p className="max-w-4xl text-sm leading-6 text-zinc-500 md:text-base">
              Each sector supplies its own purpose, authority, evidence, policies and consequences. VALO reuses the same evaluation, clearance, controlled commit and receipt architecture.
            </p>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {INDUSTRY_ENVELOPES.map((envelope) => {
              const Icon = domainIcons[envelope.id]
              const isLive = envelope.id === 'healthcare'

              const content = (
                <div className={`h-full rounded-2xl border p-5 transition ${isLive ? 'border-cyan-300/35 bg-cyan-300/[0.055] hover:bg-cyan-300/[0.08]' : 'border-white/10 bg-black/20'}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex size-10 items-center justify-center rounded-xl bg-white/5 text-cyan-200">
                      <Icon className="size-5" />
                    </div>
                    <span className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold tracking-wide ${isLive ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200' : 'border-white/10 bg-white/[0.03] text-zinc-500'}`}>
                      {envelope.status}
                    </span>
                  </div>
                  <h3 className="mt-5 text-lg font-semibold text-zinc-100">{envelope.domain}</h3>
                  <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-zinc-600">Proposed action</div>
                  <p className="mt-1 text-sm leading-6 text-zinc-300">{envelope.proposedAction}</p>
                  <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-zinc-600">Authority and evidence</div>
                  <p className="mt-1 text-sm leading-6 text-zinc-500">{envelope.authority}</p>
                  <div className="mt-4 border-t border-white/10 pt-4 text-sm font-medium text-zinc-300">{envelope.outcome}</div>
                </div>
              )

              return isLive ? (
                <Link key={envelope.id} to="/demo" aria-label="Open the healthcare execution governance demo">
                  {content}
                </Link>
              ) : (
                <div key={envelope.id}>{content}</div>
              )
            })}
          </div>
        </section>

        <section>
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-600">
                <FlaskConical size={16} />
                Operational Twin
              </div>
              <h2 className="mt-2 text-2xl font-semibold text-zinc-100">Governed workflow status</h2>
              <p className="mt-1 text-sm text-zinc-500">Existing drafts, reviews, watchlist activity and gate telemetry remain available below the enterprise narrative.</p>
            </div>
          </div>

          <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard icon={FileText} label="Total Drafts" value={stats?.totalDrafts || 0} color="bg-blue-600" />
            <StatCard icon={Clock} label="Pending" value={stats?.pending || 0} color="bg-amber-600" />
            <StatCard icon={CheckCircle} label="Approved" value={stats?.approved || 0} color="bg-emerald-600" />
            <StatCard icon={Send} label="Posted" value={stats?.posted || 0} color="bg-purple-600" />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card className="border-[#222] bg-[#141414]">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Shield size={14} className="text-emerald-400" />
                  VALO Gate Health
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-4 flex items-center gap-4">
                  <div className="text-4xl font-bold text-emerald-400">{stats?.avgCoherence || 0}%</div>
                  <div>
                    <p className="text-xs text-[#666]">Avg Coherence</p>
                    <Badge variant="outline" className="border-emerald-800 bg-emerald-950 text-emerald-400">
                      HEALTHY
                    </Badge>
                  </div>
                </div>
                <Separator className="my-3 bg-[#222]" />
                {stats?.regimeBreakdown && Object.entries(stats.regimeBreakdown).map(([regime, count]) => (
                  <div key={regime} className="flex justify-between py-1 text-xs">
                    <span className="text-[#888]">{regime}</span>
                    <span className="text-[#e8e8e8]">{count as number}</span>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="border-[#222] bg-[#141414]">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Eye size={14} className="text-blue-400" />
                  Watchlist
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-2 text-3xl font-bold text-[#e8e8e8]">{stats?.watchlistCount || 0}</div>
                <p className="mb-3 text-xs text-[#666]">Monitored contacts</p>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs"><span className="text-amber-400">Monitor</span><span className="text-[#888]">Active</span></div>
                  <div className="flex justify-between text-xs"><span className="text-emerald-400">Engage</span><span className="text-[#888]">Priority</span></div>
                  <div className="flex justify-between text-xs"><span className="text-red-400">Critical</span><span className="text-[#888]">Alert</span></div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="mt-6 border-[#222] bg-[#141414]">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Activity size={14} className="text-purple-400" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              {activity && activity.length > 0 ? (
                <div className="space-y-2">
                  {activity.map((item) => (
                    <div key={item.id} className="flex items-center justify-between border-b border-[#1a1a1a] py-1.5 text-xs">
                      <div className="flex items-center gap-2">
                        <div className={`size-2 rounded-full ${
                          item.action.includes('approved') ? 'bg-emerald-500' :
                          item.action.includes('rejected') ? 'bg-red-500' :
                          item.action.includes('created') ? 'bg-blue-500' :
                          'bg-amber-500'
                        }`} />
                        <span className="text-[#888]">{item.action.replace(/_/g, ' ')}</span>
                      </div>
                      <span className="text-[#555]">{item.createdAt ? new Date(item.createdAt).toLocaleTimeString() : 'N/A'}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-[#555]">No activity yet</p>
              )}
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  )
}
