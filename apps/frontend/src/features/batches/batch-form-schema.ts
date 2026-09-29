import { zBatchCreate } from '@web-app/api-client'
import { z } from 'zod'

import { fieldMessages, optionalText, trimmed } from '@/lib/validation'

/** A quantity typed as digits; see `normalizePositiveIntegerInput`. */
function quantity(schema: z.ZodType<number, number>) {
  return z.string().min(1).transform(Number).pipe(schema)
}

export function normalizePositiveIntegerInput(value: string): string {
  return value.replace(/\D/g, '').replace(/^0+/, '')
}

const name = trimmed(zBatchCreate.shape.name)
const description = optionalText(zBatchCreate.shape.description)
const dayPlanQty = quantity(zBatchCreate.shape.dayPlanQty)

export const createBatchFormSchema = z.object({
  activationType: zBatchCreate.shape.activationType,
  dayPlanQty,
  description,
  kgPrefixId: zBatchCreate.shape.kgPrefixId,
  // Optional in the API, but every batch of the plant has a KG version.
  kgVersionId: z.uuid(),
  lorawanVersion: zBatchCreate.shape.lorawanVersion,
  name,
  plannedQty: quantity(zBatchCreate.shape.plannedQty),
  productionOrderId: z
    .string()
    .transform((value) => value || null)
    .pipe(z.uuid().nullable()),
})

export const editBatchFormSchema = z.object({ dayPlanQty, description, name })

/** Pass as `zodResolver(schema, { error: batchFormMessages })`. */
export const batchFormMessages = fieldMessages({
  kgPrefixId: { invalid_format: 'Выберите DevEUI-префикс.' },
  kgVersionId: { invalid_format: 'Выберите версию КГ.' },
})
