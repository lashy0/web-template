import { zDefectGroupCreate, zDefectTypeCreate } from '@web-app/api-client'
import { z } from 'zod'

import { fieldMessages, optionalText, trimmed } from '@/lib/validation'

export const createDefectGroupSchema = z.object({
  code: trimmed(zDefectGroupCreate.shape.code),
  description: optionalText(zDefectGroupCreate.shape.description),
  name: trimmed(zDefectGroupCreate.shape.name),
})

export const updateDefectGroupSchema = createDefectGroupSchema.pick({
  description: true,
  name: true,
})

export const createDefectTypeSchema = z.object({
  code: trimmed(zDefectTypeCreate.shape.code),
  description: trimmed(zDefectTypeCreate.shape.description),
  engineerAction: optionalText(zDefectTypeCreate.shape.engineerAction),
  groupId: zDefectTypeCreate.shape.groupId,
  name: trimmed(zDefectTypeCreate.shape.name),
  possibleCause: optionalText(zDefectTypeCreate.shape.possibleCause),
})

export const updateDefectTypeSchema = createDefectTypeSchema.omit({ code: true, groupId: true })

/** Pass as `zodResolver(schema, { error: defectFormMessages })`. */
export const defectFormMessages = fieldMessages({
  code: { invalid_format: 'Код не должен содержать пробелы.' },
  groupId: { invalid_format: 'Выберите группу.' },
})
