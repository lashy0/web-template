import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { listAuditEntriesOptions } from '@web-app/api-client'
import { useCallback, useMemo, useState } from 'react'

import { AuditEntrySheet } from '@/components/Audit/AuditEntrySheet'
import { createAuditColumns } from '@/components/Audit/columns'
import { PendingAudit } from '@/components/Audit/PendingAudit'
import { AuditFilter } from '@/components/Common/AuditFilter'
import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import { ListEmptyState } from '@/components/Common/ListEmptyState'
import {
  auditQuery,
  auditSorts,
  type AuditEntry,
  type AuditSearch,
  type AuditSection,
} from '@/features/audit/audit'
import { listEnum } from '@/lib/list-search'

/** The audit log of one section, with its period, sorting and pages in the URL. */
export function AuditPage({
  navigate,
  search,
  section,
}: Readonly<{
  navigate: (update: (previous: AuditSearch) => AuditSearch) => void
  search: AuditSearch
  section: AuditSection
}>) {
  const pagination: DataTablePaginationState = {
    pageIndex: (search.page ?? 1) - 1,
    pageSize: search.pageSize ?? (25 as PageSize),
  }
  const sorting = sortingFromSearch(search)
  const period = search.from && search.to ? { from: search.from, to: search.to } : null
  // The entry stays while the sheet closes, so its content does not vanish mid-animation.
  const [entry, setEntry] = useState<AuditEntry | null>(null)
  const [entryOpen, setEntryOpen] = useState(false)
  const openEntry = useCallback((next: AuditEntry) => {
    setEntry(next)
    setEntryOpen(true)
  }, [])
  const columns = useMemo(() => createAuditColumns(section, openEntry), [section, openEntry])
  const {
    data: audit,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    ...listAuditEntriesOptions({ query: auditQuery(section, search) }),
    placeholderData: keepPreviousData,
  })

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">{section.title}</h1>
      </div>
      <div className="mt-5">
        <div className="mb-4 flex">
          <AuditFilter
            onApply={(nextPeriod) => {
              navigate((previous) => ({
                ...previous,
                from: nextPeriod?.from,
                page: undefined,
                to: nextPeriod?.to,
              }))
            }}
            value={period}
          />
        </div>
        {!audit ? (
          isError ? (
            <DataLoadError onRetry={() => void refetch()} />
          ) : (
            <PendingAudit section={section} />
          )
        ) : audit.items.length === 0 && period ? (
          <ListEmptyState
            description="Попробуйте изменить параметры поиска."
            title="Ничего не найдено"
          />
        ) : (
          <DataTable
            columns={columns}
            data={audit.items}
            fixedLayout
            loading={isFetching}
            onRowClick={openEntry}
            onPaginationChange={(next) => {
              navigate((previous) => ({
                ...previous,
                page: next.pageIndex === 0 ? undefined : next.pageIndex + 1,
                pageSize: next.pageSize === 25 ? undefined : (next.pageSize as PageSize),
              }))
            }}
            onSortingChange={(nextSorting) => {
              navigate((previous) => ({
                ...previous,
                ...searchForSorting(nextSorting),
                page: undefined,
              }))
            }}
            pagination={pagination}
            sorting={sorting}
            total={audit.total}
          />
        )}
      </div>
      <AuditEntrySheet
        entry={entry}
        onOpenChange={setEntryOpen}
        open={entryOpen}
        section={section}
      />
    </section>
  )
}

function sortingFromSearch(search: AuditSearch): DataTableSorting {
  const sort = search.sort ?? 'created_at'
  const defaultDesc = sort === 'created_at'
  return [{ id: sort, desc: search.order ? search.order === 'desc' : defaultDesc }]
}

function searchForSorting(sorting: DataTableSorting): Pick<AuditSearch, 'order' | 'sort'> {
  const [current] = sorting
  const sort = listEnum(auditSorts, current?.id) ?? 'created_at'
  const defaultDesc = sort === 'created_at'
  const desc = current?.desc ?? defaultDesc

  return {
    order: desc === defaultDesc ? undefined : desc ? 'desc' : 'asc',
    sort: sort === 'created_at' ? undefined : sort,
  }
}
