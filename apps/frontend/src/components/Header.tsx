import { ChevronsUpDownIcon } from 'lucide-react'

import { Button } from '@web-app/ui/components/button'

import { AccountMenu } from '@/components/Account/AccountMenu'
import { AccountSummary } from '@/components/Account/AccountSummary'
import { APP_NAME } from '@/app/config'
import type { AuthenticatedUser } from '@/features/auth/auth-api'

export function Header({ currentUser }: Readonly<{ currentUser: AuthenticatedUser }>) {
  return (
    <header className="border-b bg-background">
      <div className="mx-auto flex min-h-16 w-full max-w-7xl items-center gap-4 px-4 sm:px-8 lg:px-12">
        <span className="shrink-0 text-sm font-semibold">{APP_NAME}</span>
        <nav aria-label="Основная навигация" className="min-w-0 flex-1" />
        <AccountMenu
          trigger={
            <Button
              aria-label={`Меню пользователя: ${currentUser.name}`}
              className="h-auto min-h-11 max-w-full cursor-pointer justify-start px-2 text-left"
              data-testid="user-menu"
              variant="ghost"
            >
              <AccountSummary compact user={currentUser} />
              <ChevronsUpDownIcon className="hidden shrink-0 text-muted-foreground sm:block" />
            </Button>
          }
          user={currentUser}
        />
      </div>
    </header>
  )
}
