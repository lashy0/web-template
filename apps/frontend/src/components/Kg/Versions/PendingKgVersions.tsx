import { Skeleton } from '@web-app/ui/components/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@web-app/ui/components/table'

export default function PendingKgVersions() {
  return (
    <div aria-label="Загрузка списка версий КГ">
      <Table className="min-w-[40rem] md:min-w-0">
        <TableHeader>
          <TableRow>
            <TableHead>Код</TableHead>
            <TableHead>Название</TableHead>
            <TableHead>
              <span className="sr-only">Действия</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {['one', 'two', 'three', 'four', 'five'].map((key) => (
            <TableRow key={key}>
              <TableCell>
                <Skeleton className="h-4 w-24" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-48" />
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
}
