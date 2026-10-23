import { headers } from 'next/headers'
import { auth } from '@/lib/auth'

export async function GET() {
  let session = null
  try {
    session = await auth.api.getSession({ headers: await headers() }).catch(() => null)
  } catch {
    session = null
  }

  if (session?.user) {
    return Response.json({ user: { name: session.user.name, email: session.user.email } })
  }

  return Response.json({ user: { name: 'Shubham', email: 'shubhamabhi004@gmail.com' } })
}
