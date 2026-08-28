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

export function RestoreUser({
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
  const mutation = useMutation({
    mutationFn: () => updateUserArchived(user.id, false),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['users'] })
      closeDialog(true)
      onSuccess()
      showSuccessToast(
        'Пользователь востановлен',
        `Учетная запись «${user.name}» возвращена из архива.`,
      )
    },
    onError: () => {
      showErrorToast('Не удалось востановить пользователя', 'Попробуйте еще раз.')
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
          <DialogTitle>Востановить пользователя?</DialogTitle>
          <DialogDescription>
            Учетная запись «{user.name}» будет возвращена из архива.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={() => closeDialog()} variant="outline">
            Отмена
          </Button>
          <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending && <Spinner data-icon="inline-start" />}
            {mutation.isPending ? 'Востановление...' : 'Востановить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
