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

import { updateUserActive, type User } from '@/features/users/users-api'
import useCustomToast from '@/hooks/useCustomToast'

export function StatusUser({
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
  const active = user.authState !== 'active'
  const action = active ? 'Активировать' : 'Деактивировать'

  const mutation = useMutation({
    mutationFn: () => updateUserActive(user.id, active),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['users'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      closeDialog(true)
      onSuccess()
      showSuccessToast(
        `Пользователь ${active ? 'активирован' : 'деактивирован'}`,
        active
          ? `Учётная запись «${user.name}» снова может войти в систему.`
          : `Учётная запись «${user.name}» больше не может войти в систему.`,
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
            {active
              ? `Пользователь «${user.name}» снова сможет войти в систему.`
              : `Пользователь «${user.name}» не сможет войти в систему. Его активные сессии будут завершены.`}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={() => closeDialog()} variant="outline">
            Отмена
          </Button>
          <Button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            variant={active ? 'default' : 'destructive'}
          >
            {mutation.isPending && <Spinner data-icon="inline-start" />}
            {mutation.isPending ? `${action}…` : action}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
