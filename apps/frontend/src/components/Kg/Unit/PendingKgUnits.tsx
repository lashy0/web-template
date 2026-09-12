import { Skeleton } from '@web-app/ui/components/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@web-app/ui/components/table'

export function PendingKgUnits() {
  return (
    <div aria-label="Загрузка списка КГ">
      <Table className="min-w-[48rem] md:min-w-0">
        <TableHeader>
          <TableRow>
            <TableHead>DevEUI</TableHead>
            <TableHead>Статус</TableHead>
            <TableHead>Прошивка</TableHead>
            <TableHead>Последняя ОТК</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 5 }).map((_, index) => (
            <TableRow key={index}>
              <TableCell>
                <Skeleton className="h-4 w-44" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-5 w-32 rounded-full" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-20" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-32" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
