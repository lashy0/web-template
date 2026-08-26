import { describe, expect, it } from 'vitest'

import {
  getDatePeriodPreset,
  toCalendarDateRange,
  toDatePeriod,
  toExclusiveUtcDateRange,
} from '@/lib/date'

describe('date period utilities', () => {
  it('creates an inclusive preset ending today', () => {
    expect(getDatePeriodPreset(7, new Date(2026, 7, 25, 10))).toEqual({
      from: '2026-08-19',
      to: '2026-08-25',
    })
  })

  it('converts calendar selection while preserving an incomplete period', () => {
    expect(toDatePeriod({ from: new Date(2026, 7, 19) })).toEqual({
      from: '2026-08-19',
      to: undefined,
    })
    expect(
      toDatePeriod({
        from: new Date(2026, 7, 19),
        to: new Date(2026, 7, 25),
      }),
    ).toEqual({ from: '2026-08-19', to: '2026-08-25' })
  })

  it('uses an exclusive start of the next day as the range end', () => {
    const period = { from: '2026-08-19', to: '2026-08-25' }
    const range = toExclusiveUtcDateRange(period)

    expect(range).toEqual({
      from: new Date('2026-08-19T00:00:00').toISOString(),
      to: new Date('2026-08-26T00:00:00').toISOString(),
    })
  })

  it('keeps date-only values in the local calendar day', () => {
    const range = toCalendarDateRange('2026-08-19', '2026-08-25')

    expect(range?.from?.getFullYear()).toBe(2026)
    expect(range?.from?.getMonth()).toBe(7)
    expect(range?.from?.getDate()).toBe(19)
    expect(range?.to?.getDate()).toBe(25)
  })
})
