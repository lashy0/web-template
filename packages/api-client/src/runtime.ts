import { client } from './generated/client.gen'
import type { ErrorResponse } from './generated/types.gen'

export type ApiClientConfiguration = Readonly<{
  baseUrl?: string
  onUnauthorized?: (response: Response) => void | Promise<void>
}>

let unauthorizedResponseInterceptor: number | undefined

// Query keys carry the base URL, so it is set before any key is built.
client.setConfig({ baseUrl: '', credentials: 'same-origin' })

export function configureApiClient({ baseUrl = '', onUnauthorized }: ApiClientConfiguration = {}) {
  client.setConfig({
    baseUrl,
    credentials: 'same-origin',
  })

  if (unauthorizedResponseInterceptor !== undefined) {
    client.interceptors.response.eject(unauthorizedResponseInterceptor)
    unauthorizedResponseInterceptor = undefined
  }

  if (onUnauthorized) {
    unauthorizedResponseInterceptor = client.interceptors.response.use(async (response) => {
      if (response.status === 401) {
        await onUnauthorized(response)
      }
      return response
    })
  }
}

/**
 * Whether `error` is an error response of the backend, as thrown by the
 * generated queries and mutations; with `code`, whether its `extra.code` is it.
 */
export function isApiError(error: unknown, code?: string): error is ErrorResponse {
  if (
    typeof error !== 'object' ||
    error === null ||
    !('status_code' in error) ||
    typeof error.status_code !== 'number'
  ) {
    return false
  }
  if (code === undefined) {
    return true
  }
  return (error as ErrorResponse).extra?.code === code
}
