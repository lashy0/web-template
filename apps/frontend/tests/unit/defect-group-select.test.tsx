import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DefectGroupSelect } from '@/components/Defects/Types/DefectGroupSelect'
import { type DefectGroup } from '@/features/defects/defects-api'

const { getDefectGroupMock, listDefectGroupsMock } = vi.hoisted(() => ({
  getDefectGroupMock: vi.fn<(groupId: string) => Promise<DefectGroup>>(),
  listDefectGroupsMock: vi.fn<(params: { page: number; pageSize: number; query?: string }) => Promise<{
    items: DefectGroup[]
    page: number
    pageSize: number
    total: number
  }>>(),
}))

vi.mock('@/features/defects/defects-api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/features/defects/defects-api')>()),
  getDefectGroup: getDefectGroupMock,
  listDefectGroups: listDefectGroupsMock,
}))

afterEach(() => {
  cleanup()
  getDefectGroupMock.mockReset()
  listDefectGroupsMock.mockReset()
})

describe('DefectGroupSelect', () => {
  it('loads groups after opening and returns the selected group id', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    listDefectGroupsMock.mockResolvedValue({
      items: [group],
      page: 1,
      pageSize: 100,
      total: 1,
    })

    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <DefectGroupSelect allowClear onChange={onChange} placeholder="Все группы" />
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('combobox', { name: 'Все группы' }))
    await user.click(await screen.findByText('MEX (Механические)'))

    expect(onChange).toHaveBeenCalledWith(group.id)
  })
})

const group: DefectGroup = {
  activeTypesCount: 0,
  archivedAt: null,
  code: 'MEX',
  description: null,
  id: '123e4567-e89b-42d3-a456-426614174000',
  name: 'Механические',
  typesCount: 0,
}
