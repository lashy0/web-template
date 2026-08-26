import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  DataTable,
  type DataTableColumn,
  type DataTablePaginationState,
  type DataTableSorting,
} from '@/components/Common/DataTable'

type Row = { name: string }

const columns: readonly DataTableColumn<Row>[] = [
  {
    accessorKey: 'name',
    enableSorting: true,
    header: 'Название',
    sortDescFirst: false,
  },
]

const columnsWithUnsortable: readonly DataTableColumn<Row>[] = [
  ...columns,
  {
    cell: () => null,
    enableSorting: false,
    header: 'Действия',
    id: 'actions',
  },
]

const data: readonly Row[] = Array.from({ length: 11 }, (_, index) => ({
  name: `Запись ${index + 1}`,
}))

const firstPage: DataTablePaginationState = { pageIndex: 0, pageSize: 5 }

function renderTable(overrides: Partial<React.ComponentProps<typeof DataTable<Row>>> = {}) {
  return render(
    <DataTable
      columns={columns}
      data={data.slice(0, 5)}
      onPaginationChange={vi.fn<(pagination: DataTablePaginationState) => void>()}
      onSortingChange={vi.fn<(sorting: DataTableSorting) => void>()}
      pagination={firstPage}
      sorting={[]}
      total={data.length}
      {...overrides}
    />,
  )
}

describe('DataTable', () => {
  afterEach(cleanup)

  it('requests the next server page when the next-page button is pressed', async () => {
    const user = userEvent.setup()
    const onPaginationChange = vi.fn<(pagination: DataTablePaginationState) => void>()
    const scrollIntoView = vi.fn<() => void>()
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    })

    renderTable({ onPaginationChange })

    expect(screen.getByText('Запись 1')).toBeVisible()
    expect(screen.getByText('1 / 3')).toBeVisible()

    await user.click(screen.getByRole('button', { name: 'Перейти к следующей странице' }))

    expect(onPaginationChange).toHaveBeenCalledWith({ pageIndex: 1, pageSize: 5 })
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' })
  })

  it('resets the server page when the page size changes', async () => {
    const user = userEvent.setup()
    const onPaginationChange = vi.fn<(pagination: DataTablePaginationState) => void>()

    renderTable({ onPaginationChange, pagination: { pageIndex: 1, pageSize: 5 } })

    await user.click(screen.getByRole('combobox'))
    await user.click(screen.getByRole('option', { name: '10' }))

    expect(onPaginationChange).toHaveBeenCalledWith({ pageIndex: 0, pageSize: 10 })
  })

  it('shows loading state without replacing the current rows', () => {
    renderTable({ loading: true })

    expect(screen.getByText('Запись 1')).toBeVisible()
    expect(screen.getByLabelText('Загрузка')).toBeVisible()
    expect(screen.getByRole('table').parentElement?.parentElement).toHaveAttribute(
      'aria-busy',
      'true',
    )
    expect(screen.getByRole('button', { name: 'Название' })).toBeDisabled()
  })

  it('sets aria-sort only on sortable columns', () => {
    renderTable({ columns: columnsWithUnsortable })

    expect(screen.getByRole('columnheader', { name: 'Название' })).toHaveAttribute(
      'aria-sort',
      'none',
    )
    expect(screen.getByRole('columnheader', { name: 'Действия' })).not.toHaveAttribute('aria-sort')
  })

  it('renders an empty state', () => {
    renderTable({ data: [], total: 0 })

    expect(screen.getByText('Нет данных.')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Перейти к следующей странице' })).toBeNull()
  })

  it('requests the opposite server sort direction when a sorted header is pressed', async () => {
    const user = userEvent.setup()
    const onSortingChange = vi.fn<(sorting: DataTableSorting) => void>()

    renderTable({ onSortingChange, sorting: [{ id: 'name', desc: false }] })

    await user.click(screen.getByRole('button', { name: 'Название' }))

    expect(onSortingChange).toHaveBeenCalledWith([{ id: 'name', desc: true }])
    expect(screen.getByRole('columnheader', { name: 'Название' })).toHaveAttribute(
      'aria-sort',
      'ascending',
    )
  })

  it('uses a sticky header only in the desktop layout', () => {
    const { container } = renderTable()

    expect(screen.getByRole('columnheader', { name: 'Название' })).toHaveClass(
      'xl:sticky',
      'xl:top-0',
    )
    expect(container.querySelector('[data-slot="table-container"]')).toHaveClass(
      'xl:overflow-visible',
    )
  })
})
