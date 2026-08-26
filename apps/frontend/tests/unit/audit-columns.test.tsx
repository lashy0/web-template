import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
} from '@/components/Common/DataTable'
import { auditColumns } from '@/components/User/Audit/columns'
import type { AuditEvent } from '@/features/users/users-api'

const createdUserEvent: AuditEvent = {
  id: 'event-1',
  createdAt: '2026-08-20T13:41:00Z',
  actorType: 'user',
  actorId: 'actor-1',
  actorDisplayName: 'Администратор',
  actorIdentifier: 'admin',
  action: 'user.created',
  entityType: 'user',
  entityId: 'user-1',
  entityDisplayName: 'Тестовый Оператор',
  entityIdentifier: 'test_admin',
  oldData: null,
  newData: { name: 'Тестовый Оператор', login: 'test_admin' },
}

const updatedUserEvent: AuditEvent = {
  ...createdUserEvent,
  action: 'user.updated',
  id: 'event-2',
  newData: { name: 'Старший оператор', role: 'administrator' },
  oldData: { name: 'Тестовый оператор', role: 'operator' },
}

const statusChangedEvent: AuditEvent = {
  ...createdUserEvent,
  action: 'user.active_changed',
  id: 'event-3',
  newData: { active: false },
  oldData: { active: true },
}

describe('audit columns', () => {
  afterEach(cleanup)

  it('shows the account name recorded when the event happened', () => {
    render(
      <DataTable
        columns={auditColumns}
        data={[createdUserEvent]}
        onPaginationChange={vi.fn<(pagination: DataTablePaginationState) => void>()}
        onSortingChange={vi.fn<(sorting: DataTableSorting) => void>()}
        pagination={{ pageIndex: 0, pageSize: 25 }}
        sorting={[]}
        total={1}
      />,
    )

    expect(screen.getByText('Тестовый Оператор')).toBeVisible()
  })

  it('shows only actual changes in a popover', async () => {
    const user = userEvent.setup()
    render(
      <DataTable
        columns={auditColumns}
        data={[updatedUserEvent]}
        onPaginationChange={vi.fn<(pagination: DataTablePaginationState) => void>()}
        onSortingChange={vi.fn<(sorting: DataTableSorting) => void>()}
        pagination={{ pageIndex: 0, pageSize: 25 }}
        sorting={[]}
        total={1}
      />,
    )

    await user.click(screen.getByLabelText('Показать изменения'))

    const title = await screen.findByRole('heading', { name: 'Изменения' })
    const popover = title.parentElement
    expect(popover).not.toBeNull()
    expect(within(popover!).getByText('Имя')).toBeVisible()
    expect(within(popover!).getByText('Тестовый оператор')).toBeVisible()
    expect(within(popover!).getByText('Старший оператор')).toBeVisible()
    expect(within(popover!).getByText('Оператор')).toBeVisible()
    expect(within(popover!).getByText('Администратор')).toBeVisible()
  })

  it('does not show the changes button when there is no diff', () => {
    render(
      <DataTable
        columns={auditColumns}
        data={[createdUserEvent]}
        onPaginationChange={vi.fn<(pagination: DataTablePaginationState) => void>()}
        onSortingChange={vi.fn<(sorting: DataTableSorting) => void>()}
        pagination={{ pageIndex: 0, pageSize: 25 }}
        sorting={[]}
        total={1}
      />,
    )

    expect(screen.queryByLabelText('Показать изменения')).not.toBeInTheDocument()
  })

  it('renders status changes with readable values', async () => {
    const user = userEvent.setup()
    render(
      <DataTable
        columns={auditColumns}
        data={[statusChangedEvent]}
        onPaginationChange={vi.fn<(pagination: DataTablePaginationState) => void>()}
        onSortingChange={vi.fn<(sorting: DataTableSorting) => void>()}
        pagination={{ pageIndex: 0, pageSize: 25 }}
        sorting={[]}
        total={1}
      />,
    )

    await user.click(screen.getByLabelText('Показать изменения'))

    const title = await screen.findByRole('heading', { name: 'Изменение статуса' })
    const popover = title.parentElement
    expect(popover).not.toBeNull()
    expect(within(popover!).getByText('Активен')).toBeVisible()
    expect(within(popover!).getByText('Неактивен')).toBeVisible()
  })
})
