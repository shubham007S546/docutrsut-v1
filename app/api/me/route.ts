import { headers } from 'next/headers'
import { auth } from '@/lib/auth'

export async function GET() {
  const session = await auth.api.getSession({ headers: await headers() }).catch(() => null)
  if (!session?.user) {
    if (process.env.NODE_ENV !== 'production') {
      return Response.json({ user: { name: 'Shubham', email: 'shubhamabhi004@gmail.com' } })
    }
    return Response.json({ user: null }, { status: 401 })
  }
  return Response.json({ user: { name: session.user.name, email: session.user.email } })
}
