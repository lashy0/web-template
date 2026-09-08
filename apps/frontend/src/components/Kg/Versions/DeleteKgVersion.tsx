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
  deleteKgVersion,
  kgVersionErrorCode,
  kgVersionErrorMessage,
  type KgVersion,
} from '@/features/kg/kg-versions-api'
import useCustomToast from '@/hooks/useCustomToast'

export function DeleteKgVersion({
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
  const { showErrorToast, showSuccessToast, showWarningToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: () => deleteKgVersion(version.id),
    onError: (error) => {
      if (kgVersionErrorCode(error) === 'kg_version_in_use') {
        close(true)
        showWarningToast(
          'Невозможно удалить версию КГ: она используется в одной или нескольких партиях.',
        )
        return
      }
      showErrorToast(
        'Не удалось удалить версию КГ',
        kgVersionErrorMessage(error) ?? 'Попробуйте ещё раз.',
      )
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['kg', 'versions'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      close(true)
      onSuccess()
      showSuccessToast('Версия КГ удалена', `Версия «${version.code}» удалена навсегда.`)
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
          <DialogTitle>Удалить версию КГ навсегда?</DialogTitle>
          <DialogDescription>
            Версия «{version.code}» будет удалена без возможности восстановления.
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
      </DialogContent>
    </Dialog>
  )
}
