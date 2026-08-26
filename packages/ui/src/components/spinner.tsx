import { LoaderCircleIcon } from 'lucide-react'

import { cn } from '#lib/utils'

function Spinner({ className, ...props }: React.ComponentProps<typeof LoaderCircleIcon>) {
  return (
    <LoaderCircleIcon
      aria-label="Загрузка"
      className={cn('animate-spin', className)}
      role="status"
      {...props}
    />
  )
}

export { Spinner }
