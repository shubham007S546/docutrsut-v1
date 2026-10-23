import { createHash } from 'node:crypto'
import { headers } from 'next/headers'
import { and, desc, eq } from 'drizzle-orm'
import { auth } from '@/lib/auth'
import { db } from '@/lib/db'
import { queryRuns, reviews } from '@/lib/db/schema'

function tenantUuid(userId: string) {
  const hex = createHash('sha256').update(`docutrust-tenant:${userId}`).digest('hex').slice(0, 32)
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-a${hex.slice(17, 20)}-${hex.slice(20)}`
}

export async function DELETE(request: Request) {
  const body = await request.json().catch(() => null) as { id?: string } | null
  if (!body?.id) return Response.json({ error: 'Run id is required.' }, { status: 400 })
  try {
    const session = await auth.api.getSession({ headers: await headers() }).catch(() => null)
    const isProduction = process.env.NODE_ENV === 'production'
    const userId = session?.user?.id || (!isProduction ? 'dev-auditor' : null)
    if (userId && db) {
      const tenantId = tenantUuid(userId)
      const run = await db.select({ id: queryRuns.id }).from(queryRuns).where(and(eq(queryRuns.id, body.id), eq(queryRuns.tenantId, tenantId))).limit(1)
      if (run.length) {
        await db.delete(reviews).where(and(eq(reviews.queryRunId, body.id), eq(reviews.tenantId, tenantId)))
        await db.delete(queryRuns).where(and(eq(queryRuns.id, body.id), eq(queryRuns.tenantId, tenantId)))
      }
    }
  } catch {
    // fallback
  }
  return Response.json({ ok: true, id: body.id })
}

export async function GET() {
  const backendUrl = process.env.BACKEND_API_URL ?? 'http://127.0.0.1:8000'
  try {
    const session = await auth.api.getSession({ headers: await headers() }).catch(() => null)
    const isProduction = process.env.NODE_ENV === 'production'
    const userId = session?.user?.id || (!isProduction ? 'dev-auditor' : null)
    if (userId && db) {
      const tenantId = tenantUuid(userId)
      const runs = await db.select({ id: queryRuns.id, question: queryRuns.question, answer: queryRuns.answer, confidence: queryRuns.confidence, status: queryRuns.status, evidence: queryRuns.evidence, trace: queryRuns.trace, createdAt: queryRuns.createdAt }).from(queryRuns).where(and(eq(queryRuns.tenantId, tenantId))).orderBy(desc(queryRuns.createdAt)).limit(50)
      if (runs.length > 0) {
        return Response.json({ runs: runs.map((run) => ({ ...run, confidence: run.confidence === null ? 0 : Number(run.confidence), decision: run.status === 'needs_review' ? 'review' : 'answer', evidenceStatus: Array.isArray(run.evidence) && run.evidence.length ? 'grounded' : 'insufficient', created: run.createdAt.toLocaleString() })) })
      }
    }
  } catch {
    // fallback to backend
  }

  try {
    const res = await fetch(`${backendUrl}/api/runs`, { cache: 'no-store' })
    if (res.ok) {
      const data = await res.json()
      const runs = (data.items || []).map((r: any) => ({
        id: r.id,
        question: r.query,
        answer: r.answer,
        confidence: r.confidence ?? 0,
        decision: r.requires_review ? 'review' : 'answer',
        evidenceStatus: r.evidence?.length ? 'grounded' : 'insufficient',
        created: new Date().toLocaleString()
      }))
      return Response.json({ runs })
    }
  } catch {
    // ignore
  }

  return Response.json({ runs: [] })
}
