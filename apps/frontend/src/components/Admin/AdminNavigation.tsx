import { Link as RouterLink, useRouterState } from '@tanstack/react-router'
import { BugIcon, ChevronRightIcon, CpuIcon, UsersIcon } from 'lucide-react'
import { useState } from 'react'

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@web-app/ui/components/collapsible'
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  useSidebar,
} from '@web-app/ui/components/sidebar'

export function AdminNavigation() {
  const { isMobile, setOpenMobile, state } = useSidebar()
  const [isUsersTooltipDismissed, setIsUsersTooltipDismissed] = useState(false)
  const [isPaksTooltipDismissed, setIsPaksTooltipDismissed] = useState(false)
  const [isDefectsTooltipDismissed, setIsDefectsTooltipDismissed] = useState(false)
  const router = useRouterState()
  const currentPath = router.location.pathname
  const isUsersSectionActive =
    currentPath === '/admin/user/users' || currentPath === '/admin/user/audit'
  const isPaksSectionActive =
    currentPath === '/admin/pak/paks' || currentPath === '/admin/pak/audit'
  const isDefectsSectionActive =
    currentPath === '/admin/defects/groups' ||
    currentPath === '/admin/defects/types' ||
    currentPath === '/admin/defects/audit'
  const isCollapsedDesktop = state === 'collapsed' && !isMobile

  const handleMenuClick = () => {
    if (isMobile) {
      setOpenMobile(false)
    }
  }

  return (
    <SidebarGroup>
      <SidebarGroupLabel>Управление</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          <Collapsible
            className="group/collapsible"
            defaultOpen={isUsersSectionActive}
            render={<SidebarMenuItem />}
          >
            <SidebarMenuButton
              isActive={isUsersSectionActive}
              render={
                isCollapsedDesktop ? (
                  <RouterLink
                    to="/admin/user/users"
                    onClick={() => {
                      setIsUsersTooltipDismissed(true)
                      handleMenuClick()
                    }}
                    onPointerEnter={() => setIsUsersTooltipDismissed(false)}
                  />
                ) : (
                  <CollapsibleTrigger />
                )
              }
            >
              <UsersIcon />
              <span>Пользователи</span>
              <ChevronRightIcon className="ml-auto transition-transform group-data-open/collapsible:rotate-90" />
            </SidebarMenuButton>
            {isCollapsedDesktop && !isUsersTooltipDismissed && (
              <span
                role="tooltip"
                className="pointer-events-none absolute top-1/2 left-full z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md bg-foreground px-3 py-1.5 text-xs text-background opacity-0 transition-opacity group-hover/menu-item:opacity-100 before:absolute before:top-1/2 before:-left-1 before:size-2 before:-translate-y-1/2 before:rotate-45 before:rounded-[2px] before:bg-foreground"
              >
                Пользователи
              </span>
            )}
            <CollapsibleContent>
              <SidebarMenuSub>
                <SidebarMenuSubItem>
                  <SidebarMenuSubButton
                    isActive={currentPath === '/admin/user/users'}
                    render={<RouterLink to="/admin/user/users" onClick={handleMenuClick} />}
                  >
                    Список
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
                <SidebarMenuSubItem>
                  <SidebarMenuSubButton
                    isActive={currentPath === '/admin/user/audit'}
                    render={<RouterLink to="/admin/user/audit" onClick={handleMenuClick} />}
                  >
                    Аудит
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
              </SidebarMenuSub>
            </CollapsibleContent>
          </Collapsible>
          <Collapsible
            className="group/collapsible"
            defaultOpen={isPaksSectionActive}
            render={<SidebarMenuItem />}
          >
            <SidebarMenuButton
              isActive={isPaksSectionActive}
              render={
                isCollapsedDesktop ? (
                  <RouterLink
                    to="/admin/pak/paks"
                    onClick={() => {
                      setIsPaksTooltipDismissed(true)
                      handleMenuClick()
                    }}
                    onPointerEnter={() => setIsPaksTooltipDismissed(false)}
                  />
                ) : (
                  <CollapsibleTrigger />
                )
              }
            >
              <CpuIcon />
              <span>ПАК</span>
              <ChevronRightIcon className="ml-auto transition-transform group-data-open/collapsible:rotate-90" />
            </SidebarMenuButton>
            {isCollapsedDesktop && !isPaksTooltipDismissed && (
              <span
                role="tooltip"
                className="pointer-events-none absolute top-1/2 left-full z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md bg-foreground px-3 py-1.5 text-xs text-background opacity-0 transition-opacity group-hover/menu-item:opacity-100 before:absolute before:top-1/2 before:-left-1 before:size-2 before:-translate-y-1/2 before:rotate-45 before:rounded-[2px] before:bg-foreground"
              >
                ПАК
              </span>
            )}
            <CollapsibleContent>
              <SidebarMenuSub>
                <SidebarMenuSubItem>
                  <SidebarMenuSubButton
                    isActive={currentPath === '/admin/pak/paks'}
                    render={<RouterLink to="/admin/pak/paks" onClick={handleMenuClick} />}
                  >
                    Список
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
                <SidebarMenuSubItem>
                  <SidebarMenuSubButton
                    isActive={currentPath === '/admin/pak/audit'}
                    render={<RouterLink to="/admin/pak/audit" onClick={handleMenuClick} />}
                  >
                    Аудит
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
              </SidebarMenuSub>
            </CollapsibleContent>
          </Collapsible>
          <Collapsible
            className="group/collapsible"
            defaultOpen={isDefectsSectionActive}
            render={<SidebarMenuItem />}
          >
            <SidebarMenuButton
              isActive={isDefectsSectionActive}
              render={
                isCollapsedDesktop ? (
                  <RouterLink
                    to="/admin/defects/groups"
                    onClick={() => {
                      setIsDefectsTooltipDismissed(true)
                      handleMenuClick()
                    }}
                    onPointerEnter={() => setIsDefectsTooltipDismissed(false)}
                  />
                ) : (
                  <CollapsibleTrigger />
                )
              }
            >
              <BugIcon />
              <span>Дефекты</span>
              <ChevronRightIcon className="ml-auto transition-transform group-data-open/collapsible:rotate-90" />
            </SidebarMenuButton>
            {isCollapsedDesktop && !isDefectsTooltipDismissed && (
              <span
                role="tooltip"
                className="pointer-events-none absolute top-1/2 left-full z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md bg-foreground px-3 py-1.5 text-xs text-background opacity-0 transition-opacity group-hover/menu-item:opacity-100 before:absolute before:top-1/2 before:-left-1 before:size-2 before:-translate-y-1/2 before:rotate-45 before:rounded-[2px] before:bg-foreground"
              >
                Дефекты
              </span>
            )}
            <CollapsibleContent>
              <SidebarMenuSub>
                <SidebarMenuSubItem>
                  <SidebarMenuSubButton
                    isActive={currentPath === '/admin/defects/groups'}
                    render={<RouterLink to="/admin/defects/groups" onClick={handleMenuClick} />}
                  >
                    Группы
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
                <SidebarMenuSubItem>
                  <SidebarMenuSubButton
                    isActive={currentPath === '/admin/defects/types'}
                    render={<RouterLink to="/admin/defects/types" onClick={handleMenuClick} />}
                  >
                    Типы
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
                <SidebarMenuSubItem>
                  <SidebarMenuSubButton
                    isActive={currentPath === '/admin/defects/audit'}
                    render={<RouterLink to="/admin/defects/audit" onClick={handleMenuClick} />}
                  >
                    Аудит
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
              </SidebarMenuSub>
            </CollapsibleContent>
          </Collapsible>
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}
