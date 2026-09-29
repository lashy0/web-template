/**
 * The fields of `next` whose values differ from `current`, as the body of a
 * PATCH request; the backend rejects a PATCH without fields, so check
 * `hasChanges` first.
 */
export function changedFields<T extends Record<string, unknown>>(
  current: Readonly<Record<keyof T, unknown>>,
  next: T,
): Partial<T> {
  const changes: Partial<T> = {}
  for (const key of Object.keys(next) as (keyof T)[]) {
    if (next[key] !== current[key]) {
      changes[key] = next[key]
    }
  }
  return changes
}

export function hasChanges(changes: Readonly<Record<string, unknown>>): boolean {
  return Object.keys(changes).length > 0
}
