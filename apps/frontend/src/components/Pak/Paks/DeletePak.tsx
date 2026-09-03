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

import { deletePak, type Pak } from '@/features/paks/paks-api'
import useCustomToast from '@/hooks/useCustomToast'

export function DeletePak({
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
    mutationFn: () => deletePak(pak.id),
    onError: () => showErrorToast('Не удалось удалить ПАК', 'Попробуйте ещё раз.'),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['paks'] })
      closeDialog(true)
      onSuccess()
      showSuccessToast('ПАК удалён', `ПАК «${pak.code}» удалён навсегда.`)
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
          <DialogTitle>Удалить ПАК навсегда?</DialogTitle>
          <DialogDescription>
            ПАК «{pak.code}» будет удалён без возможности восстановления. Записи аудита сохранятся.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={() => closeDialog()} variant="outline">
            Отмена
          </Button>
          <Button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            variant="destructive"
          >
            {mutation.isPending && <Spinner data-icon="inline-start" />}
            {mutation.isPending ? 'Удаление…' : 'Удалить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
