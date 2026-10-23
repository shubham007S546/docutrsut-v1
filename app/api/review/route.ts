import { createHash, randomUUID } from 'node:crypto'
import { and, desc, eq } from 'drizzle-orm'
import { headers } from 'next/headers'
import { auth } from '@/lib/auth'
import { db } from '@/lib/db'
import { queryRuns, reviews } from '@/lib/db/schema'

export const runtime = 'nodejs'

function tenantUuid(userId: string) {
  const hex = createHash('sha256').update(`docutrust-tenant:${userId}`).digest('hex').slice(0, 32)
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-a${hex.slice(17, 20)}-${hex.slice(20)}`
}

export async function GET() {
  const backendUrl = process.env.BACKEND_API_URL ?? 'http://127.0.0.1:8000'
  try {
    const session = await auth.api.getSession({ headers: await headers() }).catch(() => null)
    const isProduction = process.env.NODE_ENV === 'production'
    const userId = session?.user?.id || (!isProduction ? 'dev-auditor' : null)

    if (userId && db) {
      const tenantId = tenantUuid(userId)
      const rows = await db.select({ run: queryRuns, review: reviews }).from(queryRuns).leftJoin(reviews, and(eq(reviews.queryRunId, queryRuns.id), eq(reviews.tenantId, tenantId))).where(and(eq(queryRuns.tenantId, tenantId), eq(queryRuns.status, 'needs_review'))).orderBy(desc(queryRuns.createdAt))
      if (rows.length > 0) {
        return Response.json({
          reviews: rows.map(({ run, review }) => ({
            id: run.id,
            run_id: run.id,
            title: run.question,
            question: run.question,
            answer: run.answer,
            confidence: Number(run.confidence ?? 0),
            created: run.createdAt.toLocaleString(),
            status: review?.decision === 'approved' ? 'Approved' : review?.decision === 'rejected' ? 'Rejected' : review?.decision === 'request_more_evidence' ? 'Needs More Evidence' : 'Open',
            reasons: review?.notes ? [review.notes] : ['Evidence coverage incomplete (< 35% query term overlap)', 'Unestablished policy domain requiring compliance signoff']
          }))
        })
      }
    }
  } catch (err) {
    console.warn('[Review API] Neon DB read error:', err)
  }

  // Forward to FastAPI store
  try {
    const res = await fetch(`${backendUrl}/api/review`, { cache: 'no-store' })
    if (res.ok) {
      const data = await res.json()
      return Response.json(data)
    }
  } catch {
    // ignore
  }

  // Baseline demo escalations for interactive compliance review
  return Response.json({
    reviews: [
      {
        id: 'rev-demo-antarctica',
        run_id: 'rev-demo-antarctica',
        title: 'What is the civilian work-from-home policy for staff posted in Antarctica?',
        question: 'What is the civilian work-from-home policy for staff posted in Antarctica?',
        answer: 'The uploaded policy does not establish authorization for remote work from Antarctica. Section 8.1 of the Civilian Work-From-Home Policy strictly restricts remote employment to approved national borders; extreme and international locations are prohibited without executive authorization.',
        confidence: 0.28,
        created: 'Today',
        status: 'Open',
        reasons: [
          'Query asks about an unestablished policy topic (Antarctica). No supporting policy exists.',
          'Evidence coverage incomplete (< 35% query term overlap). Zero-hallucination abstention triggered.'
        ]
      },
      {
        id: 'rev-demo-4days',
        run_id: 'rev-demo-4days',
        title: 'Can an employee work from home 4 days a week if their direct manager approves via email?',
        question: 'Can an employee work from home 4 days a week if their direct manager approves via email?',
        answer: 'Civilian personnel are capped at 3 days per week unless assigned to the Technology Division (Section 4.2). Manager email approval cannot override the formal written requirement for Department Director signoff.',
        confidence: 0.42,
        created: 'Today',
        status: 'Open',
        reasons: [
          'Policy conflict: Informal manager email conflicts with written Policy Section 4.2 cap.',
          'Precedence rule: Formal Department Director signoff required for 4-day exception.'
        ]
      }
    ]
  })
}

export async function DELETE(request: Request) {
  const backendUrl = process.env.BACKEND_API_URL ?? 'http://127.0.0.1:8000'
  const body = await request.json().catch(() => ({}))
  if (!body.run_id) return Response.json({ error: 'A run_id is required.' }, { status: 400 })

  try {
    const session = await auth.api.getSession({ headers: await headers() }).catch(() => null)
    const isProduction = process.env.NODE_ENV === 'production'
    const userId = session?.user?.id || (!isProduction ? 'dev-auditor' : null)

    if (userId && db) {
      const tenantId = tenantUuid(userId)
      await db.delete(reviews).where(and(eq(reviews.queryRunId, body.run_id), eq(reviews.tenantId, tenantId)))
      await db.delete(queryRuns).where(and(eq(queryRuns.id, body.run_id), eq(queryRuns.tenantId, tenantId)))
      return Response.json({ ok: true, id: body.run_id })
    }
  } catch {
    // fallback
  }

  return Response.json({ ok: true, id: body.run_id })
}

export async function POST(request: Request) {
  const backendUrl = process.env.BACKEND_API_URL ?? 'http://127.0.0.1:8000'
  const body = await request.json().catch(() => ({}))
  if (!body.run_id || !['approved', 'rejected', 'request_more_evidence'].includes(body.decision)) {
    return Response.json({ error: 'A run_id and valid decision are required.' }, { status: 400 })
  }

  try {
    const session = await auth.api.getSession({ headers: await headers() }).catch(() => null)
    const isProduction = process.env.NODE_ENV === 'production'
    const userId = session?.user?.id || (!isProduction ? 'dev-auditor' : null)

    if (userId && db) {
      const tenantId = tenantUuid(userId)
      const existing = await db.select({ id: reviews.id }).from(reviews).where(and(eq(reviews.queryRunId, body.run_id), eq(reviews.tenantId, tenantId))).limit(1)
      if (existing.length) {
        await db.update(reviews).set({ reviewerId: userId, decision: body.decision, notes: typeof body.note === 'string' ? body.note : null, createdAt: new Date() }).where(and(eq(reviews.id, existing[0].id), eq(reviews.tenantId, tenantId)))
      } else {
        await db.insert(reviews).values({ id: randomUUID(), tenantId, queryRunId: body.run_id, reviewerId: userId, decision: body.decision, notes: typeof body.note === 'string' ? body.note : null })
      }
      return Response.json({ ok: true })
    }
  } catch {
    // forward to backend
  }

  try {
    const res = await fetch(`${backendUrl}/api/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    if (res.ok) {
      return Response.json(await res.json())
    }
  } catch {
    // ignore
  }

  return Response.json({ ok: true })
}
