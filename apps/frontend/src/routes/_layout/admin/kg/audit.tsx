import { createFileRoute } from '@tanstack/react-router'

import { AuditPage } from '@/components/Audit/AuditPage'
import { PendingAudit } from '@/components/Audit/PendingAudit'
import { validateAuditSearch } from '@/features/audit/audit'
import { kgAudit } from '@/features/kg/kg-audit'

export const Route = createFileRoute('/_layout/admin/kg/audit')({
  validateSearch: validateAuditSearch,
  component: KgAudit,
  pendingComponent: () => <PendingAudit section={kgAudit} showPageHeader />,
})

export function KgAudit() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <AuditPage
      navigate={(update) => void navigate({ search: update })}
      search={search}
      section={kgAudit}
    />
  )
}
