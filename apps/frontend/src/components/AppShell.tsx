import type { ReactNode } from 'react'

import type { AuthenticatedUser } from '@/features/auth/auth-api'

import { Header } from './Header'

export function AppShell({
  children,
  currentUser,
}: Readonly<{
  children: ReactNode
  currentUser: AuthenticatedUser
}>) {
  return (
    <div className="flex min-h-svh flex-col bg-muted/20">
      <Header currentUser={currentUser} />
      <main className="mx-auto flex w-full max-w-6xl flex-1 px-4 py-8 sm:px-8 lg:px-12">
        {children}
      </main>
    </div>
  )
}
