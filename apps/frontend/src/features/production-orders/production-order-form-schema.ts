import { z } from 'zod'

const name = z
  .string()
  .trim()
  .min(1, 'Укажите название.')
  .max(128, 'Название не должно превышать 128 символов.')
const description = z.string().trim().max(2000, 'Описание не должно превышать 2000 символов.')

export const productionOrderFormSchema = z.object({ description, name })
