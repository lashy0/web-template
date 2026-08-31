import tailwindcss from '@tailwindcss/vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'

const repositoryRoot = fileURLToPath(new URL('../..', import.meta.url))

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, repositoryRoot, '')
  const baseDomain = env.BASE_DOMAIN || 'localhost'
  const kratosPublicPort = env.KRATOS_PUBLIC_PORT || '4433'
  const apiHost = `api.${baseDomain}`
  const apiTarget =
    env.DEV_API_PROXY_TARGET ||
    (baseDomain === 'localhost' ? 'http://127.0.0.1' : `http://${apiHost}`)
  const kratosPublicTarget =
    env.DEV_KRATOS_PUBLIC_PROXY_TARGET || `http://127.0.0.1:${kratosPublicPort}`

  return {
    envDir: repositoryRoot,
    plugins: [
      tanstackRouter({
        target: 'react',
        autoCodeSplitting: true,
      }),
      react(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          configure:
            baseDomain === 'localhost'
              ? (proxy) => {
                  proxy.on('proxyReq', (request) => {
                    request.setHeader('host', apiHost)
                  })
                }
              : undefined,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
        '/self-service': {
          target: kratosPublicTarget,
          changeOrigin: true,
        },
        '/sessions': {
          target: kratosPublicTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
