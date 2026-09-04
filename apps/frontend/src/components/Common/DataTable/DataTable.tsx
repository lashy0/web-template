import {
  flexRender,
  functionalUpdate,
  rowPaginationFeature,
  rowSortingFeature,
  tableFeatures,
  useTable,
  type ColumnDef,
  type RowData,
} from '@tanstack/react-table'
import { useRef } from 'react'

import { DataTableColumnHeader } from './DataTableColumnHeader'
import { DataTablePagination } from './DataTablePagination'
import type { DataTablePaginationState, DataTableSorting } from './DataTable.types'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@web-app/ui/components/table'

type DataTableColumnMeta = Readonly<{
  widthClassName?: string
}>

const dataTableFeatures = tableFeatures({
  columnMeta: {} as DataTableColumnMeta,
  rowPaginationFeature,
  rowSortingFeature,
})

export type DataTableColumn<Row extends RowData> = ColumnDef<typeof dataTableFeatures, Row>

export function DataTable<Row extends RowData>({
  columns,
  data,
  fixedLayout = false,
  getRowClassName,
  loading = false,
  onPaginationChange,
  onSortingChange,
  pagination,
  sorting,
  total,
}: Readonly<{
  columns: readonly DataTableColumn<Row>[]
  data: readonly Row[]
  fixedLayout?: boolean
  getRowClassName?: (row: Row) => string | undefined
  loading?: boolean
  onPaginationChange: (pagination: DataTablePaginationState) => void
  onSortingChange: (sorting: DataTableSorting) => void
  pagination: DataTablePaginationState
  sorting: DataTableSorting
  total: number
}>) {
  const tableRef = useRef<HTMLDivElement>(null)
  const scrollToTable = () => {
    const shouldReduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    tableRef.current?.scrollIntoView?.({
      behavior: shouldReduceMotion ? 'auto' : 'smooth',
      block: 'start',
    })
  }
  const table = useTable(
    {
      columns,
      data,
      enableMultiSort: false,
      enableSorting: true,
      enableSortingRemoval: false,
      features: dataTableFeatures,
      manualPagination: true,
      manualSorting: true,
      onPaginationChange: (updater) => {
        const next = functionalUpdate(updater, pagination)
        onPaginationChange({
          pageIndex: next.pageSize === pagination.pageSize ? next.pageIndex : 0,
          pageSize: next.pageSize,
        })
      },
      onSortingChange: (updater) => {
        onSortingChange(functionalUpdate(updater, sorting))
      },
      rowCount: total,
      state: { pagination, sorting },
    },
    (state) => ({ pagination: state.pagination, sorting: state.sorting }),
  )
  const tableClassName = fixedLayout
    ? `min-w-[48rem] ${loading ? 'opacity-60 ' : ''}table-fixed border-collapse`
    : `min-w-[45rem] md:min-w-0 ${loading ? 'opacity-60 ' : ''}xl:border-separate xl:border-spacing-0`

  return (
    <div aria-busy={loading} className="flex flex-col gap-4" ref={tableRef}>
      <Table className={tableClassName} containerClassName="xl:overflow-visible">
        <TableHeader className="xl:bg-transparent">
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow className="hover:bg-transparent" key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const canSort = header.column.getCanSort()
                const sortDirection = header.column.getIsSorted()

                return (
                  <TableHead
                    aria-sort={
                      canSort
                        ? sortDirection === 'asc'
                          ? 'ascending'
                          : sortDirection === 'desc'
                            ? 'descending'
                            : 'none'
                        : undefined
                    }
                    className={`xl:sticky xl:top-0 xl:z-10 xl:bg-muted xl:first:rounded-tl-lg xl:last:rounded-tr-lg ${header.column.columnDef.meta?.widthClassName ?? ''}`}
                    key={header.id}
                  >
                    {header.isPlaceholder ? null : canSort ? (
                      <DataTableColumnHeader
                        disabled={loading}
                        onSortingToggle={() => {
                          header.column.toggleSorting()
                          scrollToTable()
                        }}
                        sortDirection={sortDirection}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </DataTableColumnHeader>
                    ) : (
                      flexRender(header.column.columnDef.header, header.getContext())
                    )}
                  </TableHead>
                )
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow className={getRowClassName?.(row.original)} key={row.id}>
                {row.getAllCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow className="hover:bg-transparent">
              <TableCell
                className="h-32 text-center text-muted-foreground"
                colSpan={columns.length}
              >
                Нет данных.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <DataTablePagination
        loading={loading}
        onPaginationChange={(next) => {
          onPaginationChange(next)
          if (next.pageIndex !== pagination.pageIndex) {
            scrollToTable()
          }
        }}
        pagination={pagination}
        total={total}
      />
    </div>
  )
}
