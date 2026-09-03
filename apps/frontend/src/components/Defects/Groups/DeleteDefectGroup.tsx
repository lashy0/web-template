import { Link } from '@tanstack/react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { TriangleAlertIcon } from 'lucide-react'
import { useState } from 'react'

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
  deleteDefectGroup,
  type DefectGroup,
} from '@/features/defects/defects-api'
import useCustomToast from '@/hooks/useCustomToast'

export function DeleteDefectGroup({
  group,
  onOpenChange,
  onSuccess,
  open,
}: Readonly<{
  group: DefectGroup
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
}>) {
  const [blockedByTypes, setBlockedByTypes] = useState(false)
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: () => deleteDefectGroup(group.id),
    onError: (error) => {
      if (defectErrorCode(error) === 'defect_group_cannot_be_deleted') {
        setBlockedByTypes(true)
        return
      }
      showErrorToast(
        'Не удалось удалить группу',
        defectErrorMessage(error) ?? 'Попробуйте ещё раз.',
      )
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['defects'] })
      closeDialog(true)
      onSuccess()
      showSuccessToast('Группа удалена', `Группа «${group.code}» удалена навсегда.`)
    },
  })

  function closeDialog(force = false) {
    if (mutation.isPending && !force) return
    setBlockedByTypes(false)
    onOpenChange(false)
  }

  const hasTypes = group.typesCount > 0 || blockedByTypes

  return (
    <Dialog onOpenChange={closeDialog} open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={!mutation.isPending}>
        {hasTypes ? (
          <DeleteWarning group={group} onOpenChange={closeDialog} />
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Удалить группу навсегда?</DialogTitle>
              <DialogDescription>
                Группа «{group.code}» будет удалена без возможности восстановления.
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
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

function DeleteWarning({
  group,
  onOpenChange,
}: Readonly<{
  group: DefectGroup
  onOpenChange: (force?: boolean) => void
}>) {
  const message =
    group.typesCount > 0
      ? `В группе «${group.code}» ${typesMessage(group.typesCount)}. Сначала удалите ${typePronoun(group.typesCount)}.`
      : 'В группе есть типы. Сначала удалите их.'

  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <TriangleAlertIcon aria-hidden="true" className="size-5 text-amber-500" />
          Нельзя удалить группу
        </DialogTitle>
        <DialogDescription>{message}</DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button onClick={() => onOpenChange()} type="button" variant="outline">
          Отмена
        </Button>
        <Button
          render={
            <Link
              state={(state) => ({
                ...state,
                defectGroupId: group.id,
                defectTypesArchived: group.activeTypesCount === 0,
              })}
              to="/admin/defects/types"
            />
          }
        >
          Перейти к типам
        </Button>
      </DialogFooter>
    </>
  )
}

function typesMessage(count: number): string {
  const ending =
    count % 10 === 1 && count % 100 !== 11
      ? 'тип'
      : count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 10 || count % 100 >= 20)
        ? 'типа'
        : 'типов'
  return `есть ${count} ${ending}`
}

function typePronoun(count: number): 'его' | 'их' {
  return count % 10 === 1 && count % 100 !== 11 ? 'его' : 'их'
}
