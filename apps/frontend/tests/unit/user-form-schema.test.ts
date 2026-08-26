import { describe, expect, it } from 'vitest'

import { createUserSchema, editUserSchema } from '@/features/users/user-form-schema'

describe('User form schemas', () => {
  it('normalizes valid data for a new user', () => {
    const result = createUserSchema.safeParse({
      active: true,
      login: '  operator.1  ',
      name: '  Иван Петров  ',
      password: 'secure-password',
      role: 'operator',
    })

    expect(result).toMatchObject({
      data: {
        login: 'operator.1',
        name: 'Иван Петров',
      },
      success: true,
    })
  })

  it('rejects a short password and an invalid login', () => {
    const result = createUserSchema.safeParse({
      active: true,
      login: 'Invalid login',
      name: 'Иван Петров',
      password: 'short',
      role: 'operator',
    })

    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues).toHaveLength(2)
    }
  })

  it('requires a valid login when editing a user', () => {
    expect(
      editUserSchema.safeParse({ login: '', name: 'Иван Петров', role: 'operator' }).success,
    ).toBe(false)
  })
})
