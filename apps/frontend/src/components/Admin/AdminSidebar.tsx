import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarTrigger,
  useSidebar,
} from '@web-app/ui/components/sidebar'
import { useState } from 'react'

import type { AuthenticatedUser } from '@/features/auth/auth-api'
import { APP_NAME } from '@/app/config'

import { AdminNavigation } from './AdminNavigation'
import { AdminUserMenu } from './AdminUserMenu'

export function AdminSidebar({ currentUser }: Readonly<{ currentUser: AuthenticatedUser }>) {
  const { isMobile, state } = useSidebar()
  const [isToggleTooltipDismissed, setIsToggleTooltipDismissed] = useState(false)
  const sidebarLabel =
    state === 'expanded' ? 'Свернуть боковую панель' : 'Развернуть боковую панель'

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="group/sidebar-toggle relative flex items-center justify-between gap-2 px-2 py-1 group-data-[collapsible=icon]:justify-center">
          <span className="truncate text-sm font-semibold group-data-[collapsible=icon]:hidden">
            {APP_NAME}
          </span>
          <SidebarTrigger
            aria-label={sidebarLabel}
            className="hidden xl:inline-flex group-data-[collapsible=icon]:flex"
            onClickCapture={() => setIsToggleTooltipDismissed(true)}
            onPointerEnter={() => setIsToggleTooltipDismissed(false)}
          />
          {!isMobile && state === 'collapsed' && !isToggleTooltipDismissed && (
            <span
              role="tooltip"
              className="pointer-events-none absolute top-1/2 left-full z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md bg-foreground px-3 py-1.5 text-xs text-background opacity-0 transition-opacity group-hover/sidebar-toggle:opacity-100 before:absolute before:top-1/2 before:-left-1 before:size-2 before:-translate-y-1/2 before:rotate-45 before:rounded-[2px] before:bg-foreground"
            >
              {sidebarLabel}
            </span>
          )}
        </div>
      </SidebarHeader>
      <SidebarContent className="group-data-[collapsible=icon]:overflow-visible">
        <AdminNavigation />
      </SidebarContent>
      <SidebarFooter>
        <AdminUserMenu user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}
