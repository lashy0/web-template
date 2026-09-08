import { z } from 'zod'

const code = z.string().trim().min(1, 'Укажите код.').max(32, 'Код не должен превышать 32 символа.')

const name = z
  .string()
  .trim()
  .min(1, 'Укажите название.')
  .max(128, 'Название не должно превышать 128 символов.')

const description = z.string().trim().max(2000, 'Описание не должно превышать 2000 символов.')

export const createKgVersionSchema = z.object({ code, description, name })
export const updateKgVersionSchema = createKgVersionSchema.pick({ description: true, name: true })
