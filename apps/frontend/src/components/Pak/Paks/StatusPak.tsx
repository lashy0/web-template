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

import { updatePakActive, type Pak } from '@/features/paks/paks-api'
import useCustomToast from '@/hooks/useCustomToast'

export function StatusPak({
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
  const activate = pak.status !== 'active'
  const action = activate ? 'Активировать' : 'Отключить'
  const mutation = useMutation({
    mutationFn: () => updatePakActive(pak.id, activate),
    onError: () => showErrorToast(`Не удалось ${action.toLowerCase()} ПАК`, 'Попробуйте ещё раз.'),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['paks'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      closeDialog(true)
      onSuccess()
      showSuccessToast(
        activate ? 'ПАК активирован' : 'ПАК отключён',
        activate
          ? `ПАК «${pak.code}» снова разрешён к работе.`
          : `Работа ПАК «${pak.code}» запрещена.`,
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
            {activate
              ? `ПАК «${pak.code}» снова будет разрешён к работе.`
              : `Работа ПАК «${pak.code}» будет запрещена, но он останется в текущем списке.`}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={() => closeDialog()} variant="outline">
            Отмена
          </Button>
          <Button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            variant={activate ? 'default' : 'destructive'}
          >
            {mutation.isPending && <Spinner data-icon="inline-start" />}
            {mutation.isPending ? `${action}…` : action}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
