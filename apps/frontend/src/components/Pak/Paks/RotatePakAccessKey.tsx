import { useMutation } from '@tanstack/react-query'
import { CopyIcon } from 'lucide-react'
import { useState } from 'react'

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

import { rotatePakAccessKey, type Pak } from '@/features/paks/paks-api'
import useCustomToast from '@/hooks/useCustomToast'

export function RotatePakAccessKey({
  onOpenChange,
  open,
  pak,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  open: boolean
  pak: Pak
}>) {
  const [accessKey, setAccessKey] = useState<string | null>(null)
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: () => rotatePakAccessKey(pak.id),
    onSuccess: (nextKey) => {
      setAccessKey(nextKey)
      showSuccessToast('Ключ доступа обновлён')
    },
    onError: () => showErrorToast('Не удалось ротировать ключ доступа', 'Попробуйте ещё раз.'),
  })

  function close() {
    if (mutation.isPending) return
    setAccessKey(null)
    onOpenChange(false)
  }

  async function copy() {
    if (!accessKey) return
    await navigator.clipboard?.writeText(accessKey)
    showSuccessToast('Ключ скопирован')
  }

  return (
    <Dialog onOpenChange={(nextOpen) => (nextOpen ? onOpenChange(true) : close())} open={open}>
      <DialogContent className="sm:max-w-lg" showCloseButton={!mutation.isPending}>
        <DialogHeader>
          <DialogTitle>{accessKey ? 'Новый ключ доступа' : 'Ротировать ключ доступа?'}</DialogTitle>
          <DialogDescription>
            {accessKey
              ? 'Сохраните новый ключ. Старый ключ больше не работает.'
              : `Старый ключ ПАК «${pak.code}» немедленно перестанет работать.`}
          </DialogDescription>
        </DialogHeader>
        {accessKey ? (
          <div className="rounded-md border bg-muted p-3 font-mono text-sm break-all">{accessKey}</div>
        ) : null}
        <DialogFooter>
          {accessKey ? (
            <>
              <Button onClick={() => void copy()} type="button" variant="outline">
                <CopyIcon data-icon="inline-start" />
                Копировать
              </Button>
              <Button onClick={close} type="button">
                Готово
              </Button>
            </>
          ) : (
            <>
              <Button disabled={mutation.isPending} onClick={close} type="button" variant="outline">
                Отмена
              </Button>
              <Button disabled={mutation.isPending} onClick={() => mutation.mutate()} type="button">
                {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
                {mutation.isPending ? 'Ротация…' : 'Ротировать'}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
