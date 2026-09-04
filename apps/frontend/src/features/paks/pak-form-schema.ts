import { zPakDeviceKind } from '@web-app/api-client'
import { z } from 'zod'

const codeSchema = z
  .string()
  .trim()
  .min(1, 'Укажите код ПАК.')
  .max(128, 'Код не должен превышать 128 символов.')
  .regex(
    /^[A-Za-z0-9][A-Za-z0-9._-]*$/,
    'Используйте латинские буквы, цифры, точки, дефисы или подчёркивания.',
  )

const kindSchema = zPakDeviceKind

export const createPakSchema = z.object({
  active: z.boolean(),
  code: codeSchema,
  kind: kindSchema,
})

export const editPakSchema = z.object({
  code: codeSchema,
  kind: kindSchema,
})
