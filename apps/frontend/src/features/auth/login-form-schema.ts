import { z } from 'zod'

export const loginFormSchema = z.object({
  login: z.string().min(1, 'Введите логин.'),
  password: z.string().min(1, 'Введите пароль.'),
})

export type LoginFormValues = z.infer<typeof loginFormSchema>

export const initialLoginFormValues: LoginFormValues = {
  login: '',
  password: '',
}
