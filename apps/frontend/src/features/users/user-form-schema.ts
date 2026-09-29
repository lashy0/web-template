import { zUserCreate, zUserPasswordUpdate, zUserRole } from '@web-app/api-client'
import { z } from 'zod'

import { fieldMessages, trimmed } from '@/lib/validation'

// The rules come from the backend; the form trims and lowers what a person typed.
const login = z.string().trim().toLowerCase().pipe(zUserCreate.shape.login)
const name = trimmed(zUserCreate.shape.name)

export const createUserSchema = z.object({
  isActive: z.boolean(),
  login,
  name,
  password: zUserCreate.shape.password,
  role: zUserRole,
})

export const editUserSchema = z.object({
  login,
  name,
  role: zUserRole,
})

export const changeUserPasswordSchema = z
  .object({
    password: zUserPasswordUpdate.shape.password,
    passwordConfirmation: z.string(),
  })
  .refine(({ password, passwordConfirmation }) => password === passwordConfirmation, {
    message: 'Пароли не совпадают.',
    path: ['passwordConfirmation'],
  })

/** Pass as `zodResolver(schema, { error: userFormMessages })`. */
export const userFormMessages = fieldMessages({
  login: {
    invalid_format:
      'Латинские буквы, цифры, точки, дефисы или подчёркивания; начинается с буквы или цифры.',
  },
  name: {
    invalid_format: 'Только буквы, пробелы, апострофы, точки и дефисы.',
  },
  password: {
    invalid_format:
      'Нужны заглавная и строчная латинские буквы, цифра и спецсимвол; пароль не должен начинаться с 123, abc, qwe и подобного.',
  },
})
