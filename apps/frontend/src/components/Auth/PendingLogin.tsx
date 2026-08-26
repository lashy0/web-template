import { Skeleton } from '@web-app/ui/components/skeleton'

export function PendingLogin() {
  return (
    <output aria-busy="true" aria-label="Загрузка формы входа" className="flex flex-col gap-5">
      <Skeleton className="h-4 w-16" />
      <Skeleton className="h-9 w-full" />
      <Skeleton className="h-4 w-16" />
      <Skeleton className="h-9 w-full" />
      <Skeleton className="h-10 w-full" />
    </output>
  )
}
