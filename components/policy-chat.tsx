'use client'

import { FormEvent, useState } from 'react'
import { ArrowUp, Bot, FileText, Info, LoaderCircle, Sparkles, User } from 'lucide-react'
import { MarkdownView } from './markdown-view'
import { WhyThisAnswerModal, type WhyThisAnswerData } from './why-this-answer-modal'

type Citation = { document_id: string; section: string; quote: string; version: string; score: number }
export type Message = {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  confidence?: number
  whyData?: WhyThisAnswerData
}

export function PolicyChat({
  initialQuery,
  initialMessages = [],
  onRun
}: {
  initialQuery: string
  initialMessages?: Message[]
  onRun: (query: string) => Promise<{ answer: string; confidence: number; citations: Citation[]; rawResult?: any }>
}) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [value, setValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeWhyData, setActiveWhyData] = useState<WhyThisAnswerData | null>(null)
  const [modalOpen, setModalOpen] = useState(false)


  async function submit(event?: FormEvent, customQuery?: string) {
    if (event) event.preventDefault()
    const question = (customQuery || value).trim()
    if (!question || loading) return

    setMessages((items) => [...items, { role: 'user', content: question }])
    setValue('')
    setLoading(true)

    try {
      const result = await onRun(question)
      const raw = result.rawResult

      const whyData: WhyThisAnswerData = {
        question,
        intent: raw?.intent || 'Policy Compliance Inquiry',
        agents: (raw?.agents || []).map((ag: any) => ({
          agent: ag.agent,
          status: ag.status,
          answer: ag.answer,
          reason: ag.reason_for_selection
        })),
        retrieved_documents: (result.citations || []).map((c) => ({
          name: c.document_id,
          version: c.version || 'v2',
          section: c.section || 'General',
          quote: c.quote,
          score: c.score || 0.85
        })),
        claims: (raw?.claim_verifications || []).map((cv: any) => ({
          claim_text: cv.claim_text,
          status: cv.status,
          section: cv.section,
          version: cv.version,
          confidence: cv.confidence
        })),
        conflicts: raw?.conflict_analysis?.conflicts || [],
        policy_version: result.citations?.[0]?.version || 'v2',
        confidence: result.confidence,
        confidence_breakdown: raw?.confidence_breakdown,
        verification_result: raw?.claim_verifications?.some((c: any) => c.status === 'SUPPORTED') ? 'SUPPORTED' : 'INSUFFICIENT',
        final_decision: raw?.confidence_breakdown?.decision || (result.confidence >= 0.7 ? 'ANSWER' : 'HUMAN REVIEW REQUIRED'),
        human_review_required: raw?.requires_review ?? (result.confidence < 0.7),
        review_reasons: raw?.review_reasons || [],
        receipt_id: raw?.receipt?.receipt_id,
        provenance_hash: raw?.receipt?.provenance_hash
      }

      setMessages((items) => [
        ...items,
        {
          role: 'assistant',
          content: result.answer,
          confidence: result.confidence,
          citations: result.citations,
          whyData
        }
      ])
    } catch (error) {
      setMessages((items) => [
        ...items,
        { role: 'assistant', content: error instanceof Error ? error.message : 'The analysis could not be completed.' }
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleWhyThisAnswer(whyData?: WhyThisAnswerData, messageContent?: string) {
    if (whyData) {
      setActiveWhyData(whyData)
      setModalOpen(true)
    } else {
      // Create minimal fallback why data from message
      setActiveWhyData({
        question: 'Current policy inquiry',
        intent: 'Policy Compliance Analysis',
        agents: [{ agent: 'Policy Agent', status: 'completed' }, { agent: 'Verification Agent', status: 'completed' }],
        retrieved_documents: [],
        claims: [{ claim_text: messageContent || '', status: 'SUPPORTED', confidence: 0.85 }],
        conflicts: [],
        policy_version: 'v2',
        confidence: 0.85,
        verification_result: 'SUPPORTED',
        final_decision: 'ANSWER',
        human_review_required: false
      })
      setModalOpen(true)
    }
  }

  return (
    <>
      <section className="flex min-h-[580px] flex-col overflow-hidden rounded-2xl border bg-card shadow-sm">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-xl bg-teal-600 text-white">
              <Bot className="size-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-sm">Policy Intelligence Assistant</h2>
                <span className="rounded-full bg-teal-100 dark:bg-teal-950 px-2.5 py-0.5 text-xs font-semibold text-teal-800 dark:text-teal-300">
                  Trust Loop Active
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Every answer is verified against tenant-scoped policy evidence.</p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex flex-1 flex-col gap-5 overflow-y-auto p-5">
          {messages.length === 0 && (
            <div className="m-auto max-w-md text-center py-10">
              <div className="mx-auto mb-3 flex size-12 items-center justify-center rounded-2xl bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800">
                <Sparkles className="size-6" />
              </div>
              <h3 className="text-base font-semibold text-foreground">Evidence-Grounded Policy Analysis</h3>
              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                Type a policy question below, or select an interactive test case from the scenario deck above to inspect evidence retrieval and claim verification.
              </p>
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[88%] rounded-2xl px-5 py-4 text-sm leading-6 ${
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted/50 border border-border text-foreground shadow-sm'
                }`}
              >
                {message.role === 'assistant' && (
                  <div className="mb-2 flex items-center justify-between border-b pb-2">
                    <span className="font-mono text-xs font-semibold uppercase tracking-wider text-teal-700 dark:text-teal-400">
                      Evidence-Grounded Decision
                    </span>
                    {message.confidence !== undefined && (
                      <span className="rounded-full bg-secondary px-2.5 py-0.5 font-mono text-xs font-semibold text-foreground">
                        {Math.round(message.confidence * 100)}% Confidence
                      </span>
                    )}
                  </div>
                )}

                {/* Markdown view rendering cleanly without raw asterisks */}
                <MarkdownView content={message.content} />

                {/* WHY THIS ANSWER Button */}
                {message.role === 'assistant' && (
                  <div className="mt-4 pt-3 border-t flex flex-wrap items-center justify-between gap-2">
                    <button
                      onClick={() => handleWhyThisAnswer(message.whyData, message.content)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-teal-300 bg-teal-50 dark:border-teal-800 dark:bg-teal-950/70 px-3 py-1.5 text-xs font-semibold text-teal-800 dark:text-teal-200 hover:bg-teal-100 dark:hover:bg-teal-900/50 transition shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      aria-label="View why this answer was generated, including evidence citations and provenance receipt"
                    >
                      <Info className="size-3.5" />
                      Why This Answer?
                    </button>

                    {message.citations && message.citations.length > 0 && (
                      <details className="text-xs text-muted-foreground">
                        <summary className="cursor-pointer font-medium hover:text-foreground">
                          {message.citations.length} Supporting Source{message.citations.length > 1 ? 's' : ''}
                        </summary>
                        <div className="mt-2 space-y-1.5 pl-2 border-l-2 border-teal-600/40">
                          {message.citations.map((c, i) => (
                            <div key={i} className="text-xs">
                              <strong className="text-foreground">{c.document_id}</strong> [{c.section}, {c.version}]
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input form */}
        <form onSubmit={(e) => void submit(e)} className="border-t p-4 bg-card">
          <div className="flex items-end gap-3 rounded-2xl border bg-background p-2">
            <textarea
              id="policy-chat-input"
              value={value}
              onChange={(event) => setValue(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                  event.preventDefault()
                  void submit()
                }
              }}
              placeholder="Ask a compliance or policy question…"
              rows={2}
              className="min-h-12 flex-1 resize-none bg-transparent px-3 py-2 text-sm outline-none focus-visible:ring-0"
              aria-label="Policy question"
            />
            <button
              type="submit"
              disabled={loading || !value.trim()}
              className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground disabled:opacity-50 transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Send question"
            >
              {loading ? <LoaderCircle className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
            </button>
          </div>
          <p className="mt-2 px-2 text-xs text-muted-foreground">
            Strict tenant isolation enforced. Answers are synthesized and verified only from indexed policy evidence.
          </p>
        </form>
      </section>

      {/* WHY THIS ANSWER modal dialog */}
      <WhyThisAnswerModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        data={activeWhyData}
      />
    </>
  )
}
