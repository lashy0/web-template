import { z } from 'zod'

const name = z
  .string()
  .trim()
  .min(1, 'Укажите название.')
  .max(128, 'Название не должно превышать 128 символов.')
const description = z.string().trim().max(2000, 'Описание не должно превышать 2000 символов.')
const positiveInteger = z.string().regex(/^[1-9]\d*$/, 'Должен быть целым числом больше нуля.')

export function normalizePositiveIntegerInput(value: string): string {
  return value.replace(/\D/g, '').replace(/^0+/, '')
}

export const createBatchFormSchema = z.object({
  activationType: z.enum(['otaa', 'abp'], { error: 'Выберите тип активации.' }),
  dayPlanQty: positiveInteger,
  description,
  devEuiPrefix: z.string().min(1, 'Выберите DevEUI-префикс.'),
  kgVersionId: z.string().uuid('Выберите версию КГ.'),
  lorawanVersion: z.enum(['1.0', '1.1'], { error: 'Выберите версию LoRaWAN.' }),
  name,
  plannedQty: positiveInteger,
  productionOrderId: z.string(),
})

export const editBatchFormSchema = z.object({
  dayPlanQty: positiveInteger,
  description,
  name,
})
