import { Button } from '@web-app/ui/components/button'

export function DataLoadError({
  onRetry,
}: Readonly<{
  onRetry: () => void
}>) {
  return (
    <div
      className="flex min-h-56 items-center justify-center rounded-lg border border-dashed"
      role="alert"
    >
      <div className="text-center">
        <p className="font-medium">Не удалось загрузить данные</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Проверьте подключение к серверу и повторите попытку.
        </p>
        <Button className="mt-4" onClick={onRetry} size="sm" variant="outline">
          Повторить
        </Button>
      </div>
    </div>
  )
}
