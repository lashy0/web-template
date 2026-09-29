import { zPakDeviceCreate, zPakDeviceKind } from '@web-app/api-client'
import { z } from 'zod'

import { fieldMessages, trimmed } from '@/lib/validation'

const code = trimmed(zPakDeviceCreate.shape.code)

export const createPakSchema = z.object({
  code,
  isActive: z.boolean(),
  kind: zPakDeviceKind,
})

export const editPakSchema = z.object({
  code,
  kind: zPakDeviceKind,
})

/** Pass as `zodResolver(schema, { error: pakFormMessages })`. */
export const pakFormMessages = fieldMessages({
  code: {
    invalid_format:
      'Латинские буквы, цифры, точки, дефисы или подчёркивания; начинается с буквы или цифры.',
  },
})
