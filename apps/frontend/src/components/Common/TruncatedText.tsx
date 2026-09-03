export function TruncatedText({
  maxLength,
  value,
}: Readonly<{
  maxLength?: number
  value: string
}>) {
  const displayedValue = truncateValue(value, maxLength)

  return <span className="block min-w-0 truncate">{displayedValue}</span>
}

function truncateValue(value: string, maxLength: number | undefined): string {
  if (maxLength === undefined || value.length <= maxLength) return value

  return `${value.slice(0, maxLength)}…`
}
