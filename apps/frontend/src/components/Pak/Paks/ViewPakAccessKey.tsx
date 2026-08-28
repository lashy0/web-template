import { useMutation } from '@tanstack/react-query'
import { CopyIcon } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { Button } from '@web-app/ui/components/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@web-app/ui/components/dialog'
import { Spinner } from '@web-app/ui/components/spinner'

import { getPakAccessKey, type Pak } from '@/features/paks/paks-api'
import useCustomToast from '@/hooks/useCustomToast'

export function ViewPakAccessKey({
  onOpenChange,
  open,
  pak,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  open: boolean
  pak: Pak
}>) {
  const requestedForOpen = useRef(false)
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: () => getPakAccessKey(pak.id),
    onError: () => {
      showErrorToast('Не удалось получить ключ доступа', 'Попробуйте ещё раз.')
    },
  })

  useEffect(() => {
    if (!open) {
      requestedForOpen.current = false
      mutation.reset()
      return
    }

    if (!requestedForOpen.current) {
      requestedForOpen.current = true
      mutation.mutate()
    }
  }, [mutation, open])

  function handleOpenChange(nextOpen: boolean) {
    onOpenChange(nextOpen)
  }

  async function copy() {
    if (!mutation.data) return
    await navigator.clipboard?.writeText(mutation.data)
    showSuccessToast('Ключ скопирован')
  }

  return (
    <Dialog onOpenChange={handleOpenChange} open={open}>
      <DialogContent className="sm:max-w-lg" showCloseButton={!mutation.isPending}>
        <DialogHeader>
          <DialogTitle>Ключ доступа ПАК</DialogTitle>
          <DialogDescription>
            Ключ ПАК «{pak.code}». Не передавайте его посторонним.
          </DialogDescription>
        </DialogHeader>
        {mutation.isPending ? (
          <div className="flex min-h-20 items-center justify-center">
            <Spinner />
          </div>
        ) : mutation.data ? (
          <div className="rounded-md border bg-muted p-3 font-mono text-sm break-all">
            {mutation.data}
          </div>
        ) : (
          <div className="flex min-h-20 flex-col items-center justify-center gap-3 text-sm text-muted-foreground">
            <span>Не удалось загрузить ключ.</span>
            <Button onClick={() => mutation.mutate()} size="sm" variant="outline">
              Повторить
            </Button>
          </div>
        )}
        <DialogFooter>
          {mutation.data ? (
            <Button onClick={() => void copy()} type="button" variant="outline">
              <CopyIcon data-icon="inline-start" />
              Копировать
            </Button>
          ) : null}
          <Button onClick={() => onOpenChange(false)} type="button">
            Готово
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
