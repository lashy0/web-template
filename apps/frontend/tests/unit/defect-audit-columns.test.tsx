import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
} from '@/components/Common/DataTable'
import { defectAuditColumns } from '@/components/Defects/Audit/columns'
import type { DefectAuditEvent } from '@/features/defects/defects-api'

const tableProps = {
  onPaginationChange: vi.fn<(nextPagination: DataTablePaginationState) => void>(),
  onSortingChange: vi.fn<(nextSorting: DataTableSorting) => void>(),
  pagination: { pageIndex: 0, pageSize: 25 },
  sorting: [],
  total: 1,
}

const archivedGroupEvent: DefectAuditEvent = {
  action: 'defect_group.archived',
  actorDisplayName: 'Администратор',
  actorIdentifier: 'admin',
  actorType: 'user',
  createdAt: '2026-09-03T08:00:00Z',
  entityDisplayName: 'Общие',
  entityIdentifier: 'ОБ',
  entityType: 'defect_group',
  id: 'event-1',
  newData: { archived_at: '2026-09-03T08:00:00Z' },
  oldData: { archived_at: null },
}

const updatedTypeWithDescription: DefectAuditEvent = {
  ...archivedGroupEvent,
  action: 'defect_type.updated',
  entityDisplayName: 'Механические',
  entityIdentifier: 'МЕХ',
  entityType: 'defect_type',
  id: 'event-2',
  newData: { description: 'Новое подробное описание типа дефекта.' },
  oldData: { description: 'Предыдущее подробное описание типа дефекта.' },
}

describe('defect audit columns', () => {
  afterEach(cleanup)

  it('does not show archive or restore timestamps as changes', () => {
    render(<DataTable {...tableProps} columns={defectAuditColumns} data={[archivedGroupEvent]} />)

    expect(screen.queryByLabelText('Показать изменения')).not.toBeInTheDocument()
  })

  it('opens long-text changes in a sheet', () => {
    render(
      <DataTable
        {...tableProps}
        columns={defectAuditColumns}
        data={[updatedTypeWithDescription]}
      />,
    )

    fireEvent.click(screen.getByLabelText('Показать изменения'))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Предыдущее подробное описание типа дефекта.')).toBeInTheDocument()
    expect(screen.getByText('Новое подробное описание типа дефекта.')).toBeInTheDocument()
  })
})
