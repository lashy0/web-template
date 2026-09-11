import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
} from '@/components/Common/DataTable'
import { createBatchColumns } from '@/components/Batches/columns'
import type { Batch } from '@/features/batches/batches-api'
import { validateBatchesSearch } from '@/routes/_layout/admin/production/batches'

const tableProps = {
  onPaginationChange: vi.fn<(nextPagination: DataTablePaginationState) => void>(),
  onSortingChange: vi.fn<(nextSorting: DataTableSorting) => void>(),
  pagination: { pageIndex: 0, pageSize: 25 },
  sorting: [],
  total: 1,
}

const batch: Batch = {
  archivedAt: null,
  canDelete: true,
  completedAt: null,
  createdAt: '2026-09-09T10:00:00Z',
  dayPlanQty: 20,
  description: 'Тестовая партия',
  id: 'batch-1',
  name: 'Партия 00124',
  plannedQty: 100,
  productionOrder: { id: 'order-1', name: 'Тестовый' },
  status: 'IN_PRODUCTION',
  updatedAt: '2026-09-09T10:00:00Z',
}

afterEach(cleanup)

function renderTable(productionOrder: Batch['productionOrder']) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <DataTable
        {...tableProps}
        columns={createBatchColumns()}
        data={[{ ...batch, productionOrder }]}
      />
    </QueryClientProvider>,
  )
}

describe('Batch columns', () => {
  it('keeps the archive tab in the validated search state', () => {
    expect(validateBatchesSearch({ archived: true })).toMatchObject({ archived: true })
    expect(validateBatchesSearch({ archived: 'true' })).toMatchObject({ archived: undefined })
  })

  it('shows the production order as muted secondary text', () => {
    renderTable(batch.productionOrder)

    const order = screen.getByText('Заказ: Тестовый')
    expect(screen.getByText('Партия 00124')).toBeVisible()
    expect(order).toHaveClass('text-muted-foreground')
    expect(screen.getByText('100')).toBeVisible()
    expect(screen.getByText('В производстве')).toBeVisible()
  })

  it('shows an order-less batch and exposes supported actions', async () => {
    const user = userEvent.setup()
    renderTable(null)

    expect(screen.getByText('Без заказа')).toHaveClass('text-muted-foreground')

    await user.click(screen.getByRole('button', { name: 'Действия с партией Партия 00124' }))
    expect(await screen.findByRole('menuitem', { name: 'Редактировать' })).toBeVisible()
    expect(screen.getByRole('menuitem', { name: 'Завершить' })).toBeVisible()
    expect(screen.getByRole('menuitem', { name: 'Архивировать' })).toBeVisible()
    expect(screen.getByRole('menuitem', { name: 'Удалить' })).toBeVisible()
    expect(screen.queryByRole('menuitem', { name: 'Подробнее' })).not.toBeInTheDocument()
  })

  it('shows the deletion warning before sending a delete request for a blocked batch', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <DataTable
          {...tableProps}
          columns={createBatchColumns()}
          data={[{ ...batch, canDelete: false }]}
        />
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Действия с партией Партия 00124' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Удалить' }))

    expect(await screen.findByRole('heading', { name: 'Нельзя удалить партию' })).toBeVisible()
    expect(screen.getByText(/есть производственные операции/i)).toBeVisible()
  })
})
