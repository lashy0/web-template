import { createFileRoute } from '@tanstack/react-router'

import { APP_NAME } from '@/app/config'

export const Route = createFileRoute('/')({
  component: HomePage,
})

export function HomePage() {
  return (
    <section className="mx-auto flex w-full max-w-6xl flex-1 items-center px-4 py-16 sm:px-6">
      <div className="max-w-2xl">
        <p className="text-sm font-medium text-muted-foreground">Application foundation</p>
        <h1 className="mt-3 text-balance text-4xl font-semibold tracking-tight sm:text-6xl">
          {APP_NAME}
        </h1>
        <p className="mt-5 max-w-xl text-pretty text-base leading-7 text-muted-foreground sm:text-lg">
          Ready for the first product flow.
        </p>
      </div>
    </section>
  )
}
