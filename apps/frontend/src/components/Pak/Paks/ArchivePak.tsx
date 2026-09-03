import { useMutation, useQueryClient } from '@tanstack/react-query'

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

import { updatePakArchived, type Pak } from '@/features/paks/paks-api'
import useCustomToast from '@/hooks/useCustomToast'

export function ArchivePak({
  onOpenChange,
  onSuccess,
  open,
  pak,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  pak: Pak
}>) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: () => updatePakArchived(pak.id, true),
    onError: () => showErrorToast('Не удалось архивировать ПАК', 'Попробуйте ещё раз.'),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['paks'] })
      closeDialog(true)
      onSuccess()
      showSuccessToast('ПАК архивирован', `ПАК «${pak.code}» скрыт из текущего списка.`)
    },
  })

  function closeDialog(force = false) {
    if (mutation.isPending && !force) return
    onOpenChange(false)
  }

  return (
    <Dialog onOpenChange={closeDialog} open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={!mutation.isPending}>
        <DialogHeader>
          <DialogTitle>Архивировать ПАК?</DialogTitle>
          <DialogDescription>
            ПАК «{pak.code}» будет скрыт из текущего списка. Архивация не связана с доступностью
            комплекса.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={() => closeDialog()} variant="outline">
            Отмена
          </Button>
          <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending && <Spinner data-icon="inline-start" />}
            {mutation.isPending ? 'Архивация…' : 'Архивировать'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
