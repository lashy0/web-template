import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DefectGroupActionsMenu } from '@/components/Defects/Groups/DefectGroupActionsMenu'
import { DefectTypeActionsMenu } from '@/components/Defects/Types/DefectTypeActionsMenu'
import { type DefectGroup, type DefectType } from '@/features/defects/defects-api'
import { validateDefectTypeSearch } from '@/routes/_layout/admin/defects/types'

const { updateGroup, updateType } = vi.hoisted(() => ({
  updateGroup: vi.fn<(id: string, archived: boolean) => Promise<DefectGroup>>(),
  updateType: vi.fn<(id: string, archived: boolean) => Promise<DefectType>>(),
}))
vi.mock('@/features/defects/defects-api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/features/defects/defects-api')>()),
  updateDefectGroupArchived: updateGroup,
  updateDefectTypeArchived: updateType,
}))
afterEach(() => {
  cleanup()
  vi.resetAllMocks()
})

describe('Defect management', () => {
  it.each([false, true])('changes group archive state (archived: %s)', async (archived) => {
    const user = userEvent.setup()
    const group = {
      ...archivedGroup,
      archivedAt: archived ? archivedGroup.archivedAt : null,
      activeTypesCount: archived ? 2 : 0,
    }
    updateGroup.mockResolvedValue(group)
    renderMenu(<DefectGroupActionsMenu group={group} />)
    const action = archived ? 'Восстановить' : 'Архивировать'
    await user.click(screen.getByRole('button', { name: 'Действия с группой POWER' }))
    await user.click(await screen.findByRole('menuitem', { name: action }))
    expect(screen.getByRole('heading', { name: action + ' группу?' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: action }))
    expect(updateGroup).toHaveBeenCalledExactlyOnceWith(group.id, !archived)
  })
  it.each([false, true])('changes type archive state (archived: %s)', async (archived) => {
    const user = userEvent.setup()
    const type = { ...archivedType, archivedAt: archived ? archivedType.archivedAt : null }
    updateType.mockResolvedValue(type)
    renderMenu(<DefectTypeActionsMenu type={type} />)
    const action = archived ? 'Восстановить' : 'Архивировать'
    await user.click(screen.getByRole('button', { name: 'Действия с типом POWER_LOSS' }))
    await user.click(await screen.findByRole('menuitem', { name: action }))
    expect(screen.getByRole('heading', { name: action + ' тип?' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: action }))
    expect(updateType).toHaveBeenCalledExactlyOnceWith(type.id, !archived)
  })
  it('keeps a group filter in validated URL search parameters', () => {
    const groupId = '123e4567-e89b-42d3-a456-426614174000'

    expect(validateDefectTypeSearch({ archived: true, group: groupId })).toMatchObject({
      archived: true,
      group: groupId,
    })
    expect(validateDefectTypeSearch({ group: 'not-a-uuid' })).toMatchObject({
      archived: undefined,
      group: undefined,
    })
  })

  it('allows editing an archived group', async () => {
    const user = userEvent.setup()
    renderMenu(<DefectGroupActionsMenu group={archivedGroup} />)

    await user.click(screen.getByRole('button', { name: 'Действия с группой POWER' }))

    expect(await screen.findByRole('menuitem', { name: 'Изменить' })).toBeVisible()
    expect(screen.getByRole('menuitem', { name: 'Восстановить' })).toBeVisible()
  })

  it('allows editing an archived type', async () => {
    const user = userEvent.setup()
    renderMenu(<DefectTypeActionsMenu type={archivedType} />)

    await user.click(screen.getByRole('button', { name: 'Действия с типом POWER_LOSS' }))

    expect(await screen.findByRole('menuitem', { name: 'Изменить' })).toBeVisible()
    expect(screen.getByRole('menuitem', { name: 'Восстановить' })).toBeVisible()
  })
})

function renderMenu(children: React.ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>)
}

const archivedGroup: DefectGroup = {
  activeTypesCount: 0,
  archivedAt: '2026-09-03T10:00:00Z',
  code: 'POWER',
  description: null,
  id: '123e4567-e89b-42d3-a456-426614174000',
  name: 'Питание',
  typesCount: 1,
}

const archivedType: DefectType = {
  archivedAt: '2026-09-03T10:00:00Z',
  code: 'POWER_LOSS',
  description: 'Нет питания.',
  engineerAction: null,
  group: {
    archivedAt: '2026-09-03T10:00:00Z',
    code: 'POWER',
    id: archivedGroup.id,
    name: 'Питание',
  },
  groupId: archivedGroup.id,
  id: '223e4567-e89b-42d3-a456-426614174000',
  name: 'Нет питания',
  possibleCause: null,
}
