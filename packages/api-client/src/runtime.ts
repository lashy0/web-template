import { client } from './generated/client.gen'

export type ApiClientConfiguration = Readonly<{
  baseUrl?: string
  onUnauthorized?: (response: Response) => void | Promise<void>
}>

let unauthorizedResponseInterceptor: number | undefined

export function configureApiClient({
  baseUrl = '/api',
  onUnauthorized,
}: ApiClientConfiguration = {}) {
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
