import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect, useState, type ReactNode } from 'react'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@web-app/ui/components/breadcrumb'
import { Alert, AlertDescription, AlertTitle } from '@web-app/ui/components/alert'
import { Button } from '@web-app/ui/components/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@web-app/ui/components/empty'
import { Skeleton } from '@web-app/ui/components/skeleton'

import { type DataTablePaginationState } from '@/components/Common/DataTable'
import { KgUnitFilters } from '@/components/Kg/Unit/KgUnitFilters'
import { PendingKgUnits } from '@/components/Kg/Unit/PendingKgUnits'
import { KgUnitTable } from '@/components/Kg/Unit/KgUnitTable'
import { getBatch } from '@/features/batches/batches-api'
import { kgQueryKeys, kgStatuses, listKgByBatch, type KgStatus } from '@/features/kg/kg-api'
import { listEnum, listPage, listQuery } from '@/lib/list-search'

const KG_PAGE_SIZE = 10

export const Route = createFileRoute('/_layout/admin/production/batches/$batchId')({
  component: BatchPage,
  validateSearch: validateBatchPageSearch,
})

type BatchPageSearch = Readonly<{
  page?: number
  q?: string
  unitStatus?: KgStatus
}>

function validateBatchPageSearch(search: Record<string, unknown>): BatchPageSearch {
  return {
    page: listPage(search.page),
    q: listQuery(search.q),
    unitStatus: listEnum(kgStatuses, search.unitStatus),
  }
}

function BatchPage() {
  const { batchId } = Route.useParams()
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const status = search.unitStatus ?? 'all'
  const [queryInput, setQueryInput] = useState(search.q ?? '')
  const pagination: DataTablePaginationState = {
    pageIndex: (search.page ?? 1) - 1,
    pageSize: KG_PAGE_SIZE,
  }
  const batch = useQuery({
    queryFn: () => getBatch(batchId),
    queryKey: ['batches', 'detail', batchId],
  })
  useEffect(() => setQueryInput(search.q ?? ''), [search.q])
  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const query = queryInput.trim()
      if (query !== (search.q ?? '')) {
        navigate({
          replace: true,
          search: (previous) => ({ ...previous, page: undefined, q: query || undefined }),
        })
      }
    }, 300)
    return () => window.clearTimeout(timeout)
  }, [navigate, queryInput, search.q])
  const kg = useQuery({
    placeholderData: keepPreviousData,
    queryFn: () =>
      listKgByBatch({
        batchId,
        page: pagination.pageIndex + 1,
        pageSize: pagination.pageSize,
        query: search.q,
        status: status === 'all' ? undefined : status,
      }),
    queryKey: kgQueryKeys.batch({
      batchId,
      page: pagination.pageIndex + 1,
      pageSize: pagination.pageSize,
      query: search.q,
      status,
    }),
  })

  if (batch.isPending || kg.isPending) return <PendingBatchPage />

  if (batch.isError || kg.isError || !batch.data || !kg.data) {
    return (
      <PageLayout>
        <Alert variant="destructive">
          <AlertTitle>Не удалось загрузить партию</AlertTitle>
          <AlertDescription>
            Проверьте подключение к серверу и повторите попытку.
          </AlertDescription>
        </Alert>
        <Button
          className="mt-4"
          onClick={() => void Promise.all([batch.refetch(), kg.refetch()])}
          variant="outline"
        >
          Повторить
        </Button>
      </PageLayout>
    )
  }

  return (
    <PageLayout batchName={batch.data.name}>
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">{batch.data.name}</h1>
      </div>
      <div className="mt-5">
        <KgUnitFilters
          onQueryChange={setQueryInput}
          onStatusChange={(value) =>
            navigate({
              search: (previous) => ({
                ...previous,
                page: undefined,
                unitStatus: value === 'all' ? undefined : value,
              }),
            })
          }
          query={queryInput}
          status={status}
        />
      </div>
      <div className="mt-4">
        {kg.data.total === 0 ? (
          <EmptyKg hasFilters={Boolean(search.q) || status !== 'all'} />
        ) : (
          <KgUnitTable
            items={kg.data.items}
            loading={kg.isFetching}
            onPaginationChange={(next) =>
              navigate({
                search: (previous) => ({
                  ...previous,
                  page: next.pageIndex === 0 ? undefined : next.pageIndex + 1,
                }),
              })
            }
            pagination={pagination}
            total={kg.data.total}
          />
        )}
      </div>
    </PageLayout>
  )
}

function PageLayout({
  batchName,
  children,
}: Readonly<{ batchName?: string; children: ReactNode }>) {
  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <Link className="hover:text-foreground transition-colors" to="/admin/production/batches">
              Партии
            </Link>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{batchName ?? 'Партия'}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <div className="mt-5">{children}</div>
    </section>
  )
}

function EmptyKg({ hasFilters }: Readonly<{ hasFilters: boolean }>) {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyTitle>{hasFilters ? 'Ничего не найдено' : 'В партии пока нет КГ'}</EmptyTitle>
        <EmptyDescription>
          {hasFilters
            ? 'Попробуйте изменить параметры поиска.'
            : 'Устройства появятся здесь после создания.'}
        </EmptyDescription>
      </EmptyHeader>
    </Empty>
  )
}

function PendingBatchPage() {
  return (
    <PageLayout>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-9 w-80" />
        <Skeleton className="h-5 w-48" />
      </div>
      <div className="mt-6">
        <PendingKgUnits />
      </div>
    </PageLayout>
  )
}
