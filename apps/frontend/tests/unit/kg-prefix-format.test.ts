import { describe, expect, it } from 'vitest'

import { formatDevEuiPrefix, normalizeDevEuiPrefix } from '@/features/kg/kg-prefix-format'

describe('normalizeDevEuiPrefix', () => {
  it('keeps at most ten hexadecimal characters and normalizes them to lowercase', () => {
    expect(normalizeDevEuiPrefix('A1-b2 C3:d4E5F6')).toBe('a1b2c3d4e5')
  })
})

describe('formatDevEuiPrefix', () => {
  it('groups hexadecimal characters into bytes for display', () => {
    expect(formatDevEuiPrefix('aabbccddee')).toBe('AA BB CC DD EE')
  })
})
