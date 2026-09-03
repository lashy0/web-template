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
  defectErrorCode,
  defectErrorMessage,
  deleteDefectType,
  type DefectType,
} from '@/features/defects/defects-api'
import useCustomToast from '@/hooks/useCustomToast'

export function DeleteDefectType({
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
  const { showErrorToast, showSuccessToast, showWarningToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: () => deleteDefectType(type.id),
    onError: (error) => {
      if (defectErrorCode(error) === 'defect_type_cannot_be_deleted') {
        closeDialog(true)
        showWarningToast('Нельзя удалить тип', 'Тип используется в других данных.')
        return
      }
      showErrorToast('Не удалось удалить тип', defectErrorMessage(error) ?? 'Попробуйте ещё раз.')
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['defects'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      closeDialog(true)
      onSuccess()
      showSuccessToast('Тип удалён', `Тип «${type.code}» удалён навсегда.`)
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
          <DialogTitle>Удалить тип навсегда?</DialogTitle>
          <DialogDescription>
            Тип «{type.code}» будет удалён без возможности восстановления.
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
