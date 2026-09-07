import { z } from 'zod'

const name = z.string().trim().max(128, 'Название не должно превышать 128 символов.')

export const createKgPrefixSchema = z.object({
  name,
  prefix: z
    .string()
    .trim()
    .regex(
      /^[0-9a-fA-F]{10}$/,
      'Префикс должен содержать ровно 10 шестнадцатеричных символов.',
    ),
  short_code: z
    .string()
    .trim()
    .min(1, 'Укажите короткий код.')
    .max(10, 'Короткий код не должен превышать 10 символов.')
    .regex(
      /^[a-zA-Z0-9]+$/,
      'Короткий код может содержать только латинские буквы и цифры.',
    ),
})

export const updateKgPrefixSchema = z.object({ name })
