import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/_layout/')({
  beforeLoad: ({ context }) => {
    if (context.currentUser.role === 'administrator') {
      throw redirect({ to: '/admin/user/users' })
    }
  },
  component: AccessDeniedPage,
})

export function AccessDeniedPage() {
  return (
    <section className="flex w-full items-center justify-center py-16 text-center">
      <div className="max-w-2xl">
        <h1 className="text-balance text-4xl font-semibold tracking-tight sm:text-6xl">
          Нет доступа
        </h1>
        <p className="mt-5 max-w-xl text-pretty text-base leading-7 text-muted-foreground sm:text-lg">
          Для вашей учётной записи пока нет доступных разделов.
        </p>
      </div>
    </section>
  )
}
