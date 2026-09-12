import * as React from 'react'

import { cn } from '#lib/utils'

function Empty({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'flex min-h-56 flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center',
        className,
      )}
      data-slot="empty"
      {...props}
    />
  )
}

function EmptyHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('flex flex-col gap-1', className)} data-slot="empty-header" {...props} />
}

function EmptyTitle({ className, ...props }: React.ComponentProps<'p'>) {
  return <p className={cn('font-medium', className)} data-slot="empty-title" {...props} />
}

function EmptyDescription({ className, ...props }: React.ComponentProps<'p'>) {
  return (
    <p className={cn('text-sm text-muted-foreground', className)} data-slot="empty-description" {...props} />
  )
}

export { Empty, EmptyDescription, EmptyHeader, EmptyTitle }
