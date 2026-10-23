'use client'

import React, { useState } from 'react'
import {
  ArrowDown,
  CheckCircle2,
  ChevronRight,
  FileCheck,
  GitBranch,
  Lock,
  Search,
  Shield,
  ShieldAlert,
  Sparkles,
  Users,
  Workflow,
  Zap
} from 'lucide-react'

export function TrustArchitectureView() {
  const [selectedNode, setSelectedNode] = useState<string | null>('supervisor')

  const nodes = [
    {
      id: 'query',
      title: '1. User Query & Intent Analysis',
      subtitle: 'Analyzes compliance domain, risk level, and intent',
      icon: Search,
      tag: 'Input Analysis',
      details:
        'The query is parsed for domain-specific policy requirements, identifying whether the problem relates to general employee guidelines, GDPR privacy, mandatory technical security controls, or cross-version contradictions.',
      controls: ['Sanitization', 'Safe query budget', 'Domain classification']
    },
    {
      id: 'supervisor',
      title: '2. Multi-Agent Supervisor / Router',
      subtitle: 'Determines which specialist agent(s) are appropriate',
      icon: Users,
      tag: 'Specialized Routing',
      details:
        'Rather than running every agent indiscriminately, the Supervisor selectively dispatches domain specialists: Policy Agent, Privacy Agent, Security Agent, Legal/Compliance Agent, or Conflict Resolution Agent. It produces a clear rationale for every agent selected.',
      controls: ['Bounded agent budget', 'Explicit routing contract', 'Zero blind execution']
    },
    {
      id: 'retrieval',
      title: '3. Tenant-Scoped Private Retrieval',
      subtitle: 'Hybrid RAG via FAISS Vector Store + BM25 Lexical + CrossEncoder',
      icon: Lock,
      tag: 'Tenant Isolation',
      details:
        'Every retrieval operation carries the authenticated tenant_id. Strict filtering guarantees that documents from Tenant A can never be observed or retrieved by Tenant B. Combines dense semantic search with sparse lexical matching and Reciprocal Rank Fusion.',
      controls: ['Strict tenant_id partition', 'Zero cross-tenant leakage', 'Provenance chunk tagging']
    },
    {
      id: 'evidence',
      title: '4. Evidence Collection & Provenance',
      subtitle: 'Structured EvidenceRecord generation with section and version tracking',
      icon: FileCheck,
      tag: 'First-Class Evidence',
      details:
        'Retrieved passages are bound into structured EvidenceRecord objects containing document title, version (e.g., v1 vs v2), section identifier, page number, character offsets, and retrieval score.',
      controls: ['Cryptographic chunk hashing', 'Document version stamping', 'Attributable passage boundaries']
    },
    {
      id: 'sufficiency',
      title: '5. Evidence Sufficiency Analysis',
      subtitle: 'Determines if retrieved evidence is adequate before generation',
      icon: CheckCircle2,
      tag: 'Safety Guardrail',
      details:
        'Before synthesizing a conclusion, the system assesses whether the retrieved passages actually cover the subject. If evidence is missing or below threshold (e.g. ungrounded queries like "working from Antarctica"), the system abstains from answering and marks INSUFFICIENT EVIDENCE.',
      controls: ['Keyword coverage ratio', 'Relevance threshold check', 'Abstention without hallucination']
    },
    {
      id: 'conflict',
      title: '6. Conflict-Aware Reasoning & Resolution',
      subtitle: 'Detects cross-policy or cross-version contradictions',
      icon: GitBranch,
      tag: 'Precedence Logic',
      details:
        'Compares conflicting numerical limits (e.g., 3 days vs 4 days remote work) across policy versions, effective dates, and departmental scopes. If a newer policy explicitly supersedes an older version, the resolution is documented. Unresolved conflicts are escalated.',
      controls: ['Version precedence rules', 'Departmental exception matching', 'Escalation on ambiguity']
    },
    {
      id: 'claims',
      title: '7. Claim-Level Evidence Verification',
      subtitle: 'Verifies every synthesized claim against specific passages',
      icon: Shield,
      tag: 'Fine-Grained Audit',
      details:
        'The proposed answer is parsed into declarative assertions. Each claim is verified against cited policy sections, categorizing them as SUPPORTED, PARTIALLY_SUPPORTED, or NOT_SUPPORTED.',
      controls: ['Sentence-level fact checking', 'Source passage citation', 'Unsupported claim detection']
    },
    {
      id: 'confidence',
      title: '8. Interpretable Evidence Confidence Score',
      subtitle: 'Calculated via formula: w1*R + w2*C + w3*A + w4*V - w5*F',
      icon: Zap,
      tag: 'Interpretable Metric',
      details:
        'Never arbitrary percentages. Formulated from: Retrieval Relevance (R), Evidence Coverage (C), Source Agreement (A), Verification Strength (V), and Conflict Penalty (F). Configurable and documented.',
      controls: ['Documented weights', 'Component breakdown visibility', 'Objective thresholding (70%)']
    },
    {
      id: 'decision',
      title: '9. Decision & Human-in-the-Loop Escalation',
      subtitle: 'High confidence -> ANSWER | Low confidence or conflict -> HUMAN REVIEW',
      icon: ShieldAlert,
      tag: 'Governance',
      details:
        'When confidence falls below threshold or an unresolved contradiction exists, the run is routed to the Human Review Queue with explainable reasons. Reviewers can approve, reject, or request more evidence.',
      controls: ['Explainable escalation reasons', 'Actionable reviewer queue', 'Disposition audit trail']
    },
    {
      id: 'receipt',
      title: '10. Evidence Receipt & Cryptographic Provenance',
      subtitle: 'Downloadable audit trail with SHA-256 provenance hash',
      icon: Workflow,
      tag: 'Audit Provenance',
      details:
        'Every final decision issues an auditable Evidence Receipt recording the question, decision, confidence breakdown, participating specialist agents, cited versions, sections, and SHA-256 hash.',
      controls: ['Downloadable receipt JSON', 'SHA-256 provenance seal', 'End-to-end traceability']
    }
  ]

  const active = nodes.find((n) => n.id === selectedNode) ?? nodes[0]

  return (
    <div className="space-y-6">
      {/* Header section */}
      <section className="rounded-2xl border border-teal-900/20 bg-gradient-to-br from-teal-50/50 via-card to-card p-6 dark:from-teal-950/20">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold text-teal-700 dark:text-teal-400">
                Architectural Identity
              </span>
              <span className="rounded-full bg-teal-100 px-2.5 py-0.5 text-xs font-semibold text-teal-800 dark:bg-teal-900 dark:text-teal-200">
                Research Contribution
              </span>
            </div>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">
              Evidence-Grounded Decision and Escalation Architecture
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              DocuTrust does not merely retrieve documents and generate answers. It establishes an auditable
              evidence-to-decision workflow where specialized agents retrieve tenant-isolated evidence, analyze
              sufficiency, resolve policy contradictions, verify claims, calculate interpretable confidence, and
              escalate uncertain cases to human governance.
            </p>
          </div>
        </div>

        {/* Cross-Cutting Controls Bar */}
        <div className="mt-6 grid grid-cols-2 gap-3 border-t border-border/80 pt-4 sm:grid-cols-4">
          <div className="rounded-xl border bg-card p-3">
            <span className="block text-xs font-semibold text-teal-700 dark:text-teal-400">
              Tenant Isolation
            </span>
            <p className="mt-1 text-xs text-muted-foreground">Retrieval strictly scoped to user tenant. 0 cross-tenant leaks.</p>
          </div>
          <div className="rounded-xl border bg-card p-3">
            <span className="block text-xs font-semibold text-teal-700 dark:text-teal-400">
              Bounded Tools
            </span>
            <p className="mt-1 text-xs text-muted-foreground">Strictly allow-listed tools. No arbitrary code or web execution.</p>
          </div>
          <div className="rounded-xl border bg-card p-3">
            <span className="block text-xs font-semibold text-teal-700 dark:text-teal-400">
              Audit Trail
            </span>
            <p className="mt-1 text-xs text-muted-foreground">Cryptographic SHA-256 evidence receipts for every decision.</p>
          </div>
          <div className="rounded-xl border bg-card p-3">
            <span className="block text-xs font-semibold text-teal-700 dark:text-teal-400">
              Policy Versioning
            </span>
            <p className="mt-1 text-xs text-muted-foreground">Precedence rules prioritize current active policy over v1.</p>
          </div>
        </div>
      </section>

      {/* Interactive Workflow Diagram + Inspector */}
      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        {/* Workflow Diagram */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold text-muted-foreground">
            Pipeline Execution Sequence <span className="font-normal">(Click to Inspect)</span>
          </h3>
          <div className="space-y-2">
            {nodes.map((node, index) => {
              const Icon = node.icon
              const isSelected = selectedNode === node.id

              return (
                <div key={node.id} className="relative">
                  <button
                    onClick={() => setSelectedNode(node.id)}
                    aria-current={isSelected ? 'step' : undefined}
                    className={`w-full text-left rounded-xl border p-4 transition-all flex items-center justify-between gap-4 ${
                      isSelected
                        ? 'border-teal-600 border-l-4 border-l-teal-600 bg-teal-500/10 shadow-sm ring-1 ring-teal-600 dark:border-l-teal-400'
                        : 'border-border bg-card hover:bg-muted/50'
                    }`}
                  >
                    <div className="flex items-center gap-3.5">
                      <span
                        className={`flex size-9 items-center justify-center rounded-xl transition ${
                          isSelected
                            ? 'bg-teal-600 text-white shadow-sm'
                            : 'bg-secondary text-muted-foreground'
                        }`}
                      >
                        <Icon className="size-4.5" aria-hidden="true" />
                      </span>
                      <div>
                        <div className="flex items-center gap-2">
                          <strong className="text-sm font-semibold">{node.title}</strong>
                          <span className="rounded bg-secondary px-2.5 py-0.5 text-xs font-mono text-muted-foreground">
                            {node.tag}
                          </span>
                        </div>
                        <p className="mt-0.5 text-xs text-muted-foreground">{node.subtitle}</p>
                      </div>
                    </div>
                    {isSelected && (
                      <ChevronRight className="size-4 shrink-0 text-teal-600 dark:text-teal-400" aria-hidden="true" />
                    )}
                  </button>
                  {index < nodes.length - 1 && (
                    <div className="flex justify-center py-1">
                      <ArrowDown className="size-3.5 text-muted-foreground/60" aria-hidden="true" />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Selected Stage Deep-Dive Card */}
        <div className="sticky top-20 self-start space-y-4">
          <h3 className="text-xs font-semibold text-muted-foreground">
            Stage Inspection & Controls
          </h3>
          <div className="rounded-2xl border border-teal-900/20 bg-card p-6 shadow-sm">
            <div className="flex items-center gap-3.5 border-b border-border/70 pb-4">
              <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white shadow-sm">
                <active.icon className="size-5" aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1">
                <h4 className="text-base font-semibold leading-snug tracking-tight text-foreground">{active.title}</h4>
                <span className="inline-block mt-0.5 text-xs font-mono font-medium text-teal-700 dark:text-teal-400">{active.tag}</span>
              </div>
            </div>

            <p className="mt-4 text-sm leading-6 text-foreground/90">{active.details}</p>

            <div className="mt-6 border-t pt-4">
              <h5 className="text-xs font-semibold text-muted-foreground">
                Built-in Architectural Controls
              </h5>
              <ul className="mt-2.5 space-y-2 text-xs">
                {active.controls.map((ctrl, i) => (
                  <li key={i} className="flex items-center gap-2 text-foreground/80">
                    <CheckCircle2 className="size-3.5 text-teal-600 shrink-0" aria-hidden="true" />
                    <span>{ctrl}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-6 rounded-xl border border-dashed bg-secondary/50 p-4 text-xs text-muted-foreground">
              <p className="font-semibold text-foreground">Defensible Statement:</p>
              <p className="mt-1 text-xs leading-relaxed text-foreground/85">
                &ldquo;DocuTrust implements a system-level trust loop: claims are generated strictly from evidence,
                verified against chunks, scored via an interpretable formula, and escalated to human review when
                uncertainty exceeds safety tolerances.&rdquo;
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
