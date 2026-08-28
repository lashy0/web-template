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
import { Button } from '@web-app/ui/components/button'

export const Route = createFileRoute('/_layout/admin/user/users')({
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

function defaultUserSorting(archived: boolean): DataTableSorting {
  return [{ id: archived ? 'archived_at' : 'name', desc: archived }]
}

function userSortParams(sorting: DataTableSorting): Readonly<{ order: SortOrder; sort: UserSort }> {
  const [current] = sorting
  if (current?.id === 'login' || current?.id === 'archived_at' || current?.id === 'name') {
    return { order: current.desc ? 'desc' : 'asc', sort: current.id }
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
  const [pagination, setPagination] = useState<DataTablePaginationState>({
    pageIndex: 0,
    pageSize: 25 as PageSize,
  })
  const [archived, setArchived] = useState(false)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [role, setRole] = useState<Role | 'all'>('all')
  const [authState, setAuthState] = useState<AuthState | 'all'>('all')
  const [sorting, setSorting] = useState<DataTableSorting>(() => defaultUserSorting(false))

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setPagination((current) => ({ ...current, pageIndex: 0 }))
      setDebouncedQuery(query.trim())
    }, 300)

    return () => window.clearTimeout(timeout)
  }, [query])

  function handleRoleChange(value: Role | 'all') {
    setPagination((current) => ({ ...current, pageIndex: 0 }))
    setRole(value)
  }

  function handleAuthStateChange(value: AuthState | 'all') {
    setPagination((current) => ({ ...current, pageIndex: 0 }))
    setAuthState(value)
  }

  function handleQueryChange(value: string) {
    setPagination((current) => ({ ...current, pageIndex: 0 }))
    setQuery(value)
  }

  const hasFilters = debouncedQuery !== '' || role !== 'all' || (!archived && authState !== 'all')

  const columns = useMemo(
    () => createUserColumns(currentUser.id, archived),
    [currentUser.id, archived],
  )

  const usersQuery = {
    archived,
    authState: !archived && authState !== 'all' ? authState : undefined,
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query: debouncedQuery || undefined,
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
                  setPagination((current) => ({ ...current, pageIndex: 0 }))
                  setArchived(false)
                  setSorting(defaultUserSorting(false))
                }}
              >
                Текущие
              </Button>

              <Button
                className="cursor-pointer"
                size="sm"
                variant={archived ? 'secondary' : 'ghost'}
                onClick={() => {
                  setPagination((current) => ({ ...current, pageIndex: 0 }))
                  setArchived(true)
                  setSorting(defaultUserSorting(true))
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
              query={query}
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
            onPaginationChange={setPagination}
            onSortingChange={(nextSorting) => {
              setPagination((current) => ({ ...current, pageIndex: 0 }))
              setSorting(nextSorting)
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
