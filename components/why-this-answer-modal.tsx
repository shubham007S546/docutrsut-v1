'use client'

import React from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  FileCheck2,
  FileText,
  HelpCircle,
  Scale,
  Shield,
  ShieldAlert,
  Sparkles,
  Users,
  X
} from 'lucide-react'
import { MarkdownView } from './markdown-view'

export type WhyThisAnswerData = {
  question: string
  intent: string
  agents: { agent: string; status: string; answer?: string; reason?: string }[]
  retrieved_documents: { name: string; version: string; section: string; quote: string; score: number }[]
  claims: { claim_text: string; status: string; section?: string; version?: string; confidence: number }[]
  conflicts: { topic?: string; status?: string; resolution?: string; rule_a?: string; rule_b?: string }[]
  policy_version: string
  confidence: number
  confidence_breakdown?: {
    retrieval_relevance: number
    evidence_coverage: number
    source_agreement: number
    verification_strength: number
    conflict_penalty: number
  }
  verification_result: string
  final_decision: string
  human_review_required: boolean
  review_reasons?: string[]
  receipt_id?: string
  provenance_hash?: string
}

export function WhyThisAnswerModal({
  isOpen,
  onClose,
  data
}: {
  isOpen: boolean
  onClose: () => void
  data: WhyThisAnswerData | null
}) {
  if (!isOpen || !data) return null

  const isApproved = !data.human_review_required && data.final_decision === 'ANSWER'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative flex max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl border border-teal-900/20 bg-card shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border bg-secondary/50 px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-xl bg-teal-600 text-white shadow-sm">
              <ClipboardCheck className="size-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold tracking-tight">Why This Answer?</h2>
                <span className="rounded-full bg-teal-100 dark:bg-teal-950 px-2.5 py-0.5 font-mono text-xs font-semibold text-teal-800 dark:text-teal-300">
                  Trust Provenance Audit
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Complete explainability trail from query to evidence receipt.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close why this answer dialog"
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Body content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Decision Status Banner */}
          <div
            className={`flex flex-wrap items-center justify-between gap-4 rounded-xl border p-4 ${
              isApproved
                ? 'border-emerald-200 bg-emerald-50/70 text-emerald-950 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-100'
                : 'border-amber-200 bg-amber-50/70 text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-100'
            }`}
          >
            <div className="flex items-center gap-3">
              {isApproved ? (
                <CheckCircle2 className="size-6 text-emerald-600 dark:text-emerald-400 shrink-0" />
              ) : (
                <ShieldAlert className="size-6 text-amber-600 dark:text-amber-400 shrink-0" />
              )}
              <div>
                <p className="font-mono text-xs font-bold uppercase tracking-wider">
                  Decision: {data.final_decision}
                </p>
                <p className="text-xs opacity-90 mt-0.5">
                  {isApproved
                    ? 'All material claims verified against active policy provisions with high confidence.'
                    : 'Uncertainty, conflicting provisions, or unestablished rules detected. Escalated for human adjudication.'}
                </p>
              </div>
            </div>
            <div className="text-right">
              <span className="font-mono text-xl font-bold">
                {Math.round(data.confidence * 100)}%
              </span>
              <span className="block text-xs uppercase tracking-wider text-muted-foreground">
                Evidence Confidence
              </span>
            </div>
          </div>

          {/* Key Overview Cards */}
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-xl border bg-muted/30 p-3.5">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Question Intent</p>
              <p className="mt-1 text-sm font-medium capitalize">{data.intent.replace(/_/g, ' ')}</p>
            </div>
            <div className="rounded-xl border bg-muted/30 p-3.5">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Active Policy Version</p>
              <p className="mt-1 text-sm font-medium">{data.policy_version || 'v2 (Current Effective)'}</p>
            </div>
            <div className="rounded-xl border bg-muted/30 p-3.5">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Human Review Status</p>
              <p className="mt-1 text-sm font-medium">
                {data.human_review_required ? 'Required (Enqueued)' : 'Not Required'}
              </p>
            </div>
          </div>

          {/* Confidence Breakdown Formula */}
          {data.confidence_breakdown && (
            <section className="rounded-xl border p-4 bg-card">
              <div className="flex items-center justify-between border-b pb-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-teal-800 dark:text-teal-300">
                  Evidence Confidence Formula
                </h3>
                <span className="font-mono text-xs text-muted-foreground">
                  Score = 0.35*R + 0.25*C + 0.15*A + 0.25*V - 0.20*F
                </span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-5 text-center">
                <div className="rounded-lg bg-secondary/60 p-2.5">
                  <span className="block font-mono text-base font-bold text-teal-700 dark:text-teal-400">
                    {Math.round(data.confidence_breakdown.retrieval_relevance * 100)}%
                  </span>
                  <span className="text-xs font-medium text-muted-foreground">Retrieval (R)</span>
                </div>
                <div className="rounded-lg bg-secondary/60 p-2.5">
                  <span className="block font-mono text-base font-bold text-teal-700 dark:text-teal-400">
                    {Math.round(data.confidence_breakdown.evidence_coverage * 100)}%
                  </span>
                  <span className="text-xs font-medium text-muted-foreground">Coverage (C)</span>
                </div>
                <div className="rounded-lg bg-secondary/60 p-2.5">
                  <span className="block font-mono text-base font-bold text-teal-700 dark:text-teal-400">
                    {Math.round(data.confidence_breakdown.source_agreement * 100)}%
                  </span>
                  <span className="text-xs font-medium text-muted-foreground">Agreement (A)</span>
                </div>
                <div className="rounded-lg bg-secondary/60 p-2.5">
                  <span className="block font-mono text-base font-bold text-teal-700 dark:text-teal-400">
                    {Math.round(data.confidence_breakdown.verification_strength * 100)}%
                  </span>
                  <span className="text-xs font-medium text-muted-foreground">Verification (V)</span>
                </div>
                <div className="rounded-lg bg-secondary/60 p-2.5">
                  <span className="block font-mono text-base font-bold text-rose-600 dark:text-rose-400">
                    -{Math.round(data.confidence_breakdown.conflict_penalty * 100)}%
                  </span>
                  <span className="text-xs font-medium text-muted-foreground">Conflict Penalty (F)</span>
                </div>
              </div>
            </section>
          )}

          {/* Selected Specialist Agents */}
          <section className="rounded-xl border p-4 bg-card">
            <h3 className="text-xs font-bold uppercase tracking-wider text-teal-800 dark:text-teal-300">
              Specialist Agent Roster
            </h3>
            <div className="mt-3 divide-y">
              {data.agents.map((ag, i) => (
                <div key={i} className="py-2.5 flex items-start justify-between gap-3 text-xs">
                  <div>
                    <span className="font-semibold text-foreground">{ag.agent}</span>
                    <span className="ml-2 rounded-full bg-secondary px-2.5 py-0.5 text-xs text-muted-foreground">
                      {ag.status}
                    </span>
                    {ag.reason && <p className="mt-0.5 text-muted-foreground">{ag.reason}</p>}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Claim-Level Verification */}
          {data.claims.length > 0 && (
            <section className="rounded-xl border p-4 bg-card">
              <h3 className="text-xs font-bold uppercase tracking-wider text-teal-800 dark:text-teal-300">
                Claim-Level Verification
              </h3>
              <div className="mt-3 space-y-2.5">
                {data.claims.map((claim, idx) => (
                  <div key={idx} className="rounded-lg border bg-muted/20 p-3 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-bold text-muted-foreground">
                        CLAIM {idx + 1}
                      </span>
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                          claim.status === 'SUPPORTED'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                        }`}
                      >
                        {claim.status}
                      </span>
                    </div>
                    <p className="mt-1.5 font-medium text-foreground">{claim.claim_text}</p>
                    <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                      <FileCheck2 className="size-3.5 text-teal-600" />
                      <span>{claim.section || 'General'}</span>
                      <span>·</span>
                      <span>{claim.version || 'v2'}</span>
                      <span>·</span>
                      <span>Confidence: {Math.round((claim.confidence || 0.85) * 100)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Conflict Analysis */}
          {data.conflicts.length > 0 && (
            <section className="rounded-xl border border-amber-200 dark:border-amber-900 bg-amber-50/30 dark:bg-amber-950/20 p-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="size-4 text-amber-600" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-900 dark:text-amber-300">
                  Cross-Policy Conflict Analysis
                </h3>
              </div>
              <div className="mt-2 space-y-2 text-xs">
                {data.conflicts.map((conf, i) => (
                  <div key={i} className="rounded-lg border border-amber-200 bg-card p-3">
                    <p className="font-semibold text-foreground">{conf.topic || 'Rule Discrepancy'}</p>
                    {conf.rule_a && <p className="mt-1 text-muted-foreground">Policy A: {conf.rule_a}</p>}
                    {conf.rule_b && <p className="mt-0.5 text-muted-foreground">Policy B: {conf.rule_b}</p>}
                    {conf.resolution && (
                      <p className="mt-2 rounded bg-secondary p-2 text-teal-800 dark:text-teal-300 font-medium">
                        Resolution: {conf.resolution}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Retrieved Evidence Provenance */}
          <section className="rounded-xl border p-4 bg-card">
            <h3 className="text-xs font-bold uppercase tracking-wider text-teal-800 dark:text-teal-300">
              Retrieved Policy Passages ({data.retrieved_documents.length})
            </h3>
            <div className="mt-3 space-y-2.5">
              {data.retrieved_documents.map((doc, idx) => (
                <div key={idx} className="rounded-lg border bg-secondary/30 p-3 text-xs">
                  <div className="flex items-center justify-between gap-2 font-medium">
                    <span className="flex items-center gap-1.5 text-teal-800 dark:text-teal-300">
                      <FileText className="size-3.5" />
                      {doc.name} · {doc.section} ({doc.version})
                    </span>
                    <span className="font-mono text-xs text-muted-foreground">
                      Match Score: {doc.score.toFixed(3)}
                    </span>
                  </div>
                  <p className="mt-2 italic text-muted-foreground">"{doc.quote}"</p>
                </div>
              ))}
            </div>
          </section>

          {/* Cryptographic Receipt */}
          {data.receipt_id && (
            <div className="rounded-xl border border-dashed bg-secondary/40 p-4 font-mono text-xs">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>EVIDENCE RECEIPT: {data.receipt_id}</span>
                <span>PROVENANCE HASH: {data.provenance_hash ? data.provenance_hash.slice(0, 16) + '...' : 'VERIFIED'}</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t bg-secondary/40 px-6 py-3 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            DocuTrust Trust-Oriented Evidence Architecture
          </p>
          <button
            onClick={onClose}
            className="rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  )
}
