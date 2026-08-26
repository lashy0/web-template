import { z } from 'zod'

const roleSchema = z.enum(['administrator', 'manager', 'engineer', 'packer', 'operator'])

const nameSchema = z
  .string()
  .trim()
  .min(1, 'Укажите имя пользователя.')
  .max(128, 'Имя не должно превышать 128 символов.')

const loginSchema = z
  .string()
  .trim()
  .regex(
    /^[a-z0-9][a-z0-9._-]{2,63}$/,
    'От 3 строчных латинских букв, цифр, точек, дефисов или подчёркиваний.',
  )

export const createUserSchema = z.object({
  active: z.boolean(),
  login: loginSchema,
  name: nameSchema,
  password: z.string().min(12, 'Пароль должен содержать не менее 12 символов.'),
  role: roleSchema,
})

export const editUserSchema = z.object({
  login: loginSchema,
  name: nameSchema,
  role: roleSchema,
})

export const changeUserPasswordSchema = z
  .object({
    password: z.string().min(12, 'Пароль должен содержать не менее 12 символов.'),
    passwordConfirmation: z.string(),
  })
  .refine(({ password, passwordConfirmation }) => password === passwordConfirmation, {
    message: 'Пароли не совпадают.',
    path: ['passwordConfirmation'],
  })

export function zodErrorMessage(error: z.ZodError): string {
  return error.issues[0]?.message ?? 'Проверьте введённые данные.'
}
