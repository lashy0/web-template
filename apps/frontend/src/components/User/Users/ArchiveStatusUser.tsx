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

import { updateUserArchived, type User } from '@/features/users/users-api'
import useCustomToast from '@/hooks/useCustomToast'

export function ArchiveStatusUser({
  onOpenChange,
  onSuccess,
  open,
  user,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  user: User
}>) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const restore = user.archivedAt !== null
  const action = restore ? 'Восстановить' : 'Архивировать'
  const pendingAction = restore ? 'Восстановление…' : 'Архивация…'
  const mutation = useMutation({
    mutationFn: () => updateUserArchived(user.id, !restore),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['users'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      closeDialog(true)
      onSuccess()
      showSuccessToast(
        restore ? 'Пользователь восстановлен' : 'Пользователь архивирован',
        restore
          ? `Учётная запись «${user.name}» возвращена из архива.`
          : `Учётная запись «${user.name}» деактивирована и скрыта из обычного списка.`,
      )
    },
    onError: () => {
      showErrorToast(`Не удалось ${action.toLowerCase()} пользователя`, 'Попробуйте ещё раз.')
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
          <DialogTitle>{action} пользователя?</DialogTitle>
          <DialogDescription>
            {restore ? (
              <>Учётная запись «{user.name}» будет возвращена из архива.</>
            ) : (
              <>Учётная запись «{user.name}» будет деактивирована и скрыта из обычного списка.</>
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
