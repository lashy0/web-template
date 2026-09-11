import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import { AddProductionOrder } from '@/components/ProductionOrders/AddProductionOrder'
import { ProductionOrderFilters } from '@/components/ProductionOrders/ProductionOrderFilters'
import PendingProductionOrders from '@/components/ProductionOrders/PendingProductionOrders'
import { createProductionOrderColumns } from '@/components/ProductionOrders/columns'
import {
  listProductionOrders,
  productionOrderQueryKeys,
  type ProductionOrderSort,
  type SortOrder,
} from '@/features/production-orders/production-order-api'
import { listEnum, listOrder, listPage, listPageSize, listQuery } from '@/lib/list-search'

const productionOrderSorts = [
  'archived_at',
  'batches_count',
  'created_at',
  'name',
  'total_planned_qty',
  'updated_at',
] as const satisfies readonly ProductionOrderSort[]

export const Route = createFileRoute('/_layout/admin/production/production-orders')({
  component: ProductionOrders,
  pendingComponent: () => <PendingProductionOrders showPageHeader />,
  validateSearch: validateProductionOrdersSearch,
})

type ProductionOrdersSearch = Readonly<{
  archived?: true
  order?: SortOrder
  page?: number
  pageSize?: PageSize
  q?: string
  sort?: ProductionOrderSort
}>
type ProductionOrdersQuery = Readonly<{
  archived: boolean
  order: SortOrder
  page: number
  pageSize: number
  query?: string
  sort: ProductionOrderSort
}>

export function validateProductionOrdersSearch(
  search: Record<string, unknown>,
): ProductionOrdersSearch {
  return {
    archived: search.archived === true ? true : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    sort: listEnum(productionOrderSorts, search.sort),
  }
}

function ProductionOrders() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const pagination: DataTablePaginationState = {
    pageIndex: (search.page ?? 1) - 1,
    pageSize: search.pageSize ?? (25 as PageSize),
  }
  const sorting = sortingFromSearch(search, archived)
  const [queryInput, setQueryInput] = useState(search.q ?? '')

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

  const params: ProductionOrdersQuery = {
    archived,
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query: search.q,
    ...sortParams(sorting),
  }
  const columns = useMemo(() => createProductionOrderColumns(archived), [archived])
  const { data, isError, isFetching, refetch } = useQuery({
    placeholderData: keepPreviousData,
    queryFn: () => listProductionOrders(params),
    queryKey: productionOrderQueryKeys.list(params),
  })

  function resetList(nextArchived: boolean) {
    navigate({
      search: (previous) => ({
        ...previous,
        archived: nextArchived ? true : undefined,
        order: undefined,
        page: undefined,
        sort: undefined,
      }),
    })
  }

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">Производственные заказы</h1>
        <AddProductionOrder />
      </div>
      <Tabs
        className="mt-5"
        onValueChange={(value) => resetList(value === 'archived')}
        value={archived ? 'archived' : 'current'}
      >
        <TabsList>
          <TabsTrigger value="current">Текущие</TabsTrigger>
          <TabsTrigger value="archived">Архивные</TabsTrigger>
        </TabsList>
      </Tabs>
      <div className="mt-4">
        <ProductionOrderFilters onQueryChange={setQueryInput} query={queryInput} />
      </div>
      <div className="mt-4">
        {!data ? (
          isError ? (
            <DataLoadError onRetry={() => void refetch()} />
          ) : (
            <PendingProductionOrders />
          )
        ) : data.items.length === 0 ? (
          <EmptyState archived={archived} hasQuery={Boolean(search.q)} />
        ) : (
          <DataTable
            columns={columns}
            data={data.items}
            loading={isFetching}
            onPaginationChange={(next) =>
              navigate({
                search: (previous) => ({
                  ...previous,
                  page: next.pageIndex === 0 ? undefined : next.pageIndex + 1,
                  pageSize: next.pageSize === 25 ? undefined : (next.pageSize as PageSize),
                }),
              })
            }
            onSortingChange={(next) =>
              navigate({
                search: (previous) => ({
                  ...previous,
                  ...searchForSorting(next, archived),
                  page: undefined,
                }),
              })
            }
            pagination={pagination}
            sorting={sorting}
            total={data.total}
          />
        )}
      </div>
    </section>
  )
}

function sortParams(
  sorting: DataTableSorting,
): Readonly<{ order: SortOrder; sort: ProductionOrderSort }> {
  const [current] = sorting
  const sort = listEnum(productionOrderSorts, current?.id)
  return sort
    ? { order: current?.desc ? 'desc' : 'asc', sort }
    : { order: 'desc', sort: 'created_at' }
}

function sortingFromSearch(search: ProductionOrdersSearch, archived: boolean): DataTableSorting {
  const defaultSort = archived ? 'archived_at' : 'created_at'
  return [{ desc: search.order ? search.order === 'desc' : true, id: search.sort ?? defaultSort }]
}

function searchForSorting(sorting: DataTableSorting, archived: boolean) {
  const [current] = sorting
  const defaultSort = archived ? 'archived_at' : 'created_at'
  const sort = listEnum(productionOrderSorts, current?.id) ?? defaultSort
  const desc = current?.desc ?? true
  return {
    order: desc ? undefined : 'asc',
    sort: sort === defaultSort ? undefined : sort,
  } as const
}

function EmptyState({ archived, hasQuery }: Readonly<{ archived: boolean; hasQuery: boolean }>) {
  return (
    <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
      <div className="flex flex-col gap-1 text-center">
        <p className="font-medium">
          {hasQuery ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'Заказов пока нет'}
        </p>
        <p className="text-sm text-muted-foreground">
          {hasQuery
            ? 'Попробуйте изменить параметры поиска.'
            : archived
              ? 'Архивированные заказы появятся здесь.'
              : 'Добавьте заказ, чтобы он появился в списке.'}
        </p>
      </div>
    </div>
  )
}
