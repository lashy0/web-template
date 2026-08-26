import {
  Outlet,
  createFileRoute,
  redirect,
  useRouter,
  useRouterState,
} from '@tanstack/react-router'
import { TooltipProvider } from '@web-app/ui/components/tooltip'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@web-app/ui/components/sidebar'

import { AdminSidebar } from '@/components/Admin/AdminSidebar'
import PendingAudit from '@/components/User/Audit/PendingAudit'
import PendingUsers from '@/components/User/Users/PendingUsers'

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
  const router = useRouter()
  const isNavigating = useRouterState({ select: (state) => state.isLoading })
  const pendingUsersRoute = router.matchRoute({ to: '/admin/user/users' }, { pending: true })
  const pendingAuditRoute = router.matchRoute({ to: '/admin/user/audit' }, { pending: true })

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
            {isNavigating && pendingUsersRoute ? (
              <PendingUsers showPageHeader />
            ) : isNavigating && pendingAuditRoute ? (
              <PendingAudit showPageHeader />
            ) : (
              <Outlet />
            )}
          </div>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}
