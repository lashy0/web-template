export function normalizeDevEuiPrefix(value: string): string {
  return value
    .replace(/[^0-9a-f]/gi, '')
    .slice(0, 10)
    .toLowerCase()
}

export function formatDevEuiPrefix(value: string): string {
  return (
    normalizeDevEuiPrefix(value)
      .match(/.{1,2}/g)
      ?.join(' ') ?? ''
  ).toUpperCase()
}

export function formatDevEui(value: string): string {
  return (
    value
      .replace(/[^0-9a-f]/gi, '')
      .slice(0, 16)
      .match(/.{1,2}/g)
      ?.join(' ') ?? ''
  ).toUpperCase()
}
