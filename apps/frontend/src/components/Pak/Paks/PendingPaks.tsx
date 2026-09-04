import { Skeleton } from '@web-app/ui/components/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@web-app/ui/components/table'

export default function PendingPaks({
  showPageHeader = false,
}: Readonly<{ showPageHeader?: boolean }>) {
  const table = (
    <div aria-label="Загрузка списка ПАК">
      <Table className="min-w-[48rem] md:min-w-0">
        <TableHeader>
          <TableRow>
            <TableHead>Код ПАК</TableHead>
            <TableHead>Тип</TableHead>
            <TableHead>Статус</TableHead>
            <TableHead>Последняя связь</TableHead>
            <TableHead>
              <span className="sr-only">Действия</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 5 }).map((_, index) => (
            <TableRow key={index}>
              <TableCell>
                <Skeleton className="h-4 w-36" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-5 w-24 rounded-full" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-24" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-32" />
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
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">ПАК</h1>
          <p className="mt-2 text-muted-foreground">
            Управление программно-аппаратными комплексами.
          </p>
        </div>
        <Skeleton className="h-10 w-36" />
      </div>
      <div className="pt-8">{table}</div>
    </section>
  )
}
