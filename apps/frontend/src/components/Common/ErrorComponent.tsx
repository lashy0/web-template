import { Link } from '@tanstack/react-router'

import { Button } from '@web-app/ui/components/button'

export default function ErrorComponent() {
  return (
    <div
      className="flex min-h-svh flex-col items-center justify-center p-4"
      data-testid="error-component"
    >
      <div className="z-10 flex items-center">
        <div className="ml-4 flex flex-col items-center justify-center p-4">
          <span className="mb-4 text-6xl font-bold leading-none md:text-8xl">Ошибка</span>
          <span className="mb-2 text-2xl font-bold">Упс!</span>
        </div>
      </div>
      <p className="z-10 mb-4 text-center text-lg text-muted-foreground">
        Что-то пошло не так. Попробуйте ещё раз.
      </p>
      <Link to="/">
        <Button>На главную</Button>
      </Link>
    </div>
  )
}
