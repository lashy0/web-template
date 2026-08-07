import { client } from './generated/client.gen'

export function configureApiClient(baseUrl = '/api') {
  client.setConfig({
    baseUrl,
    credentials: 'same-origin',
  })
}
