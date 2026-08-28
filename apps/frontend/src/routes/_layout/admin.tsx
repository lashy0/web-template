import { Outlet, createFileRoute, redirect } from '@tanstack/react-router'
import { TooltipProvider } from '@web-app/ui/components/tooltip'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@web-app/ui/components/sidebar'

import { AdminSidebar } from '@/components/Admin/AdminSidebar'

export const Route = createFileRoute('/_layout/admin')({
  beforeLoad: ({ context }) => {
    if (context.currentUser.role !== 'administrator') {
      throw redirect({ to: '/' })
    }
  },
  component: AdminRoute,
})

function AdminRoute() {
  const { currentUser } = Route.useRouteContext()

  return (
    <TooltipProvider>
      <SidebarProvider>
        <AdminSidebar currentUser={currentUser} />
        <SidebarInset>
          <SidebarTrigger
            size="icon-lg"
            className="fixed top-2 left-2 z-20 bg-sidebar text-sidebar-foreground shadow-sm hover:bg-sidebar-accent hover:text-sidebar-accent-foreground xl:hidden"
          />
          <div className="min-w-0 flex-1 bg-background">
            <Outlet />
          </div>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}
