import { Link as RouterLink, useRouterState } from '@tanstack/react-router'
import {
  BugIcon,
  ChevronRightIcon,
  ClipboardListIcon,
  CpuIcon,
  RadioTowerIcon,
  UsersIcon,
} from 'lucide-react'
import { useEffect, useState } from 'react'

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@web-app/ui/components/collapsible'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from '@web-app/ui/components/dropdown-menu'
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

const sections = [
  {
    label: 'Пользователи',
    icon: UsersIcon,
    items: [
      { label: 'Список', to: '/admin/user/users' },
      { label: 'Аудит', to: '/admin/user/audit' },
    ],
  },
  {
    label: 'ПАК',
    icon: CpuIcon,
    items: [
      { label: 'Список', to: '/admin/pak/paks' },
      { label: 'Аудит', to: '/admin/pak/audit' },
    ],
  },
  {
    label: 'Производство',
    icon: ClipboardListIcon,
    items: [
      { label: 'Заказы', to: '/admin/production/production-orders' },
      { label: 'Партии', to: '/admin/production/batches' },
    ],
  },
  {
    label: 'Дефекты',
    icon: BugIcon,
    items: [
      { label: 'Группы', to: '/admin/defects/groups' },
      { label: 'Типы', to: '/admin/defects/types' },
      { label: 'Аудит', to: '/admin/defects/audit' },
    ],
  },
  {
    label: 'КГ',
    icon: RadioTowerIcon,
    items: [
      { label: 'Префиксы', to: '/admin/kg/prefixes' },
      { label: 'Версии', to: '/admin/kg/versions' },
      { label: 'Аудит', to: '/admin/kg/audit' },
    ],
  },
] as const

export function AdminNavigation() {
  const { isMobile, setOpenMobile, state } = useSidebar()
  const currentPath = useRouterState().location.pathname
  const isCollapsedDesktop = state === 'collapsed' && !isMobile
  const [openSection, setOpenSection] = useState<string | null>(null)

  useEffect(() => {
    setOpenSection(null)
  }, [isCollapsedDesktop, currentPath])

  const handleMenuClick = () => {
    if (isMobile) setOpenMobile(false)
  }

  return (
    <SidebarGroup>
      <SidebarGroupLabel>Управление</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {sections.map((section) => {
            const isActive = section.items.some((item) => item.to === currentPath)
            const Icon = section.icon

            if (isCollapsedDesktop) {
              return (
                <SidebarMenuItem key={section.label}>
                  <DropdownMenu
                    modal={false}
                    open={openSection === section.label}
                    onOpenChange={(open) => {
                      setOpenSection((current) =>
                        open ? section.label : current === section.label ? null : current,
                      )
                    }}
                  >
                    <DropdownMenuTrigger
                      openOnHover
                      delay={150}
                      closeDelay={200}
                      render={<SidebarMenuButton isActive={isActive} aria-label={section.label} />}
                    >
                      <Icon />
                      <span className="sr-only">{section.label}</span>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      side="right"
                      align="start"
                      sideOffset={8}
                      className="w-48 data-closed:hidden"
                    >
                      <DropdownMenuGroup>
                        <DropdownMenuLabel>{section.label}</DropdownMenuLabel>
                        {section.items.map((item) => (
                          <DropdownMenuItem
                            key={item.to}
                            className="aria-[current=page]:bg-sidebar-accent aria-[current=page]:text-sidebar-accent-foreground"
                            render={
                              <RouterLink
                                to={item.to}
                                search={{}}
                                aria-current={currentPath === item.to ? 'page' : undefined}
                              />
                            }
                          >
                            {item.label}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuGroup>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </SidebarMenuItem>
              )
            }

            return (
              <Collapsible
                key={section.label}
                className="group/collapsible"
                defaultOpen={isActive}
                render={<SidebarMenuItem />}
              >
                <SidebarMenuButton isActive={isActive} render={<CollapsibleTrigger />}>
                  <Icon />
                  <span>{section.label}</span>
                  <ChevronRightIcon className="ml-auto transition-transform group-data-open/collapsible:rotate-90" />
                </SidebarMenuButton>
                <CollapsibleContent>
                  <SidebarMenuSub>
                    {section.items.map((item) => (
                      <SidebarMenuSubItem key={item.to}>
                        <SidebarMenuSubButton
                          isActive={currentPath === item.to}
                          render={<RouterLink to={item.to} search={{}} onClick={handleMenuClick} />}
                        >
                          {item.label}
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                    ))}
                  </SidebarMenuSub>
                </CollapsibleContent>
              </Collapsible>
            )
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}
