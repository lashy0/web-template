import { Configuration, FrontendApi } from '@ory/client-fetch'

const frontend = new FrontendApi(
  new Configuration({
    basePath: window.location.origin,
    credentials: 'include',
  }),
)

export async function createBrowserLogoutUrl(): Promise<string> {
  const flow = await frontend.createBrowserLogoutFlow()
  return flow.logout_url
}
