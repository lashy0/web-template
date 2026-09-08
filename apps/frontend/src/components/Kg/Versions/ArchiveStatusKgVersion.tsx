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

import {
  kgVersionErrorMessage,
  updateKgVersionArchived,
  type KgVersion,
} from '@/features/kg/kg-versions-api'
import useCustomToast from '@/hooks/useCustomToast'

export function ArchiveStatusKgVersion({
  onOpenChange,
  onSuccess,
  open,
  version,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  version: KgVersion
}>) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const restore = version.archivedAt !== null
  const action = restore ? 'Восстановить' : 'Архивировать'
  const pendingAction = restore ? 'Восстановление…' : 'Архивация…'
  const mutation = useMutation({
    mutationFn: () => updateKgVersionArchived(version.id, !restore),
    onError: (error) =>
      showErrorToast(
        `Не удалось ${action.toLowerCase()} версию КГ`,
        kgVersionErrorMessage(error) ?? 'Попробуйте ещё раз.',
      ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['kg', 'versions'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      close(true)
      onSuccess()
      showSuccessToast(
        restore ? 'Версия КГ восстановлена' : 'Версия КГ архивирована',
        restore
          ? `Версия «${version.code}» возвращена в текущий список.`
          : `Версия «${version.code}» скрыта из текущего списка.`,
      )
    },
  })

  function close(force = false) {
    if (mutation.isPending && !force) return
    onOpenChange(false)
  }

  return (
    <Dialog onOpenChange={close} open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={!mutation.isPending}>
        <DialogHeader>
          <DialogTitle>{action} версию КГ?</DialogTitle>
          <DialogDescription>
            {restore
              ? `Версия «${version.code}» будет возвращена в текущий список.`
              : `Версия «${version.code}» будет скрыта из текущего списка.`}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={() => close()} variant="outline">
            Отмена
          </Button>
          <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
            {mutation.isPending ? pendingAction : action}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
