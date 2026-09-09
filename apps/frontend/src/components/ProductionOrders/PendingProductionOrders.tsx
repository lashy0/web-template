import { Skeleton } from '@web-app/ui/components/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@web-app/ui/components/table'

export default function PendingProductionOrders({
  showPageHeader = false,
}: Readonly<{ showPageHeader?: boolean }>) {
  const rows = ['one', 'two', 'three', 'four', 'five'] as const
  const table = (
    <div aria-label="Загрузка списка производственных заказов">
      <Table className="min-w-[42rem] md:min-w-0">
        <TableHeader>
          <TableRow>
            <TableHead>Название</TableHead>
            <TableHead>Партий</TableHead>
            <TableHead>Общий план</TableHead>
            <TableHead>
              <span className="sr-only">Действия</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row}>
              <TableCell>
                <Skeleton className="h-4 w-48" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-12" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-16" />
              </TableCell>
              <TableCell>
                <Skeleton className="ml-auto h-8 w-8" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )

  if (!showPageHeader) return table

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">Производственные заказы</h1>
        <Skeleton className="h-8 w-24" />
      </div>
      <Skeleton className="mt-5 h-9 w-44 rounded-full" />
      <Skeleton className="mt-4 h-8 w-80" />
      <div className="mt-4">{table}</div>
    </section>
  )
}
