import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { getBatchOptions, listKgUnitsOptions, type Batch } from '@web-app/api-client'
import type { ReactNode } from 'react'

import { Alert, AlertDescription, AlertTitle } from '@web-app/ui/components/alert'
import { Badge } from '@web-app/ui/components/badge'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@web-app/ui/components/breadcrumb'
import { Button } from '@web-app/ui/components/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@web-app/ui/components/empty'
import { Skeleton } from '@web-app/ui/components/skeleton'

import { KgUnitFilters } from '@/components/Kg/Unit/KgUnitFilters'
import { KgUnitTable } from '@/components/Kg/Unit/KgUnitTable'
import { PendingKgUnits } from '@/components/Kg/Unit/PendingKgUnits'
import { batchStatusLabels } from '@/features/batches/batches-api'
import { kgOtkStatuses, kgStates } from '@/features/kg/kg-api'
import { formatDevEui, formatDevEuiPrefix } from '@/features/kg/kg-prefix-format'
import { listEnum, listPage, listQuery, useSearchInput } from '@/lib/list-search'

const KG_PAGE_SIZE = 10

export const Route = createFileRoute('/_layout/admin/production/batches/$batchId')({
  component: BatchPage,
  validateSearch: validateBatchPageSearch,
})

type BatchPageSearch = Readonly<{
  otk?: (typeof kgOtkStatuses)[number]
  page?: number
  q?: string
  state?: (typeof kgStates)[number]
}>

function validateBatchPageSearch(search: Record<string, unknown>): BatchPageSearch {
  return {
    otk: listEnum(kgOtkStatuses, search.otk),
    page: listPage(search.page),
    q: listQuery(search.q),
    state: listEnum(kgStates, search.state),
  }
}

function BatchPage() {
  const { batchId } = Route.useParams()
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const state = search.state ?? 'all'
  const otkStatus = search.otk ?? 'all'
  const pagination = { pageIndex: (search.page ?? 1) - 1, pageSize: KG_PAGE_SIZE }
  const [queryInput, setQueryInput] = useSearchInput(search.q, (q) => {
    navigate({ replace: true, search: (previous) => ({ ...previous, page: undefined, q }) })
  })

  const batch = useQuery(getBatchOptions({ path: { batch_id: batchId } }))
  const units = useQuery({
    ...listKgUnitsOptions({
      query: {
        batchIdIn: [batchId],
        currentPage: pagination.pageIndex + 1,
        otkStatusIn: otkStatus !== 'all' ? [otkStatus] : undefined,
        pageSize: KG_PAGE_SIZE,
        searchIgnoreCase: true,
        searchString: search.q,
        stateIn: state !== 'all' ? [state] : undefined,
      },
    }),
    placeholderData: keepPreviousData,
  })

  if (batch.isPending) return <PendingBatchPage />

  if (batch.isError) {
    return (
      <PageLayout>
        <LoadError onRetry={() => void batch.refetch()} title="Не удалось загрузить партию" />
      </PageLayout>
    )
  }

  return (
    <PageLayout batchName={batch.data.name}>
      <BatchSummary batch={batch.data} />
      <div className="mt-8">
        <KgUnitFilters
          onOtkStatusChange={(value) => {
            navigate({
              search: (previous) => ({
                ...previous,
                otk: value === 'all' ? undefined : value,
                page: undefined,
              }),
            })
          }}
          onQueryChange={setQueryInput}
          onStateChange={(value) => {
            navigate({
              search: (previous) => ({
                ...previous,
                page: undefined,
                state: value === 'all' ? undefined : value,
              }),
            })
          }}
          otkStatus={otkStatus}
          query={queryInput}
          state={state}
        />
      </div>
      <div className="mt-4">
        {!units.data ? (
          units.isError ? (
            <LoadError onRetry={() => void units.refetch()} title="Не удалось загрузить КГ" />
          ) : (
            <PendingKgUnits />
          )
        ) : units.data.total === 0 ? (
          <EmptyKg hasFilters={Boolean(search.q) || state !== 'all' || otkStatus !== 'all'} />
        ) : (
          <KgUnitTable
            items={units.data.items}
            loading={units.isFetching}
            onPaginationChange={(next) => {
              navigate({
                search: (previous) => ({
                  ...previous,
                  page: next.pageIndex === 0 ? undefined : next.pageIndex + 1,
                }),
              })
            }}
            pagination={pagination}
            total={units.data.total}
          />
        )}
      </div>
    </PageLayout>
  )
}

function BatchSummary({ batch }: Readonly<{ batch: Batch }>) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-semibold tracking-tight">{batch.name}</h1>
        <Badge variant="secondary">{batchStatusLabels[batch.status]}</Badge>
        {batch.archivedAt ? <Badge variant="outline">В архиве</Badge> : null}
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-4 text-sm sm:grid-cols-4">
        <Detail label="План">{batch.plannedQty.toLocaleString('ru-RU')}</Detail>
        <Detail label="Принято">{batch.receivedQty.toLocaleString('ru-RU')}</Detail>
        <Detail label="Упаковано">{batch.packedQty.toLocaleString('ru-RU')}</Detail>
        <Detail label="Отгружено">{batch.shippedQty.toLocaleString('ru-RU')}</Detail>
        <Detail label="Производственный заказ">{batch.productionOrder?.name ?? '—'}</Detail>
        <Detail label="Версия КГ">{batch.kgVersion?.code ?? '—'}</Detail>
        <Detail label="DevEUI-префикс">
          <code>{formatDevEuiPrefix(batch.kgPrefix.prefix)}</code>
        </Detail>
        <Detail label="Диапазон DevEUI">
          <code className="text-xs">
            {formatDevEui(batch.firstDevEui)} — {formatDevEui(batch.lastDevEui)}
          </code>
        </Detail>
      </dl>
    </div>
  )
}

function Detail({ children, label }: Readonly<{ children: ReactNode; label: string }>) {
  return (
    <div className="min-w-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="mt-1 truncate font-medium">{children}</dd>
    </div>
  )
}

function LoadError({ onRetry, title }: Readonly<{ onRetry: () => void; title: string }>) {
  return (
    <>
      <Alert variant="destructive">
        <AlertTitle>{title}</AlertTitle>
        <AlertDescription>Проверьте подключение к серверу и повторите попытку.</AlertDescription>
      </Alert>
      <Button className="mt-4" onClick={onRetry} variant="outline">
        Повторить
      </Button>
    </>
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
            <Link
              className="hover:text-foreground transition-colors"
              to="/admin/production/batches"
            >
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
        <EmptyTitle>{hasFilters ? 'Ничего не найдено' : 'В партии нет КГ'}</EmptyTitle>
        <EmptyDescription>
          {hasFilters
            ? 'Попробуйте изменить параметры поиска.'
            : 'КГ партии регистрируются при её создании.'}
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
