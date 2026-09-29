import { defineConfig } from '@hey-api/openapi-ts'

const STRING_KEYWORDS = ['minLength', 'maxLength', 'pattern'] as const
const NUMBER_KEYWORDS = ['minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum'] as const

type SchemaNode = { [key: string]: unknown }

/**
 * Litestar puts the constraints of an optional field, such as
 * `Annotated[str, Meta(max_length=128)] | None`, next to its `oneOf`, where
 * the generator ignores them. Move them into the branches they apply to.
 */
function moveConstraintsIntoBranches(node: unknown): void {
  if (Array.isArray(node)) {
    node.forEach(moveConstraintsIntoBranches)
    return
  }
  if (typeof node !== 'object' || node === null) {
    return
  }
  const schema = node as SchemaNode
  const branches = schema.oneOf ?? schema.anyOf
  if (Array.isArray(branches)) {
    for (const [keywords, types] of [
      [STRING_KEYWORDS, ['string']],
      [NUMBER_KEYWORDS, ['integer', 'number']],
    ] as const) {
      for (const keyword of keywords) {
        if (!(keyword in schema)) {
          continue
        }
        for (const branch of branches as SchemaNode[]) {
          if ((types as readonly unknown[]).includes(branch.type)) {
            branch[keyword] ??= schema[keyword]
          }
        }
        delete schema[keyword]
      }
    }
  }
  Object.values(schema).forEach(moveConstraintsIntoBranches)
}

export default defineConfig({
  input: './openapi.json',
  output: './src/generated',
  parser: {
    filters: {
      // The PAK API is for machines; health checks are for the infrastructure.
      tags: { exclude: ['PAK machine API', 'System'] },
    },
    patch: {
      input: moveConstraintsIntoBranches,
    },
  },
  plugins: [
    // Paths in the schema already start with `/api`; the client adds no base URL.
    { name: '@hey-api/client-fetch', baseUrl: false },
    { name: '@hey-api/typescript', enums: 'javascript' },
    '@hey-api/sdk',
    'zod',
    // Operation tags in query keys let a mutation invalidate a whole section.
    { name: '@tanstack/react-query', queryKeys: { tags: true } },
  ],
})
