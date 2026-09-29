import { useMutation, useQueryClient } from '@tanstack/react-query'
import { archiveDefectTypeMutation, restoreDefectTypeMutation } from '@web-app/api-client'

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
  invalidateDefectQueries,
  isDefectGroupArchivedError,
  type DefectType,
} from '@/features/defects/defects-api'
import useCustomToast from '@/hooks/useCustomToast'

export function ArchiveStatusDefectType({
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
  const restore = type.archivedAt !== null
  const action = restore ? 'Восстановить' : 'Архивировать'
  const pendingAction = restore ? 'Восстановление…' : 'Архивация…'
  const mutation = useMutation({
    ...(restore ? restoreDefectTypeMutation() : archiveDefectTypeMutation()),
    onError: (error) =>
      showErrorToast(
        `Не удалось ${action.toLowerCase()} тип`,
        isDefectGroupArchivedError(error)
          ? 'Группа типа архивирована. Сначала восстановите группу.'
          : 'Попробуйте ещё раз.',
      ),
    onSuccess: async () => {
      await invalidateDefectQueries(queryClient)
      closeDialog(true)
      onSuccess()
      showSuccessToast(
        restore ? 'Тип восстановлен' : 'Тип архивирован',
        restore
          ? `Тип «${type.code}» возвращён из архива.`
          : `Тип «${type.code}» скрыт из текущего списка.`,
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
          <DialogTitle>{action} тип?</DialogTitle>
          <DialogDescription>
            {restore ? (
              <>Тип «{type.code}» будет возвращён в текущий список.</>
            ) : (
              <>Тип «{type.code}» будет скрыт из текущего списка.</>
            )}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={() => closeDialog()} variant="outline">
            Отмена
          </Button>
          <Button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate({ path: { type_id: type.id } })}
          >
            {mutation.isPending && <Spinner data-icon="inline-start" />}
            {mutation.isPending ? pendingAction : action}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
