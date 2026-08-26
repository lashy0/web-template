import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

import { dataTablePageSizes, isDataTablePageSize } from './DataTable.constants'
import type { DataTablePaginationState } from './DataTable.types'
import { Button } from '@web-app/ui/components/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@web-app/ui/components/select'
import { Spinner } from '@web-app/ui/components/spinner'

export function DataTablePagination({
  loading,
  onPaginationChange,
  pagination,
  total,
}: Readonly<{
  loading: boolean
  onPaginationChange: (pagination: DataTablePaginationState) => void
  pagination: DataTablePaginationState
  total: number
}>) {
  const pageCount = Math.ceil(total / pagination.pageSize)
  const firstRow = total === 0 ? 0 : pagination.pageIndex * pagination.pageSize + 1
  const lastRow = Math.min((pagination.pageIndex + 1) * pagination.pageSize, total)
  const canGoToPreviousPage = pagination.pageIndex > 0
  const canGoToNextPage = pagination.pageIndex < pageCount - 1

  return (
    <div className="@container flex flex-wrap items-center gap-3 border-t p-4 @[48rem]:gap-4">
      <div className="flex basis-full items-center gap-2 text-sm text-muted-foreground @[48rem]:basis-auto">
        <span>
          Показано {firstRow} – {lastRow} из{' '}
          <span className="font-medium text-foreground">{total}</span> записей
        </span>
        {loading ? <Spinner className="size-4 text-muted-foreground" /> : null}
      </div>
      <div className="flex items-center gap-x-2">
        <p className="text-sm text-muted-foreground">Строк на странице</p>
        <Select
          disabled={loading}
          onValueChange={(value) => {
            const pageSize = Number(value)
            if (isDataTablePageSize(pageSize)) {
              onPaginationChange({ pageIndex: 0, pageSize })
            }
          }}
          value={`${pagination.pageSize}`}
        >
          <SelectTrigger className="h-8 w-[70px] cursor-pointer disabled:cursor-not-allowed">
            <SelectValue placeholder={pagination.pageSize} />
          </SelectTrigger>
          <SelectContent className="min-w-[70px]">
            {dataTablePageSizes.map((size) => (
              <SelectItem key={size} value={`${size}`}>
                {size}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {pageCount > 1 ? (
        <div className="ml-auto flex items-center gap-x-2 @[48rem]:gap-x-1">
          <Button
            className="hidden h-8 w-8 cursor-pointer p-0 disabled:cursor-not-allowed @[48rem]:order-2 @[48rem]:flex"
            disabled={loading || !canGoToPreviousPage}
            onClick={() => onPaginationChange({ ...pagination, pageIndex: 0 })}
            size="sm"
            variant="outline"
          >
            <span className="sr-only">Перейти к первой странице</span>
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            className="order-1 h-8 w-8 cursor-pointer p-0 disabled:cursor-not-allowed @[48rem]:order-3"
            disabled={loading || !canGoToPreviousPage}
            onClick={() =>
              onPaginationChange({ ...pagination, pageIndex: pagination.pageIndex - 1 })
            }
            size="sm"
            variant="outline"
          >
            <span className="sr-only">Перейти к предыдущей странице</span>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="order-2 min-w-12 text-center text-sm text-muted-foreground @[48rem]:order-1 @[48rem]:mr-5">
            <span className="@[48rem]:hidden">
              {pagination.pageIndex + 1} / {pageCount}
            </span>
            <span className="hidden @[48rem]:inline">
              Страница {pagination.pageIndex + 1} из {pageCount}
            </span>
          </span>
          <Button
            className="order-3 h-8 w-8 cursor-pointer p-0 disabled:cursor-not-allowed @[48rem]:order-4"
            disabled={loading || !canGoToNextPage}
            onClick={() =>
              onPaginationChange({ ...pagination, pageIndex: pagination.pageIndex + 1 })
            }
            size="sm"
            variant="outline"
          >
            <span className="sr-only">Перейти к следующей странице</span>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            className="hidden h-8 w-8 cursor-pointer p-0 disabled:cursor-not-allowed @[48rem]:order-5 @[48rem]:flex"
            disabled={loading || !canGoToNextPage}
            onClick={() => onPaginationChange({ ...pagination, pageIndex: pageCount - 1 })}
            size="sm"
            variant="outline"
          >
            <span className="sr-only">Перейти к последней странице</span>
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      ) : null}
    </div>
  )
}
