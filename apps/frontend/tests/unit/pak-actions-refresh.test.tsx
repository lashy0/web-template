import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useMemo } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DataTable } from '@/components/Common/DataTable'
import { createPakColumns } from '@/components/Pak/Paks/columns'
import { listPaks, type Pak, type PaginatedResult } from '@/features/paks/paks-api'

const { listMock, activeMock, archiveMock, successMock } = vi.hoisted(() => ({
  listMock: vi.fn<typeof listPaks>(),
  activeMock: vi.fn<(id: string, active: boolean) => Promise<Pak>>(),
  archiveMock: vi.fn<(id: string, archived: boolean) => Promise<Pak>>(),
  successMock: vi.fn<() => void>(),
}))

vi.mock('@/features/paks/paks-api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/features/paks/paks-api')>()),
  listPaks: listMock,
  updatePakActive: activeMock,
  updatePakArchived: archiveMock,
}))
vi.mock('@/hooks/useCustomToast', () => ({
  default: () => ({ showErrorToast: vi.fn<() => void>(), showSuccessToast: successMock }),
}))

const pak: Pak = {
  id: 'pak-1',
  code: 'ПАК-01',
  kind: 'otk_line',
  oauthClientId: 'client-1',
  status: 'active',
  archivedAt: null,
  lastSeenAt: null,
}
const page = (items: Pak[]): PaginatedResult<Pak> => ({
  items,
  total: items.length,
  page: 1,
  pageSize: 25,
})

function PakTable({ archived, status }: { archived: boolean; status?: Pak['status'] }) {
  const columns = useMemo(() => createPakColumns(archived), [archived])
  const params = { archived, status, page: 1, pageSize: 25 }
  const { data, isFetching } = useQuery({
    queryKey: ['paks', params],
    queryFn: () => listPaks(params),
  })
  return (
    <DataTable
      columns={columns}
      data={data?.items ?? []}
      total={data?.total ?? 0}
      loading={isFetching}
      pagination={{ pageIndex: 0, pageSize: 25 }}
      sorting={[]}
      onPaginationChange={vi.fn<() => void>()}
      onSortingChange={vi.fn<() => void>()}
    />
  )
}

afterEach(() => {
  cleanup()
  vi.resetAllMocks()
})

describe('PAK actions refresh', () => {
  it.each([
    {
      action: 'Деактивировать',
      initial: pak,
      updated: { ...pak, status: 'inactive' as const },
      nextAction: 'Активировать',
      status: undefined,
    },
    {
      action: 'Активировать',
      initial: { ...pak, status: 'inactive' as const },
      updated: pak,
      nextAction: 'Деактивировать',
      status: undefined,
    },
    {
      action: 'Архивировать',
      initial: pak,
      updated: { ...pak, status: 'inactive' as const, archivedAt: '2026-09-05T10:00:00Z' },
      nextAction: null,
      status: undefined,
    },
    {
      action: 'Восстановить',
      initial: { ...pak, status: 'inactive' as const, archivedAt: '2026-09-05T10:00:00Z' },
      updated: { ...pak, status: 'inactive' as const },
      nextAction: null,
      status: undefined,
    },
    {
      action: 'Деактивировать',
      initial: pak,
      updated: { ...pak, status: 'inactive' as const },
      nextAction: null,
      status: 'active' as const,
    },
  ])(
    'waits for refreshed rows after $action (filter: $status)',
    async ({ action, initial, updated, nextAction, status }) => {
      const user = userEvent.setup()
      const archived = initial.archivedAt !== null
      let resolveRefresh!: (value: PaginatedResult<Pak>) => void
      const refreshPromise = new Promise<PaginatedResult<Pak>>((resolve) => {
        resolveRefresh = resolve
      })
      listMock.mockResolvedValueOnce(page([initial])).mockReturnValueOnce(refreshPromise)
      activeMock.mockResolvedValue(updated)
      archiveMock.mockResolvedValue(updated)
      const client = new QueryClient({
        defaultOptions: { queries: { retry: false, staleTime: Infinity } },
      })
      render(
        <QueryClientProvider client={client}>
          <PakTable archived={archived} status={status} />
        </QueryClientProvider>,
      )

      await user.click(await screen.findByRole('button', { name: 'Действия с ПАК ПАК-01' }))
      await user.click(await screen.findByRole('menuitem', { name: action }))
      await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: action }))
      await waitFor(() => expect(listMock).toHaveBeenCalledTimes(2))
      expect(screen.getByRole('dialog')).toBeVisible()
      expect(within(screen.getByRole('dialog')).getByRole('button', { name: /…$/ })).toBeDisabled()
      expect(successMock).not.toHaveBeenCalled()

      await act(async () => resolveRefresh(page(nextAction ? [updated] : [])))
      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
      expect(successMock).toHaveBeenCalledTimes(1)
      expect(screen.queryAllByText('ПАК-01')).toHaveLength(nextAction ? 1 : 0)
      expect(
        screen.queryAllByText(/^(Активен|Неактивен)$/).map((element) => element.textContent),
      ).toEqual(nextAction ? [updated.status === 'active' ? 'Активен' : 'Неактивен'] : [])
      if (nextAction) {
        await user.click(screen.getByRole('button', { name: 'Действия с ПАК ПАК-01' }))
        await screen.findByRole('menuitem', { name: nextAction })
      }
      expect(screen.queryByRole('menuitem', { name: action })).not.toBeInTheDocument()
      expect(
        screen
          .queryAllByRole('menuitem')
          .map((item) => item.textContent)
          .filter((text) => text === 'Активировать' || text === 'Деактивировать'),
      ).toEqual(nextAction ? [nextAction] : [])
      expect(activeMock.mock.calls.length + archiveMock.mock.calls.length).toBe(1)
      client.clear()
    },
  )
})
