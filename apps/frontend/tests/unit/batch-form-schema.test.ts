import { describe, expect, it } from 'vitest'

import {
  createBatchFormSchema,
  normalizePositiveIntegerInput,
} from '@/features/batches/batch-form-schema'

describe('normalizePositiveIntegerInput', () => {
  it('keeps only a positive integer', () => {
    expect(normalizePositiveIntegerInput('-0012.5e3')).toBe('1253')
    expect(normalizePositiveIntegerInput('0')).toBe('')
  })
})

describe('batch configuration schema', () => {
  it('rejects unsupported activation types and LoRaWAN versions', () => {
    expect(createBatchFormSchema.shape.activationType.safeParse('custom').success).toBe(false)
    expect(createBatchFormSchema.shape.lorawanVersion.safeParse('2.0').success).toBe(false)
    expect(createBatchFormSchema.shape.activationType.safeParse('otaa').success).toBe(true)
    expect(createBatchFormSchema.shape.activationType.safeParse('abp').success).toBe(true)
    expect(createBatchFormSchema.shape.lorawanVersion.safeParse('1.0').success).toBe(true)
    expect(createBatchFormSchema.shape.lorawanVersion.safeParse('1.1').success).toBe(true)
  })
})
