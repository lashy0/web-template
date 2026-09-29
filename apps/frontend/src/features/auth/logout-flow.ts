import { kratosFrontend } from '@/features/auth/kratos'

export async function createBrowserLogoutUrl(): Promise<string> {
  const flow = await kratosFrontend.createBrowserLogoutFlow()
  return flow.logout_url
}
