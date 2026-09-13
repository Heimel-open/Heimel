import { useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, ReceiptText, ShieldCheck, XCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type Verdict = 'ALLOW' | 'DENY'

type Scenario = {
  id: string
  tab: string
  title: string
  intent: string
  verdict: Verdict
  message: string
  steps: { label: string; detail: string; verdict?: Verdict }[]
  evidence: { label: string; value: string; tone: 'pass' | 'warn' | 'fail' | 'neutral' }[]
  receipt: { id: string; action: string; state: string; policy: string }
}

const scenarios: Scenario[] = [
  {
    id: 'within',
    tab: 'Within mandate',
    title: 'Supplier payment within mandate',
    intent: 'Pay NOK 18,000 to an approved supplier under a NOK 100,000 monthly mandate.',
    verdict: 'ALLOW',
    message: 'The live consequence still fits the mandate and all conditions precedent remain true.',
    steps: [
      { label: 'Request', detail: 'Agent proposes payment of NOK 18,000 for invoice NC-2048.' },
      { label: 'Conditions', detail: 'Invoice approved, supplier active, account unchanged, goods receipt matched.', verdict: 'ALLOW' },
      { label: 'Exposure', detail: 'NOK 54,000 already committed. Proposed total: NOK 72,000.', verdict: 'ALLOW' },
      { label: 'Mandate', detail: 'Approved suppliers and cumulative monthly spend below NOK 100,000.', verdict: 'ALLOW' },
      { label: 'Commit', detail: 'Payment instruction is bound to the live mandate and released.', verdict: 'ALLOW' },
    ],
    evidence: [
      { label: 'Mandate', value: 'Approved suppliers; NOK 100,000 monthly cap', tone: 'pass' },
      { label: 'Conditions precedent', value: '4 of 4 satisfied', tone: 'pass' },
      { label: 'Cumulative exposure', value: 'NOK 72,000 of NOK 100,000', tone: 'pass' },
      { label: 'Remaining authority', value: 'NOK 28,000', tone: 'neutral' },
    ],
    receipt: { id: 'racs-payment-allow-02048', action: 'payment:NC-2048:NOK-18000', state: 'sha256:17fd0f4c8af28d91', policy: 'PAY-MANDATE-2026.07' },
  },
  {
    id: 'exposure',
    tab: 'Exposure limit',
    title: 'Cumulative exposure exceeds mandate',
    intent: 'Pay NOK 38,000 after NOK 79,000 has already been committed this month.',
    verdict: 'DENY',
    message: 'Runtime evaluation can stop or escalate the action, but it cannot create the missing authority.',
    steps: [
      { label: 'Request', detail: 'Agent proposes payment of NOK 38,000 for invoice NC-2057.' },
      { label: 'Conditions', detail: 'Invoice, supplier and account are technically valid.', verdict: 'ALLOW' },
      { label: 'Exposure', detail: 'NOK 79,000 already committed. Proposed total: NOK 117,000.', verdict: 'DENY' },
      { label: 'Mandate', detail: 'Existing authority ends at NOK 100,000. Deficit: NOK 17,000.', verdict: 'DENY' },
      { label: 'Commit', detail: 'No payment instruction is released. New human authority is required.', verdict: 'DENY' },
    ],
    evidence: [
      { label: 'Mandate', value: 'NOK 100,000 monthly cap', tone: 'neutral' },
      { label: 'Current exposure', value: 'NOK 79,000', tone: 'warn' },
      { label: 'Proposed exposure', value: 'NOK 117,000', tone: 'fail' },
      { label: 'Required action', value: 'New human authorization', tone: 'warn' },
    ],
    receipt: { id: 'racs-payment-deny-02057', action: 'payment:NC-2057:NOK-38000', state: 'sha256:a27939a8d170fa5c', policy: 'PAY-MANDATE-2026.07' },
  },
  {
    id: 'context',
    tab: 'Context changed',
    title: 'Context change invalidates payment path',
    intent: 'Pay an approved invoice after the supplier bank account changed the same day.',
    verdict: 'DENY',
    message: 'The amount remains inside the mandate, but a condition precedent is no longer satisfied.',
    steps: [
      { label: 'Request', detail: 'Agent proposes payment of NOK 18,000 to a newly supplied account.' },
      { label: 'Conditions', detail: 'A same-day bank account change is detected.', verdict: 'DENY' },
      { label: 'Exposure', detail: 'NOK 72,000 total remains inside the delegated limit.', verdict: 'ALLOW' },
      { label: 'Mandate', detail: 'Independent callback is required before using a changed account.', verdict: 'DENY' },
      { label: 'Commit', detail: 'Payment is held for step-up verification through an independent channel.', verdict: 'DENY' },
    ],
    evidence: [
      { label: 'Mandate', value: 'Amount remains within delegated limit', tone: 'pass' },
      { label: 'Context change', value: 'Supplier bank account changed today', tone: 'fail' },
      { label: 'Failed condition', value: 'Independent callback not completed', tone: 'fail' },
      { label: 'Required action', value: 'Step-up verification', tone: 'warn' },
    ],
    receipt: { id: 'racs-payment-context-02058', action: 'payment:NC-2058:NOK-18000', state: 'sha256:4cc5829920f49d7e', policy: 'PAY-MANDATE-2026.07' },
  },
]

const toneClasses = {
  pass: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
  warn: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
  fail: 'border-red-500/40 bg-red-500/10 text-red-200',
  neutral: 'border-zinc-700 bg-zinc-900 text-zinc-200',
}

export default function EnterprisePaymentDemo() {
  const [selected, setSelected] = useState('within')
  const scenario = useMemo(() => scenarios.find(item => item.id === selected) ?? scenarios[0], [selected])

  return (
    <div className="min-h-screen bg-[#0b0d0e] p-4 text-zinc-100 md:p-6">
      <main className="mx-auto max-w-7xl space-y-4">
        <header className="flex flex-col gap-3 rounded-lg border border-zinc-800 bg-[#111415] p-5 md:flex-row md:items-start md:justify-between">
          <div>
            <Badge className="mb-3 border-amber-500/40 bg-amber-500/10 text-amber-200">SIMULATED ENTERPRISE WORKFLOW</Badge>
            <h1 className="text-3xl font-semibold">Mandate to final commit</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-400">A supplier payment is evaluated against delegated authority, conditions precedent, cumulative exposure and live context.</p>
          </div>
          <div className={cn('flex items-center gap-2 rounded-lg border px-4 py-3', scenario.verdict === 'ALLOW' ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-200' : 'border-red-500/50 bg-red-500/10 text-red-200')}>
            {scenario.verdict === 'ALLOW' ? <CheckCircle2 className="size-5" /> : <XCircle className="size-5" />}
            <div><div className="text-xs uppercase opacity-70">Final commit</div><div className="text-xl font-semibold">{scenario.verdict}</div></div>
          </div>
        </header>

        <div className="flex flex-wrap gap-2">
          {scenarios.map(item => <Button key={item.id} variant="outline" onClick={() => setSelected(item.id)} className={cn('border-zinc-700 bg-zinc-900 text-zinc-200', selected === item.id && 'border-cyan-400 bg-cyan-400/10 text-cyan-200')}>{item.tab}</Button>)}
        </div>

        <section className="rounded-lg border border-zinc-800 bg-[#111415] p-5">
          <h2 className="text-2xl font-semibold">{scenario.title}</h2>
          <p className="mt-2 text-sm text-zinc-400">{scenario.intent}</p>
          <div className="mt-5 grid gap-3 md:grid-cols-5">
            {scenario.steps.map((step, index) => <div key={step.label} className={cn('rounded-lg border p-4', !step.verdict ? 'border-zinc-700 bg-zinc-950' : step.verdict === 'ALLOW' ? 'border-emerald-500/40 bg-emerald-500/10' : 'border-red-500/40 bg-red-500/10')}><div className="font-mono text-xs text-zinc-500">0{index + 1}</div><div className="mt-3 font-semibold">{step.label}</div><p className="mt-2 text-sm leading-6 text-zinc-400">{step.detail}</p></div>)}
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-zinc-800 bg-[#111415] p-5">
            <div className="flex items-center gap-2 font-semibold"><ShieldCheck className="size-4 text-emerald-300" />Mandate and live evidence</div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">{scenario.evidence.map(item => <div key={item.label} className={cn('rounded-md border px-3 py-3 text-sm', toneClasses[item.tone])}><div className="text-xs uppercase opacity-70">{item.label}</div><div className="mt-1 font-medium">{item.value}</div></div>)}</div>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-[#111415] p-5">
            <div className="flex items-center gap-2 font-semibold"><ReceiptText className="size-4 text-cyan-300" />Decision receipt</div>
            <p className="mt-2 text-sm leading-6 text-zinc-400">{scenario.message}</p>
            <div className="mt-4 space-y-2 text-sm"><ReceiptRow label="Receipt ID" value={scenario.receipt.id} /><ReceiptRow label="Bound action" value={scenario.receipt.action} /><ReceiptRow label="State hash" value={scenario.receipt.state} /><ReceiptRow label="Policy" value={scenario.receipt.policy} /></div>
          </div>
        </section>

        <section className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 text-sm leading-6 text-amber-100"><div className="flex gap-2"><AlertTriangle className="mt-1 size-4 shrink-0" /><p>Key distinction: runtime context may restrict, escalate or stop an action. It does not create broader authority than the mandate established by a human or institution.</p></div></section>
      </main>
    </div>
  )
}

function ReceiptRow({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2"><div className="text-xs uppercase text-zinc-500">{label}</div><div className="mt-1 break-all font-mono text-zinc-200">{value}</div></div>
}
