import { Configuration, FrontendApi } from '@ory/client-fetch'

/** Traefik, and Vite in development, serve the Kratos public API under this path. */
export const KRATOS_PUBLIC_PATH = '/.ory/kratos'

export function kratosPath(path: string) {
  return `${KRATOS_PUBLIC_PATH}${path}`
}

export const kratosFrontend = new FrontendApi(
  new Configuration({
    basePath: `${window.location.origin}${KRATOS_PUBLIC_PATH}`,
    credentials: 'include',
  }),
)
