import type { QueryClient } from '@tanstack/react-query'

/**
 * Invalidate every generated query of the given OpenAPI tags, such as
 * `'User Accounts'`; generated query keys carry the tags of their operation.
 */
export function invalidateTags(queryClient: QueryClient, ...tags: readonly string[]) {
  return Promise.all(
    tags.map((tag) => queryClient.invalidateQueries({ queryKey: [{ tags: [tag] }] })),
  )
}
