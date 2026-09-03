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
  defectErrorMessage,
  updateDefectTypeArchived,
  type DefectType,
} from '@/features/defects/defects-api'
import useCustomToast from '@/hooks/useCustomToast'

export function ArchiveDefectType({
  onOpenChange,
  onSuccess,
  open,
  type,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  type: DefectType
}>) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: () => updateDefectTypeArchived(type.id, true),
    onError: (error) =>
      showErrorToast(
        'Не удалось архивировать тип',
        defectErrorMessage(error) ?? 'Попробуйте ещё раз.',
      ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['defects'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      closeDialog(true)
      onSuccess()
      showSuccessToast('Тип архивирован', `Тип «${type.code}» скрыт из текущего списка.`)
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
          <DialogTitle>Архивировать тип?</DialogTitle>
          <DialogDescription>Тип «{type.code}» будет скрыт из текущего списка.</DialogDescription>
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
