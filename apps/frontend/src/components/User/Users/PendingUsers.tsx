import { Skeleton } from '@web-app/ui/components/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@web-app/ui/components/table'

export default function PendingUsers({
  showPageHeader = false,
}: Readonly<{ showPageHeader?: boolean }>) {
  const table = (
    <div aria-label="Загрузка списка пользователей">
      <Table className="min-w-[45rem] md:min-w-0">
        <TableHeader>
          <TableRow>
            <TableHead>Имя</TableHead>
            <TableHead>Логин</TableHead>
            <TableHead>Роль</TableHead>
            <TableHead>Статус</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 5 }).map((_, index) => (
            <TableRow key={index}>
              <TableCell>
                <Skeleton className="h-4 w-40" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-32" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-5 w-20 rounded-full" />
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Skeleton className="size-2 rounded-full" />
                  <Skeleton className="h-4 w-12" />
                </div>
              </TableCell>
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
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Пользователи</h1>
          <p className="mt-2 text-muted-foreground">Управление учётными записями.</p>
        </div>
        <Skeleton className="h-10 w-32" />
      </div>
      <div className="pt-8">{table}</div>
    </section>
  )
}
