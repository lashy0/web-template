import { zKgVersionCreate } from '@web-app/api-client'
import { z } from 'zod'

import { optionalText, trimmed } from '@/lib/validation'

const name = trimmed(zKgVersionCreate.shape.name)
const description = optionalText(zKgVersionCreate.shape.description)

export const createKgVersionSchema = z.object({
  code: trimmed(zKgVersionCreate.shape.code),
  description,
  name,
})

export const updateKgVersionSchema = z.object({ description, name })
