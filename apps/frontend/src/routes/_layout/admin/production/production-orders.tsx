import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { listProductionOrdersOptions } from '@web-app/api-client'
import { useMemo } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { DataLoadError } from '@/components/Common/DataLoadError'
import { ListEmptyState } from '@/components/Common/ListEmptyState'
import { DataTable } from '@/components/Common/DataTable'
import { AddProductionOrder } from '@/components/ProductionOrders/AddProductionOrder'
import { ProductionOrderFilters } from '@/components/ProductionOrders/ProductionOrderFilters'
import PendingProductionOrders from '@/components/ProductionOrders/PendingProductionOrders'
import { createProductionOrderColumns } from '@/components/ProductionOrders/columns'
import { type ProductionOrderSort } from '@/features/production-orders/production-order-api'
import {
  listEnum,
  listOrder,
  listPage,
  listPageSize,
  listQuery,
  pageQuery,
  paginationFromSearch,
  searchFromPagination,
  searchFromSorting,
  sortingFromSearch,
  sortQuery,
  useSearchInput,
  type ListPageSearch,
  type ListSortDefault,
  type ListSortSearch,
} from '@/lib/list-search'

const productionOrderSorts = [
  'archived_at',
  'batches_count',
  'created_at',
  'name',
  'total_planned_qty',
] as const satisfies readonly ProductionOrderSort[]

export const Route = createFileRoute('/_layout/admin/production/production-orders')({
  component: ProductionOrders,
  pendingComponent: () => <PendingProductionOrders showPageHeader />,
  validateSearch: validateProductionOrdersSearch,
})

type ProductionOrdersSearch = ListPageSearch &
  ListSortSearch<ProductionOrderSort> &
  Readonly<{ archived?: true; q?: string }>

function validateProductionOrdersSearch(search: Record<string, unknown>): ProductionOrdersSearch {
  return {
    archived: search.archived === true ? true : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    sort: listEnum(productionOrderSorts, search.sort),
  }
}

function defaultSort(archived: boolean): ListSortDefault<ProductionOrderSort> {
  return { desc: true, id: archived ? 'archived_at' : 'created_at' }
}

function ProductionOrders() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const pagination = paginationFromSearch(search)
  const sorting = sortingFromSearch(search, defaultSort(archived))
  const [queryInput, setQueryInput] = useSearchInput(search.q, (q) => {
    navigate({ replace: true, search: (previous) => ({ ...previous, page: undefined, q }) })
  })
  const columns = useMemo(() => createProductionOrderColumns(archived), [archived])

  const { data, isError, isFetching, refetch } = useQuery({
    ...listProductionOrdersOptions({
      query: {
        ...pageQuery(pagination),
        ...sortQuery(productionOrderSorts, sorting, defaultSort(archived)),
        archived,
        searchIgnoreCase: true,
        searchString: search.q,
      },
    }),
    placeholderData: keepPreviousData,
  })

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">Производственные заказы</h1>
        <AddProductionOrder />
      </div>
      <Tabs
        className="mt-5"
        onValueChange={(value) => {
          navigate({
            search: (previous) => ({
              ...previous,
              archived: value === 'archived' ? true : undefined,
              order: undefined,
              page: undefined,
              sort: undefined,
            }),
          })
        }}
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
          <ListEmptyState
            description={
              search.q
                ? 'Попробуйте изменить параметры поиска.'
                : archived
                  ? 'Архивированные заказы появятся здесь.'
                  : 'Добавьте заказ, чтобы он появился в списке.'
            }
            title={search.q ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'Заказов пока нет'}
          />
        ) : (
          <DataTable
            columns={columns}
            data={data.items}
            loading={isFetching}
            onPaginationChange={(next) => {
              navigate({
                search: (previous) => ({ ...previous, ...searchFromPagination(next) }),
              })
            }}
            onSortingChange={(next) => {
              navigate({
                search: (previous) => ({
                  ...previous,
                  ...searchFromSorting(productionOrderSorts, next, defaultSort(archived)),
                  page: undefined,
                }),
              })
            }}
            pagination={pagination}
            sorting={sorting}
            total={data.total}
          />
        )}
      </div>
    </section>
  )
}
