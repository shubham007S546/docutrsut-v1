'use client'

import React from 'react'
import { FileText, Sparkles } from 'lucide-react'

export function MarkdownView({ content, className = '' }: { content: string; className?: string }) {
  if (!content) return null

  const lines = content.split(/\r?\n/)
  const elements: React.ReactNode[] = []
  let inList = false
  let listItems: string[] = []
  let listType: 'ol' | 'ul' = 'ul'

  const flushList = () => {
    if (inList && listItems.length > 0) {
      if (listType === 'ol') {
        elements.push(
          <ol key={`ol-${elements.length}`} className="my-3 list-decimal space-y-2 pl-5 text-xs sm:text-sm leading-6">
            {listItems.map((item, idx) => (
              <li key={idx} className="text-foreground">
                <InlineMarkdown text={item} />
              </li>
            ))}
          </ol>
        )
      } else {
        elements.push(
          <ul key={`ul-${elements.length}`} className="my-3 list-disc space-y-2 pl-5 text-xs sm:text-sm leading-6">
            {listItems.map((item, idx) => (
              <li key={idx} className="text-foreground">
                <InlineMarkdown text={item} />
              </li>
            ))}
          </ul>
        )
      }
      listItems = []
      inList = false
    }
  }

  let i = 0
  while (i < lines.length) {
    const rawLine = lines[i]
    const trimmed = rawLine.trim()

    if (!trimmed) {
      flushList()
      i++
      continue
    }

    // --- TABLE PARSING ---
    // Detect markdown table header row: line starts with | and next line is separator |---|
    if (
      trimmed.startsWith('|') &&
      trimmed.endsWith('|') &&
      i + 1 < lines.length &&
      lines[i + 1].trim().startsWith('|') &&
      /^\|[\s\-:|]+\|$/.test(lines[i + 1].trim())
    ) {
      flushList()
      const headerLine = trimmed
      const separatorLine = lines[i + 1].trim()
      i += 2 // skip header & separator

      const headers = headerLine
        .slice(1, -1)
        .split('|')
        .map((cell) => cell.trim())

      const rows: string[][] = []
      while (i < lines.length) {
        const rowLine = lines[i].trim()
        if (!rowLine.startsWith('|') || !rowLine.endsWith('|')) {
          break
        }
        const cells = rowLine
          .slice(1, -1)
          .split('|')
          .map((cell) => cell.trim())
        rows.push(cells)
        i++
      }

      elements.push(
        <div key={`table-${elements.length}`} className="my-4 overflow-x-auto rounded-xl border border-teal-200/80 bg-card shadow-sm dark:border-teal-900/60">
          <table className="w-full border-collapse text-left text-xs sm:text-sm">
            <thead className="border-b border-teal-200/80 bg-teal-50/70 text-teal-900 dark:border-teal-900/60 dark:bg-teal-950/40 dark:text-teal-200">
              <tr>
                {headers.map((h, hIdx) => (
                  <th key={hIdx} className="px-4 py-3 font-bold tracking-tight">
                    <InlineMarkdown text={h} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {rows.map((row, rIdx) => (
                <tr key={rIdx} className="transition-colors hover:bg-muted/40 odd:bg-transparent even:bg-muted/15">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-4 py-3.5 align-top leading-relaxed text-foreground">
                      <InlineMarkdown text={cell} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
      continue
    }

    // --- HEADINGS ---
    if (trimmed.startsWith('# ')) {
      flushList()
      elements.push(
        <h1 key={`h1-${elements.length}`} className="mt-4 mb-2 text-lg sm:text-xl font-bold tracking-tight text-foreground">
          <InlineMarkdown text={trimmed.slice(2)} />
        </h1>
      )
      i++
      continue
    }

    if (trimmed.startsWith('## ')) {
      flushList()
      elements.push(
        <h2 key={`h2-${elements.length}`} className="mt-3.5 mb-2 text-base sm:text-lg font-semibold tracking-tight text-foreground">
          <InlineMarkdown text={trimmed.slice(3)} />
        </h2>
      )
      i++
      continue
    }

    if (trimmed.startsWith('### ')) {
      flushList()
      elements.push(
        <h3 key={`h3-${elements.length}`} className="mt-3 mb-1.5 text-sm sm:text-base font-semibold text-foreground">
          <InlineMarkdown text={trimmed.slice(4)} />
        </h3>
      )
      i++
      continue
    }

    // Standalone uppercase headings (e.g. "KEY TAKEAWAYS", "SUMMARY DIRECTIVES")
    if (/^(KEY TAKEAWAYS|SUMMARY|DIRECTIVES|REQUIREMENTS|RECOMMENDATIONS):?$/i.test(trimmed)) {
      flushList()
      elements.push(
        <div key={`h-special-${elements.length}`} className="mt-5 mb-2 flex items-center gap-1.5 font-bold uppercase tracking-wider text-xs text-teal-800 dark:text-teal-300">
          <Sparkles className="size-3.5 text-teal-600 dark:text-teal-400" />
          <span>{trimmed.replace(/:$/, '')}</span>
        </div>
      )
      i++
      continue
    }

    // Bold title line
    if (/^\*\*[^*]+\*\*$/.test(trimmed)) {
      flushList()
      const inner = trimmed.replace(/^\*\*|\*\*$/g, '')
      elements.push(
        <h4 key={`h4-${elements.length}`} className="mt-3.5 mb-1.5 text-xs sm:text-sm font-semibold uppercase tracking-wider text-teal-800 dark:text-teal-300">
          {inner}
        </h4>
      )
      i++
      continue
    }

    // Ordered list (1. item)
    const olMatch = trimmed.match(/^(\d+)\.\s+(.*)$/)
    if (olMatch) {
      if (!inList || listType !== 'ol') {
        flushList()
        inList = true
        listType = 'ol'
      }
      listItems.push(olMatch[2])
      i++
      continue
    }

    // Unordered list (- item or * item)
    const ulMatch = trimmed.match(/^[-*]\s+(.*)$/)
    if (ulMatch) {
      if (!inList || listType !== 'ul') {
        flushList()
        inList = true
        listType = 'ul'
      }
      listItems.push(ulMatch[1])
      i++
      continue
    }

    // Blockquote (> text)
    if (trimmed.startsWith('> ')) {
      flushList()
      elements.push(
        <blockquote key={`quote-${elements.length}`} className="my-2.5 rounded-r-lg border-l-4 border-teal-600 bg-teal-50/40 py-1.5 pl-3 pr-2 italic text-muted-foreground text-xs sm:text-sm dark:bg-teal-950/20">
          <InlineMarkdown text={trimmed.slice(2)} />
        </blockquote>
      )
      i++
      continue
    }

    // Normal paragraph
    flushList()
    elements.push(
      <p key={`p-${elements.length}`} className="my-2 text-xs sm:text-sm leading-relaxed text-foreground">
        <InlineMarkdown text={trimmed} />
      </p>
    )
    i++
  }

  flushList()

  return <div className={`markdown-body space-y-1 ${className}`}>{elements}</div>
}

function InlineMarkdown({ text }: { text: string }) {
  if (!text) return null

  // Normalize HTML <br>, <br/>, <br />
  const lines = text.split(/<br\s*\/?>/i)

  return (
    <>
      {lines.map((lineSegment, lineIdx) => (
        <React.Fragment key={lineIdx}>
          {lineIdx > 0 && <span className="block my-1" />}
          <InlineMarkdownSegment text={lineSegment.trim()} />
        </React.Fragment>
      ))}
    </>
  )
}

function InlineMarkdownSegment({ text }: { text: string }) {
  const parts: React.ReactNode[] = []
  let cursor = 0

  // Regex captures:
  // 1. Full citation: *([Doc.pdf | Section X | vY])* or ([Doc.pdf | Section X | vY])
  // 2. Bold: **text**
  // 3. Inline code: `code`
  const regex = /(\*?\(\[([^\]]+)\]\)\*?|\*\*([^*]+)\*\*|`([^`]+)`)/g
  let match: RegExpExecArray | null

  while ((match = regex.exec(text)) !== null) {
    if (match.index > cursor) {
      parts.push(text.slice(cursor, match.index))
    }

    if (match[2]) {
      // Citation pill: e.g. "03_Civilian_Work_From_Home_Policy.pdf | Section 4.2 | v1"
      const citationContent = match[2]
      parts.push(
        <span
          key={`cite-${match.index}`}
          className="my-0.5 inline-flex items-center gap-1 rounded border border-teal-300/80 bg-teal-50 px-2 py-0.5 font-mono text-[11px] font-semibold text-teal-800 transition hover:bg-teal-100 dark:border-teal-800 dark:bg-teal-950/70 dark:text-teal-200"
          title={`Verified Clause Citation: ${citationContent}`}
        >
          <FileText className="size-3 text-teal-600 dark:text-teal-400 shrink-0" />
          <span>{citationContent}</span>
        </span>
      )
    } else if (match[3]) {
      // Bold
      parts.push(
        <strong key={`b-${match.index}`} className="font-semibold text-foreground">
          {match[3]}
        </strong>
      )
    } else if (match[4]) {
      // Inline code
      parts.push(
        <code key={`c-${match.index}`} className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-teal-700 dark:text-teal-300">
          {match[4]}
        </code>
      )
    }

    cursor = match.index + match[0].length
  }

  if (cursor < text.length) {
    parts.push(text.slice(cursor))
  }

  return <>{parts}</>
}
