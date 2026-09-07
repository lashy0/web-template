import { useMutation, useQueryClient } from '@tanstack/react-query'
import { TriangleAlertIcon } from 'lucide-react'
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

import {
  deleteKgPrefix,
  kgPrefixErrorCode,
  kgPrefixErrorMessage,
  type KgPrefix,
} from '@/features/kg/kg-prefixes-api'
import useCustomToast from '@/hooks/useCustomToast'

export function DeleteKgPrefix({
  onOpenChange,
  onSuccess,
  open,
  prefix,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  prefix: KgPrefix
}>) {
  const [inUse, setInUse] = useState(false)
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: () => deleteKgPrefix(prefix.prefix),
    onError: (error) => {
      if (kgPrefixErrorCode(error) === 'kg_dev_eui_prefix_in_use') {
        setInUse(true)
        return
      }
      showErrorToast(
        'Не удалось удалить префикс',
        kgPrefixErrorMessage(error) ?? 'Попробуйте ещё раз.',
      )
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['kg', 'prefixes'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      close(true)
      onSuccess()
      showSuccessToast('Префикс удалён', `Префикс «${prefix.prefix}» удалён навсегда.`)
    },
  })

  function close(force = false) {
    if (mutation.isPending && !force) return
    setInUse(false)
    onOpenChange(false)
  }

  return (
    <Dialog onOpenChange={close} open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={!mutation.isPending}>
        {inUse ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <TriangleAlertIcon aria-hidden="true" className="size-5 text-amber-500" />
                Нельзя удалить префикс
              </DialogTitle>
              <DialogDescription>
                Префикс «{prefix.prefix}» используется партией. Сначала удалите или измените
                связанные партии.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button onClick={() => close()} type="button" variant="outline">
                Понятно
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Удалить префикс навсегда?</DialogTitle>
              <DialogDescription>
                Префикс «{prefix.prefix}» будет удалён без возможности восстановления.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button disabled={mutation.isPending} onClick={() => close()} variant="outline">
                Отмена
              </Button>
              <Button
                disabled={mutation.isPending}
                onClick={() => mutation.mutate()}
                variant="destructive"
              >
                {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
                {mutation.isPending ? 'Удаление…' : 'Удалить'}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
