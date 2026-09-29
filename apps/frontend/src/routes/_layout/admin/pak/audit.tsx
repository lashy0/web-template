import { createFileRoute } from '@tanstack/react-router'

import { AuditPage } from '@/components/Audit/AuditPage'
import { PendingAudit } from '@/components/Audit/PendingAudit'
import { validateAuditSearch } from '@/features/audit/audit'
import { pakAudit } from '@/features/paks/paks-audit'

export const Route = createFileRoute('/_layout/admin/pak/audit')({
  validateSearch: validateAuditSearch,
  component: PakAudit,
  pendingComponent: () => <PendingAudit section={pakAudit} showPageHeader />,
})

export function PakAudit() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <AuditPage
      navigate={(update) => void navigate({ search: update })}
      search={search}
      section={pakAudit}
    />
  )
}
