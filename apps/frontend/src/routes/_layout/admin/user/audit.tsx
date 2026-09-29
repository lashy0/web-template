import { createFileRoute } from '@tanstack/react-router'

import { AuditPage } from '@/components/Audit/AuditPage'
import { PendingAudit } from '@/components/Audit/PendingAudit'
import { validateAuditSearch } from '@/features/audit/audit'
import { userAudit } from '@/features/users/users-audit'

export const Route = createFileRoute('/_layout/admin/user/audit')({
  validateSearch: validateAuditSearch,
  component: Audit,
  pendingComponent: () => <PendingAudit section={userAudit} showPageHeader />,
})

export function Audit() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <AuditPage
      navigate={(update) => void navigate({ search: update })}
      search={search}
      section={userAudit}
    />
  )
}
