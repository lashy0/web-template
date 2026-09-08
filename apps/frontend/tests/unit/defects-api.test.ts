import { describe, expect, it, vi } from 'vitest'

import { getDefectGroup, updateDefectGroup } from '@/features/defects/defects-api'

vi.mock('@web-app/api-client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@web-app/api-client')>()),
  defectsGetDefectGroup: vi.fn<() => Promise<{ data: typeof group }>>(async () => ({
    data: group,
  })),
  defectsUpdateDefectGroup: vi.fn<() => Promise<{ data: typeof group }>>(async () => ({
    data: group,
  })),
}))

const group = {
  id: 'a471c958-48c0-42dc-b72b-9cedab7f94bd',
  code: 'POWER',
  name: 'Power',
  description: null,
  archived_at: null,
  created_at: '2026-09-08T10:00:00Z',
  updated_at: '2026-09-08T10:00:00Z',
  active_types_count: 2,
  types_count: 5,
}

describe('defect group counters', () => {
  it('preserves server counts in individual reads and mutation results', async () => {
    for (const result of [
      await getDefectGroup(group.id),
      await updateDefectGroup(group.id, { name: 'Power' }),
    ]) {
      expect(result.activeTypesCount).toBe(2)
      expect(result.typesCount).toBe(5)
    }
  })
})
