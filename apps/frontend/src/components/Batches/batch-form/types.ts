import type { Control } from 'react-hook-form'

import type { z } from 'zod'
import type { createBatchFormSchema } from '@/features/batches/batch-form-schema'

export type CreateBatchForm = z.infer<typeof createBatchFormSchema>

export type BatchFormControl = Control<CreateBatchForm>
export type FormStep = 1 | 2
export type SelectOption = Readonly<{ label: string; value: string }>

export type SelectOptionsState = Readonly<{
  items: readonly SelectOption[]
  loading: boolean
  error: boolean
  retry: () => void
}>

export const initialBatchFormValues: CreateBatchForm = {
  activationType: 'abp',
  dayPlanQty: '',
  description: '',
  devEuiPrefix: '',
  kgVersionId: '',
  lorawanVersion: '1.1',
  name: '',
  plannedQty: '',
  productionOrderId: '',
}

export const batchStepOneFields = [
  'name',
  'productionOrderId',
  'plannedQty',
  'dayPlanQty',
  'description',
] as const

export const activationTypeOptions: readonly SelectOption[] = [
  { label: 'OTAA', value: 'otaa' },
  { label: 'ABP', value: 'abp' },
]

export const lorawanVersionOptions: readonly SelectOption[] = [
  { label: '1.0', value: '1.0' },
  { label: '1.1', value: '1.1' },
]
