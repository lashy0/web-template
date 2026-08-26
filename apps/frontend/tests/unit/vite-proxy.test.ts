import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'
import { loadConfigFromFile } from 'vite'

const viteConfigPath = resolve(process.cwd(), 'vite.config.ts')

describe('Vite API proxy', () => {
  it('uses a Node-resolvable target for the local API host', async () => {
    const loadedConfig = await loadConfigFromFile(
      { command: 'serve', mode: 'development' },
      viteConfigPath,
    )

    expect(loadedConfig?.config.server?.proxy?.['/api']).toMatchObject({
      target: 'http://127.0.0.1',
      configure: expect.any(Function),
    })
  })
})
