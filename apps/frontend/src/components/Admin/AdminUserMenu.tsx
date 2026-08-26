import { ChevronsUpDownIcon } from 'lucide-react'
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from '@web-app/ui/components/sidebar'

import { AccountMenu } from '@/components/Account/AccountMenu'
import { AccountSummary } from '@/components/Account/AccountSummary'
import type { AuthenticatedUser } from '@/features/auth/auth-api'

export function AdminUserMenu({ user }: Readonly<{ user: AuthenticatedUser }>) {
  const { isMobile, setOpenMobile } = useSidebar()

  const handleMenuClick = () => {
    if (isMobile) setOpenMobile(false)
  }
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <AccountMenu
          onMenuAction={handleMenuClick}
          side={isMobile ? 'bottom' : 'right'}
          trigger={
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
              data-testid="user-menu"
            >
              <AccountSummary user={user} />
              <ChevronsUpDownIcon className="ml-auto text-muted-foreground" />
            </SidebarMenuButton>
          }
          user={user}
        />
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
