import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
} from '@/components/Common/DataTable'
import { pakAuditColumns } from '@/components/Pak/Audit/columns'
import { createPakColumns } from '@/components/Pak/Paks/columns'
import type { Pak, PakAuditEvent } from '@/features/paks/paks-api'

const pagination = { pageIndex: 0, pageSize: 25 }
const tableProps = {
  onPaginationChange: vi.fn<(nextPagination: DataTablePaginationState) => void>(),
  onSortingChange: vi.fn<(nextSorting: DataTableSorting) => void>(),
  pagination,
  sorting: [],
  total: 1,
}

const pak: Pak = {
  archivedAt: null,
  code: 'ПАК-01',
  id: 'pak-1',
  kind: 'otk_line',
  lastSeenAt: null,
  oauthClientId: 'client-1',
  status: 'active',
}

const accessKeyViewedEvent: PakAuditEvent = {
  action: 'pak.access_key_viewed',
  actorDisplayName: 'Администратор',
  actorIdentifier: 'admin',
  actorType: 'user',
  createdAt: '2026-08-27T12:00:00Z',
  entityDisplayName: 'ПАК-01',
  entityIdentifier: 'client-1',
  id: 'event-1',
  newData: null,
  oldData: null,
}

const updatedPakEvent: PakAuditEvent = {
  ...accessKeyViewedEvent,
  action: 'pak.updated',
  id: 'event-2',
  newData: { code: 'ПАК-02', kind: 'engineering' },
  oldData: { code: 'ПАК-01', kind: 'otk_line' },
}

const archivedPakEvent: PakAuditEvent = {
  ...accessKeyViewedEvent,
  action: 'pak.archived',
  id: 'event-3',
  newData: { archived_at: '2026-08-27T12:00:00Z' },
  oldData: { archived_at: null },
}

describe('PAK columns', () => {
  afterEach(cleanup)

  it('shows access-key audit actions in Russian', () => {
    render(<DataTable {...tableProps} columns={pakAuditColumns} data={[accessKeyViewedEvent]} />)

    expect(screen.getByText('Ключ доступа просмотрен')).toBeVisible()
  })

  it('truncates long PAK values and reserves space for the changes button', () => {
    const longValue = 'ПАК-1214444444444444444444444444444444444444444444444444'

    render(
      <DataTable
        {...tableProps}
        columns={pakAuditColumns}
        data={[{ ...updatedPakEvent, entityDisplayName: longValue }]}
      />,
    )

    const pakName = screen.getByText(`${longValue.slice(0, 32)}…`)
    expect(pakName).toHaveClass('truncate')
    expect(pakName.parentElement).toHaveClass('w-80')
    expect(pakAuditColumns.map((column) => column.meta?.widthClassName)).toEqual([
      'w-40 xl:w-[15%]',
      'w-40 xl:w-1/5',
      'w-[230px] xl:w-[31%]',
      'w-40 xl:w-[28%]',
      'w-[58px] xl:w-[6%]',
    ])
  })

  it('shows PAK details changed during editing', async () => {
    const user = userEvent.setup()
    render(<DataTable {...tableProps} columns={pakAuditColumns} data={[updatedPakEvent]} />)

    await user.click(screen.getByLabelText('Показать изменения'))

    const title = await screen.findByRole('heading', { name: 'Изменения' })
    const popover = title.parentElement
    expect(popover).not.toBeNull()
    expect(within(popover!).getByText('Код ПАК')).toBeVisible()
    expect(within(popover!).getByText('ПАК-01')).toBeVisible()
    expect(within(popover!).getByText('ПАК-02')).toBeVisible()
    expect(within(popover!).getByText('Линия ОТК')).toBeVisible()
    expect(within(popover!).getByText('Инженерный')).toBeVisible()
  })

  it('does not show archive or restore timestamps as changes', () => {
    render(<DataTable {...tableProps} columns={pakAuditColumns} data={[archivedPakEvent]} />)

    expect(screen.queryByLabelText('Показать изменения')).not.toBeInTheDocument()
  })

  it('shows that the PAK has not contacted the service yet', () => {
    const columns = createPakColumns(false).filter((column) => column.id !== 'actions')
    render(<DataTable {...tableProps} columns={columns} data={[pak]} />)

    expect(screen.getByText('Ещё не было связи')).toBeVisible()
    expect(screen.queryByText('Нет связи')).not.toBeInTheDocument()
  })
})
