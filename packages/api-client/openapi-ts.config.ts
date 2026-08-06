import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: './openapi.json',
  output: './src/generated',
  parser: {
    filters: {
      tags: {
        exclude: ['health'],
      },
      schemas: {
        exclude: ['LivenessResponse', 'ReadinessChecks', 'ReadinessResponse'],
      },
    },
  },
  plugins: [
    '@hey-api/client-fetch',
    '@hey-api/typescript',
    '@hey-api/sdk',
    'zod',
    '@tanstack/react-query',
  ],
})
