import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { listUsersOptions } from '@web-app/api-client'
import { useMemo } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { DataLoadError } from '@/components/Common/DataLoadError'
import { ListEmptyState } from '@/components/Common/ListEmptyState'
import { DataTable } from '@/components/Common/DataTable'
import { AddUser } from '@/components/User/Users/AddUser'
import { UserFilters } from '@/components/User/Users/UserFilters'
import PendingUsers from '@/components/User/Users/PendingUsers'
import { createUserColumns } from '@/components/User/Users/columns'
import { type Role, type UserSort, userRoles } from '@/features/users/users-api'
import { activeFilter, activities, type Activity } from '@/lib/activity'
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

const userSorts = ['archived_at', 'name'] as const satisfies readonly UserSort[]

export const Route = createFileRoute('/_layout/admin/user/users')({
  validateSearch: validateUsersSearch,
  component: Users,
  pendingComponent: () => <PendingUsers showPageHeader />,
})

type UsersSearch = ListPageSearch &
  ListSortSearch<UserSort> &
  Readonly<{
    archived?: true
    q?: string
    role?: Role
    status?: Activity
  }>

function validateUsersSearch(search: Record<string, unknown>): UsersSearch {
  const archived = search.archived === true ? true : undefined

  return {
    archived,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    role: listEnum(userRoles, search.role),
    sort: listEnum(userSorts, search.sort),
    status: !archived ? listEnum(activities, search.status) : undefined,
  }
}

function defaultSort(archived: boolean): ListSortDefault<UserSort> {
  return archived ? { desc: true, id: 'archived_at' } : { desc: false, id: 'name' }
}

function Users() {
  const { currentUser } = Route.useRouteContext()
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const role = search.role ?? 'all'
  const status = search.status ?? 'all'
  const pagination = paginationFromSearch(search)
  const sorting = sortingFromSearch(search, defaultSort(archived))
  const [queryInput, setQueryInput] = useSearchInput(search.q, (q) => {
    navigate({ replace: true, search: (previous) => ({ ...previous, page: undefined, q }) })
  })

  const columns = useMemo(
    () => createUserColumns(currentUser.id, archived),
    [currentUser.id, archived],
  )

  const {
    data: users,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    ...listUsersOptions({
      query: {
        ...pageQuery(pagination),
        ...sortQuery(userSorts, sorting, defaultSort(archived)),
        active: activeFilter(archived, status),
        archived,
        roleIn: role !== 'all' ? [role] : undefined,
        searchIgnoreCase: true,
        searchString: search.q,
      },
    }),
    placeholderData: keepPreviousData,
  })

  const hasFilters = Boolean(search.q) || role !== 'all' || (!archived && status !== 'all')

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">Пользователи</h1>
        <AddUser />
      </div>
      <Tabs
        className="mt-5"
        onValueChange={(value) => {
          const nextArchived = value === 'archived'
          navigate({
            search: (previous) => ({
              ...previous,
              archived: nextArchived ? true : undefined,
              order: undefined,
              page: undefined,
              sort: undefined,
              status: nextArchived ? undefined : previous.status,
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
        <UserFilters
          archived={archived}
          onQueryChange={setQueryInput}
          onRoleChange={(value) => {
            navigate({
              search: (previous) => ({
                ...previous,
                page: undefined,
                role: value === 'all' ? undefined : value,
              }),
            })
          }}
          onStatusChange={(value) => {
            navigate({
              search: (previous) => ({
                ...previous,
                page: undefined,
                status: value === 'all' ? undefined : value,
              }),
            })
          }}
          query={queryInput}
          role={role}
          status={status}
        />
      </div>
      <div className="mt-4">
        {!users ? (
          isError ? (
            <DataLoadError onRetry={() => void refetch()} />
          ) : (
            <PendingUsers />
          )
        ) : users.items.length === 0 ? (
          <ListEmptyState
            description={
              hasFilters
                ? 'Попробуйте изменить параметры поиска.'
                : archived
                  ? 'Архивированные пользователи появятся здесь.'
                  : 'Добавьте пользователя, чтобы он появился в списке.'
            }
            title={
              hasFilters ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'Пользователей пока нет'
            }
          />
        ) : (
          <DataTable
            columns={columns}
            data={users.items}
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
                  ...searchFromSorting(userSorts, next, defaultSort(archived)),
                  page: undefined,
                }),
              })
            }}
            pagination={pagination}
            sorting={sorting}
            total={users.total}
          />
        )}
      </div>
    </section>
  )
}
