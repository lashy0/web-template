import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@web-app/ui/components/empty'

export function ListEmptyState({
  description,
  title,
}: Readonly<{
  description: string
  title: string
}>) {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyTitle>{title}</EmptyTitle>
        <EmptyDescription>{description}</EmptyDescription>
      </EmptyHeader>
    </Empty>
  )
}
