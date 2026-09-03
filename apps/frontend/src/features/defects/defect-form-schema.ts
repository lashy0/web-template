import { z } from 'zod'

const code = z
  .string()
  .trim()
  .min(1, 'Укажите код.')
  .max(64, 'Код не должен превышать 64 символов.')
  .regex(/^\S+$/, 'Код не должен содержать пробелы.')

const requiredText = (label: string, max = 255) =>
  z
    .string()
    .trim()
    .min(1, `Укажите ${label}.`)
    .max(max, `Значение не должно превышать ${max} символов.`)

const optionalText = (max: number) => z.string().trim().max(max, `Не более ${max} символов.`)

export const createDefectGroupSchema = z.object({
  code: code.max(32, 'Код не должен превышать 32 символов.'),
  description: optionalText(2000),
  name: requiredText('название'),
})

export const updateDefectGroupSchema = createDefectGroupSchema.pick({
  description: true,
  name: true,
})

export const createDefectTypeSchema = z.object({
  code,
  description: requiredText('описание', 2000),
  engineer_action: optionalText(2000),
  group_id: z.string().uuid('Выберите группу.'),
  name: requiredText('название'),
  possible_cause: optionalText(2000),
})

export const updateDefectTypeSchema = createDefectTypeSchema.omit({ code: true, group_id: true })
