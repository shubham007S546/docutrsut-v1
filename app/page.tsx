import { headers } from 'next/headers'
import { redirect } from 'next/navigation'
import { auth } from '@/lib/auth'
import { DocuTrustDashboard } from '@/components/docutrust-dashboard'

export default async function Page() {
  let session = null
  try {
    session = await auth.api.getSession({ headers: await headers() })
  } catch {
    session = null
  }
  if (!session?.user && process.env.NODE_ENV === 'production') redirect('/sign-in')
  return <DocuTrustDashboard />
}
