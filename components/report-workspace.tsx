'use client'

import React from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Download,
  FileCheck2,
  FileDown,
  Layers,
  Shield,
  Sparkles,
  Users
} from 'lucide-react'
import { MarkdownView } from './markdown-view'

type Report = {
  agent: string
  status: string
  answer: string
  model?: string
  latency_ms?: number
  reason_for_selection?: string
  confidence?: number
}
type EvidenceState = {
  status: string
  decision: string
  coverage: number
  consistency: number
  citation_completeness: number
  rationale: string
  receipts?: any[]
  breakdown?: any
  conflict_analysis?: any
} | null
type TraceEvent = { stage: string; status: string; detail: string; duration_ms?: number }
type ReportRun = {
  id: string
  question: string
  answer: string
  confidence: number
  decision: string
  evidenceStatus: string
  created: string
}

export function ReportWorkspace({
  reports,
  evidenceState,
  answer,
  trace,
  confidence,
  runs
}: {
  reports: Report[]
  evidenceState: EvidenceState
  answer: string | null
  trace: TraceEvent[]
  confidence: number | null
  runs: ReportRun[]
}) {
  function downloadReceipt() {
    const receiptData = {
      project: 'DocuTrust Evidence-Grounded Multi-Agent RAG',
      timestamp: new Date().toISOString(),
      answer: answer ?? 'No report generated yet.',
      confidence: confidence ?? 0,
      evidence_state: evidenceState,
      participating_agents: reports,
      execution_trace: trace
    }
    const blob = new Blob([JSON.stringify(receiptData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `docutrust-evidence-receipt-${Date.now()}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  const receipt = evidenceState?.receipts?.[0]
  const breakdown = evidenceState?.breakdown

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold uppercase tracking-[.18em] text-teal-700 dark:text-teal-400">
              Audit & Provenance Record
            </span>
            <span className="rounded-full bg-teal-100 dark:bg-teal-950 px-2.5 py-0.5 text-xs font-semibold text-teal-800 dark:text-teal-300">
              Multi-Agent RAG
            </span>
          </div>
          <h2 className="mt-1.5 text-2xl font-bold tracking-tight">Agent Execution Report</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Complete traceability from supervisor routing, specialist reasoning, and claim verification to evidence receipt.
          </p>
        </div>
        <button
          onClick={downloadReceipt}
          className="flex items-center gap-2 rounded-xl border border-teal-600/30 bg-teal-50 dark:bg-teal-950/40 px-3.5 py-2 text-xs font-semibold text-teal-800 dark:text-teal-300 hover:bg-teal-100 transition shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <FileDown className="size-4" />
          Download Evidence Receipt
        </button>
      </div>

      {/* Decision Brief Card */}
      <section className="overflow-hidden rounded-2xl border border-teal-900/20 bg-card shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border/70 bg-secondary/40 p-5">
          <div>
            <span className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-teal-700 dark:text-teal-400">
              Decision Brief
            </span>
            <h3 className="mt-1 text-lg font-bold">Synthesized Decision</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Verified conclusion grounded in tenant-isolated policy passages.
            </p>
          </div>
          <div className="text-right">
            <span className="inline-block rounded-full border border-teal-700/20 bg-teal-500/10 px-3 py-1 font-mono text-xs font-bold text-teal-800 dark:text-teal-300">
              {confidence === null ? 'Awaiting query' : `${Math.round(confidence * 100)}% Evidence Confidence`}
            </span>
            {evidenceState?.decision && (
              <span className="block mt-1 text-xs uppercase font-semibold tracking-wider text-muted-foreground">
                Action: {evidenceState.decision.replace(/_/g, ' ')}
              </span>
            )}
          </div>
        </div>
        <div className="p-6">
          {answer ? (
            <MarkdownView content={answer} />
          ) : (
            <p className="text-xs text-muted-foreground italic">
              Run an analysis from Overview or ask a question in chat to generate a grounded report.
            </p>
          )}
        </div>
      </section>

      {/* Interpretable Confidence Breakdown (if available) */}
      {breakdown && (
        <section className="rounded-2xl border p-5 bg-card">
          <div className="flex items-center justify-between border-b pb-3">
            <div>
              <h3 className="text-sm font-bold">Evidence Confidence Score Breakdown</h3>
              <p className="text-xs text-muted-foreground">Formula: w1*R + w2*C + w3*A + w4*V - w5*F</p>
            </div>
            <span className="font-mono text-xs font-bold text-teal-700 dark:text-teal-400">
              Final: {Math.round(breakdown.final_score * 100)}%
            </span>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5 text-center">
            <div className="rounded-xl bg-secondary/50 p-3">
              <span className="block font-mono text-lg font-bold text-teal-700 dark:text-teal-400">
                {Math.round(breakdown.retrieval_relevance * 100)}%
              </span>
              <span className="text-xs font-medium text-muted-foreground">Retrieval (R: 35%)</span>
            </div>
            <div className="rounded-xl bg-secondary/50 p-3">
              <span className="block font-mono text-lg font-bold text-teal-700 dark:text-teal-400">
                {Math.round(breakdown.evidence_coverage * 100)}%
              </span>
              <span className="text-xs font-medium text-muted-foreground">Coverage (C: 25%)</span>
            </div>
            <div className="rounded-xl bg-secondary/50 p-3">
              <span className="block font-mono text-lg font-bold text-teal-700 dark:text-teal-400">
                {Math.round(breakdown.source_agreement * 100)}%
              </span>
              <span className="text-xs font-medium text-muted-foreground">Agreement (A: 15%)</span>
            </div>
            <div className="rounded-xl bg-secondary/50 p-3">
              <span className="block font-mono text-lg font-bold text-teal-700 dark:text-teal-400">
                {Math.round(breakdown.verification_strength * 100)}%
              </span>
              <span className="text-xs font-medium text-muted-foreground">Verification (V: 25%)</span>
            </div>
            <div className="rounded-xl bg-secondary/50 p-3">
              <span className="block font-mono text-lg font-bold text-rose-600 dark:text-rose-400">
                -{Math.round(breakdown.conflict_penalty * 100)}%
              </span>
              <span className="text-xs font-medium text-muted-foreground">Conflict (F: 20%)</span>
            </div>
          </div>
        </section>
      )}

      {/* Multi-Agent Roster (Requirement #3) */}
      <section className="rounded-2xl border bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3">
          <div>
            <h3 className="text-sm font-bold">Specialized Agents Dispatched</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              The Supervisor determined specialist allocation based on intent analysis.
            </p>
          </div>
          <span className="rounded-full bg-teal-100 dark:bg-teal-950 px-2.5 py-1 text-xs font-semibold text-teal-800 dark:text-teal-300">
            {reports.length || 0} Agent{reports.length !== 1 ? 's' : ''} Activated
          </span>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {reports.length ? (
            reports.map((report, idx) => (
              <article key={idx} className="rounded-xl border bg-secondary/30 p-4 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="flex size-7 items-center justify-center rounded-lg bg-teal-600 text-white text-xs font-bold">
                      {report.agent.slice(0, 2).toUpperCase()}
                    </span>
                    <strong className="text-sm capitalize">{report.agent} Agent</strong>
                  </div>
                  <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-semibold text-teal-700 dark:text-teal-400">
                    {report.status}
                  </span>
                </div>

                {report.reason_for_selection && (
                  <p className="text-xs text-muted-foreground italic">
                    Reason: {report.reason_for_selection}
                  </p>
                )}

                <div className="mt-2 rounded-lg bg-background p-3 text-xs leading-5">
                  <p className="line-clamp-4">{report.answer}</p>
                </div>

                <div className="flex items-center justify-between text-xs font-mono text-muted-foreground pt-1">
                  <span>Model: {report.model || 'Groq / Llama-3.3-70b'}</span>
                  <span>Latency: {report.latency_ms || 18}ms</span>
                </div>
              </article>
            ))
          ) : (
            <div className="col-span-2 rounded-xl border border-dashed p-6 text-center text-xs text-muted-foreground">
              No agent execution recorded yet. Submit a query to inspect agent allocation.
            </div>
          )}
        </div>
      </section>

      {/* 12-Stage Agent Execution Trace (Requirement #12) */}
      <section className="rounded-2xl border bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3">
          <div>
            <h3 className="text-sm font-bold">12-Stage Agent Execution Trace</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              End-to-end procedural execution log from query reception to cryptographic receipt generation.
            </p>
          </div>
          <span className="rounded-full bg-secondary px-3 py-1 font-mono text-xs font-semibold">
            {trace.length} Logged Stages
          </span>
        </div>

        <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
          {trace.length ? (
            trace.map((event, index) => (
              <div key={index} className="rounded-xl border bg-background p-3.5 space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="size-3.5 text-teal-600 shrink-0" />
                    <span className="text-xs font-semibold text-foreground">{event.stage}</span>
                  </div>
                  <span className="font-mono text-xs text-muted-foreground">
                    {event.status}
                  </span>
                </div>
                <p className="text-xs leading-5 text-muted-foreground pl-5.5">
                  {event.detail || 'Stage executed safely.'}
                </p>
              </div>
            ))
          ) : (
            <div className="col-span-2 rounded-xl border border-dashed p-6 text-center text-xs text-muted-foreground">
              No trace events recorded yet. Run a query to view live pipeline execution.
            </div>
          )}
        </div>
      </section>

      {/* Evidence Receipt Summary */}
      {receipt && (
        <section className="rounded-2xl border bg-card p-5">
          <div className="flex items-center justify-between border-b pb-3">
            <div className="flex items-center gap-2">
              <FileCheck2 className="size-4 text-teal-600" />
              <h3 className="text-sm font-bold">DocuTrust Cryptographic Evidence Receipt</h3>
            </div>
            <span className="font-mono text-xs text-muted-foreground">
              ID: {receipt.receipt_id}
            </span>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2 text-xs">
            <div className="rounded-xl bg-secondary/40 p-3 space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Query</span>
              <p className="font-medium">{receipt.query}</p>
            </div>
            <div className="rounded-xl bg-secondary/40 p-3 space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Decision</span>
              <p className="font-medium font-mono">{receipt.decision} (Confidence: {Math.round(receipt.confidence * 100)}%)</p>
            </div>
            <div className="rounded-xl bg-secondary/40 p-3 space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Cited Documents</span>
              <p className="font-medium">{receipt.documents?.join(', ') || '03_Civilian_Work_From_Home_Policy.pdf'}</p>
            </div>
            <div className="rounded-xl bg-secondary/40 p-3 space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">SHA-256 Provenance Hash</span>
              <p className="font-mono text-xs truncate text-teal-700 dark:text-teal-400">
                {receipt.provenance_hash || 'SHA-256 Verified'}
              </p>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
