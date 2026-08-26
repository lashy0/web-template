import type { ReactElement } from 'react'
import { LogOutIcon } from 'lucide-react'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@web-app/ui/components/dropdown-menu'

import type { AuthenticatedUser } from '@/features/auth/auth-api'
import { useAuth } from '@/hooks/useAuth'

import { AccountSummary } from './AccountSummary'

type AccountMenuProps = Readonly<{
  align?: 'center' | 'end' | 'start'
  onMenuAction?: () => void
  side?: 'bottom' | 'left' | 'right' | 'top'
  sideOffset?: number
  trigger: ReactElement
  user: AuthenticatedUser
}>

export function AccountMenu({
  align = 'end',
  onMenuAction,
  side = 'bottom',
  sideOffset = 4,
  trigger,
  user,
}: AccountMenuProps) {
  const { logout } = useAuth()

  const handleLogout = () => {
    onMenuAction?.()
    void logout()
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={trigger} />
      <DropdownMenuContent
        align={align}
        className="w-(--anchor-width) min-w-56 rounded-lg"
        side={side}
        sideOffset={sideOffset}
      >
        <DropdownMenuGroup>
          <DropdownMenuLabel className="p-0 font-normal">
            <AccountSummary details="login" user={user} />
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" onClick={handleLogout}>
            <LogOutIcon />
            Выйти
          </DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
