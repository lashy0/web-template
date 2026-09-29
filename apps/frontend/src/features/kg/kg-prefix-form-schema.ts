import { zKgPrefixCreate } from '@web-app/api-client'
import { z } from 'zod'

import { fieldMessages, optionalText } from '@/lib/validation'

const name = optionalText(zKgPrefixCreate.shape.name)

export const createKgPrefixSchema = z.object({
  name,
  prefix: z.string().trim().toLowerCase().pipe(zKgPrefixCreate.shape.prefix),
  shortCode: z.string().trim().toLowerCase().pipe(zKgPrefixCreate.shape.shortCode),
})

export const updateKgPrefixSchema = z.object({ name })

/** Pass as `zodResolver(schema, { error: kgPrefixFormMessages })`. */
export const kgPrefixFormMessages = fieldMessages({
  prefix: { invalid_format: 'Ровно 10 шестнадцатеричных символов.' },
  shortCode: { invalid_format: 'Только латинские буквы и цифры.' },
})
