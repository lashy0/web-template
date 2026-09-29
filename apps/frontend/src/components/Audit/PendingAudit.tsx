import { Skeleton } from '@web-app/ui/components/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@web-app/ui/components/table'

import type { AuditSection } from '@/features/audit/audit'

export function PendingAudit({
  section,
  showPageHeader = false,
}: Readonly<{ section: AuditSection; showPageHeader?: boolean }>) {
  const table = (
    <div aria-label={section.loadingLabel}>
      <Table className="min-w-[45rem] md:min-w-0">
        <TableHeader>
          <TableRow>
            <TableHead>Время</TableHead>
            <TableHead>Пользователь</TableHead>
            <TableHead>Действие</TableHead>
            <TableHead>{section.targetHeader}</TableHead>
            <TableHead className="w-14" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 4 }).map((_, index) => (
            <TableRow key={index}>
              <TableCell>
                <Skeleton className="h-4 w-32" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-28" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-40" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-24" />
              </TableCell>
              <TableCell />
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )

  if (!showPageHeader) {
    return table
  }

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">{section.title}</h1>
      </div>
      <Skeleton className="mt-5 h-8 w-32" />
      <div className="mt-4">{table}</div>
    </section>
  )
}
