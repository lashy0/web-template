import { createFileRoute } from '@tanstack/react-router'

import { AuditPage } from '@/components/Audit/AuditPage'
import { PendingAudit } from '@/components/Audit/PendingAudit'
import { validateAuditSearch } from '@/features/audit/audit'
import { defectAudit } from '@/features/defects/defects-audit'

export const Route = createFileRoute('/_layout/admin/defects/audit')({
  validateSearch: validateAuditSearch,
  component: DefectAudit,
  pendingComponent: () => <PendingAudit section={defectAudit} showPageHeader />,
})

export function DefectAudit() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <AuditPage
      navigate={(update) => void navigate({ search: update })}
      search={search}
      section={defectAudit}
    />
  )
}
