'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export function AuthForm() {
  const router = useRouter()
  useEffect(() => {
    router.replace('/')
  }, [router])
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <p className="text-sm text-muted-foreground">Opening DocuTrust workspace…</p>
    </div>
  )
}

