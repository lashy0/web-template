import { zodResolver } from '@hookform/resolvers/zod'
import { useCallback, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'

import {
  LoginFlowError,
  loadLoginFlow,
  restartLoginFlow,
  submitLoginFlow,
  type LoginFlow,
} from '@/features/auth/login-flow'
import {
  initialLoginFormValues,
  loginFormSchema,
  type LoginFormValues,
} from '@/features/auth/login-form-schema'

const SUBMIT_UNAVAILABLE_MESSAGE = 'Не удалось выполнить вход. Попробуйте ещё раз.'
const INVALID_CREDENTIALS_MESSAGE = 'Неверный логин или пароль'

export function usePasswordLoginForm(flowId?: string) {
  const [flow, setFlow] = useState<LoginFlow>()
  const [hasLoadError, setHasLoadError] = useState(false)
  const form = useForm<LoginFormValues>({
    defaultValues: initialLoginFormValues,
    resolver: zodResolver(loginFormSchema),
  })
  const { clearErrors, reset, resetField, setError } = form

  useEffect(() => {
    if (!flowId) {
      restartLoginFlow()
      return
    }

    let active = true
    setFlow(undefined)
    setHasLoadError(false)

    void loadLoginFlow(flowId)
      .then((nextFlow) => {
        if (!active) {
          return undefined
        }

        setFlow(nextFlow)
        reset({ login: nextFlow.login.defaultValue, password: '' })
        return undefined
      })
      .catch((error: unknown) => {
        if (!active || !(error instanceof LoginFlowError)) {
          return undefined
        }

        if (error.kind === 'restart') {
          restartLoginFlow(flowId)
          return undefined
        }

        if (error.kind === 'unsupported') {
          window.location.assign('/auth/error')
          return undefined
        }

        setHasLoadError(true)
        return undefined
      })

    return () => {
      active = false
    }
  }, [flowId, reset])

  const clearFormError = useCallback(() => {
    clearErrors('root')
    setFlow((current) => (current ? { ...current, messages: [] } : current))
  }, [clearErrors])

  const retryLoad = useCallback(() => {
    restartLoginFlow()
  }, [])

  const submit = form.handleSubmit(async (values) => {
    if (!flowId) {
      restartLoginFlow()
      return
    }

    try {
      clearErrors('root')
      const result = await submitLoginFlow(flowId, values)

      if (result.kind === 'success' || result.kind === 'redirect') {
        window.location.assign(result.redirectTo)
        return
      }

      if (result.kind === 'credentials') {
        resetField('password')
        setError('root', { message: INVALID_CREDENTIALS_MESSAGE })
        return
      }

      if (result.kind === 'unavailable') {
        setError('root', { message: SUBMIT_UNAVAILABLE_MESSAGE })
        return
      }

      setFlow((current) =>
        current
          ? {
              ...current,
              login: { ...current.login, messages: result.loginMessages },
              password: { ...current.password, messages: result.passwordMessages },
              messages: result.messages,
            }
          : current,
      )
    } catch (error) {
      if (error instanceof LoginFlowError && error.kind === 'restart') {
        restartLoginFlow(flowId)
        return
      }

      if (error instanceof LoginFlowError && error.kind === 'unsupported') {
        window.location.assign('/auth/error')
        return
      }

      setError('root', { message: SUBMIT_UNAVAILABLE_MESSAGE })
    }
  })

  return { clearFormError, flow, form, hasLoadError, retryLoad, submit }
}
