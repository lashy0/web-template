import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'

import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import { AddUser } from '@/components/User/Users/AddUser'
import { UserFilters } from '@/components/User/Users/UserFilters'
import PendingUsers from '@/components/User/Users/PendingUsers'
import { createUserColumns } from '@/components/User/Users/columns'
import {
  listUsers,
  type AuthState,
  type Role,
  type SortOrder,
  type UserSort,
} from '@/features/users/users-api'
import { listEnum, listOrder, listPage, listPageSize, listQuery } from '@/lib/list-search'
import { Button } from '@web-app/ui/components/button'

const authStates = ['active', 'inactive'] as const satisfies readonly AuthState[]
const userRoles = [
  'administrator',
  'manager',
  'engineer',
  'packer',
  'operator',
] as const satisfies readonly Role[]
const userTableSorts = ['archived_at', 'login', 'name'] as const satisfies readonly UserSort[]

export const Route = createFileRoute('/_layout/admin/user/users')({
  validateSearch: validateUsersSearch,
  component: Users,
  pendingComponent: () => <PendingUsers showPageHeader />,
})

type UsersQuery = Readonly<{
  archived: boolean
  authState?: AuthState
  page: number
  pageSize: number
  query?: string
  role?: Role
  order: SortOrder
  sort: UserSort
}>

function userSortParams(sorting: DataTableSorting): Readonly<{ order: SortOrder; sort: UserSort }> {
  const [current] = sorting
  const sort = listEnum(userTableSorts, current?.id)
  if (sort) {
    return { order: current?.desc ? 'desc' : 'asc', sort }
  }
  return { order: 'asc', sort: 'name' }
}

function getUsersQueryOptions(params: UsersQuery) {
  return {
    queryFn: () => listUsers(params),
    queryKey: ['users', params],
  }
}

function Users() {
  const { currentUser } = Route.useRouteContext()
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const pagination: DataTablePaginationState = {
    pageIndex: (search.page ?? 1) - 1,
    pageSize: search.pageSize ?? (25 as PageSize),
  }
  const role = search.role ?? 'all'
  const authState = search.authState ?? 'all'
  const sorting = sortingFromSearch(search, archived)
  const [queryInput, setQueryInput] = useState(search.q ?? '')

  useEffect(() => {
    setQueryInput(search.q ?? '')
  }, [search.q])

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

  function handleRoleChange(value: Role | 'all') {
    navigate({
      search: (previous) => ({
        ...previous,
        page: undefined,
        role: value === 'all' ? undefined : value,
      }),
    })
  }

  function handleAuthStateChange(value: AuthState | 'all') {
    navigate({
      search: (previous) => ({
        ...previous,
        authState: value === 'all' ? undefined : value,
        page: undefined,
      }),
    })
  }

  function handleQueryChange(value: string) {
    setQueryInput(value)
  }

  const hasFilters = Boolean(search.q) || role !== 'all' || (!archived && authState !== 'all')

  const columns = useMemo(
    () => createUserColumns(currentUser.id, archived),
    [currentUser.id, archived],
  )

  const usersQuery = {
    archived,
    authState: !archived && authState !== 'all' ? authState : undefined,
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query: search.q,
    role: role !== 'all' ? role : undefined,
    ...userSortParams(sorting),
  }

  const {
    data: users,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    ...getUsersQueryOptions(usersQuery),
    placeholderData: keepPreviousData,
  })

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Пользователи</h1>
          <p className="mt-2 text-muted-foreground">Управление учётными записями.</p>
        </div>
        <AddUser />
      </div>
      <div className="pt-8">
        <div className="@container mb-4">
          <div className="flex flex-col gap-3 @[56rem]:flex-row @[56rem]:items-center @[56rem]:justify-between">
            <div className="flex shrink-0 items-center gap-1">
              <Button
                className="cursor-pointer"
                size="sm"
                variant={!archived ? 'secondary' : 'ghost'}
                onClick={() => {
                  navigate({
                    search: (previous) => ({
                      ...previous,
                      archived: undefined,
                      order: undefined,
                      page: undefined,
                      sort: undefined,
                    }),
                  })
                }}
              >
                Текущие
              </Button>

              <Button
                className="cursor-pointer"
                size="sm"
                variant={archived ? 'secondary' : 'ghost'}
                onClick={() => {
                  navigate({
                    search: (previous) => ({
                      ...previous,
                      archived: true,
                      authState: undefined,
                      order: undefined,
                      page: undefined,
                      sort: undefined,
                    }),
                  })
                }}
              >
                Архивные
              </Button>
            </div>

            <UserFilters
              archived={archived}
              authState={authState}
              onAuthStateChange={handleAuthStateChange}
              onQueryChange={handleQueryChange}
              onRoleChange={handleRoleChange}
              query={queryInput}
              role={role}
            />
          </div>
        </div>
        {!users ? (
          isError ? (
            <DataLoadError onRetry={() => void refetch()} />
          ) : (
            <PendingUsers />
          )
        ) : users.items.length === 0 ? (
          <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
            <div className="text-center">
              <p className="font-medium">
                {hasFilters
                  ? 'Ничего не найдено'
                  : archived
                    ? 'Архив пуст'
                    : 'Пользователей пока нет'}
              </p>

              <p className="mt-1 text-sm text-muted-foreground">
                {hasFilters
                  ? 'Попробуйте изменить параметры поиска.'
                  : archived
                    ? 'Архивированные пользователи появятся здесь.'
                    : 'Добавьте пользователя, чтобы он появился в списке.'}
              </p>
            </div>
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={users.items}
            loading={isFetching}
            onPaginationChange={(next) => {
              navigate({
                search: (previous) => ({
                  ...previous,
                  page: next.pageIndex === 0 ? undefined : next.pageIndex + 1,
                  pageSize: next.pageSize === 25 ? undefined : (next.pageSize as PageSize),
                }),
              })
            }}
            onSortingChange={(nextSorting) => {
              navigate({
                search: (previous) => ({
                  ...previous,
                  ...searchForSorting(nextSorting, archived),
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

type UsersSearch = Readonly<{
  archived?: true
  authState?: AuthState
  order?: SortOrder
  page?: number
  pageSize?: PageSize
  q?: string
  role?: Role
  sort?: UserSort
}>

export function validateUsersSearch(search: Record<string, unknown>): UsersSearch {
  const archived = search.archived === true ? true : undefined

  return {
    archived,
    authState: !archived ? listEnum(authStates, search.authState) : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    role: listEnum(userRoles, search.role),
    sort: listEnum(userTableSorts, search.sort),
  }
}

function sortingFromSearch(search: UsersSearch, archived: boolean): DataTableSorting {
  return [
    {
      desc: search.order ? search.order === 'desc' : archived,
      id: search.sort ?? (archived ? 'archived_at' : 'name'),
    },
  ]
}

function searchForSorting(sorting: DataTableSorting, archived: boolean) {
  const [current] = sorting
  const sort = listEnum(userTableSorts, current?.id) ?? (archived ? 'archived_at' : 'name')
  const desc = current?.desc ?? archived
  const defaultSort = archived ? 'archived_at' : 'name'

  return {
    order: desc === archived && sort === defaultSort ? undefined : desc ? 'desc' : 'asc',
    sort: sort === defaultSort ? undefined : sort,
  } as const
}
