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
import { pakCodeForMessage } from '@/features/paks/pak-format'
import useCustomToast from '@/hooks/useCustomToast'

export function ArchiveStatusPak({
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
  const restore = pak.archivedAt !== null
  const action = restore ? 'Восстановить' : 'Архивировать'
  const pendingAction = restore ? 'Восстановление…' : 'Архивация…'
  const mutation = useMutation({
    mutationFn: () => updatePakArchived(pak.id, !restore),
    onError: () => showErrorToast(`Не удалось ${action.toLowerCase()} ПАК`, 'Попробуйте ещё раз.'),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['paks'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      closeDialog(true)
      onSuccess()
      showSuccessToast(
        restore ? 'ПАК восстановлен' : 'ПАК архивирован',
        restore
          ? `ПАК «${pakCodeForMessage(pak.code)}» возвращён из архива и останется отключённым.`
          : `ПАК «${pakCodeForMessage(pak.code)}» отключён и скрыт из текущего списка.`,
      )
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
          <DialogTitle>{action} ПАК?</DialogTitle>
          <DialogDescription>
            {restore ? (
              <>ПАК «{pak.code}» будет возвращён в текущий список и останется отключённым.</>
            ) : (
              <>ПАК «{pak.code}» будет отключён и скрыт из текущего списка.</>
            )}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={() => closeDialog()} variant="outline">
            Отмена
          </Button>
          <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending && <Spinner data-icon="inline-start" />}
            {mutation.isPending ? pendingAction : action}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
