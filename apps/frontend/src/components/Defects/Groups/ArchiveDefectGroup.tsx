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
  updateDefectGroupArchived,
  type DefectGroup,
} from '@/features/defects/defects-api'
import useCustomToast from '@/hooks/useCustomToast'

export function ArchiveDefectGroup({
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
  const [blockedByActiveTypes, setBlockedByActiveTypes] = useState(false)
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: () => updateDefectGroupArchived(group.id, true),
    onError: (error) => {
      if (defectErrorCode(error) === 'defect_group_has_unarchived_types') {
        setBlockedByActiveTypes(true)
        return
      }
      showErrorToast(
        'Не удалось архивировать группу',
        defectErrorMessage(error) ?? 'Попробуйте ещё раз.',
      )
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['defects'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      closeDialog(true)
      onSuccess()
      showSuccessToast('Группа архивирована', `Группа «${group.code}» скрыта из текущего списка.`)
    },
  })

  function closeDialog(force = false) {
    if (mutation.isPending && !force) return
    setBlockedByActiveTypes(false)
    onOpenChange(false)
  }

  const hasActiveTypes = group.activeTypesCount > 0 || blockedByActiveTypes

  return (
    <Dialog onOpenChange={closeDialog} open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={!mutation.isPending}>
        {hasActiveTypes ? (
          <ArchiveWarning group={group} onOpenChange={closeDialog} />
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Архивировать группу?</DialogTitle>
              <DialogDescription>
                Группа «{group.code}» будет скрыта из текущего списка.
              </DialogDescription>
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
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

function ArchiveWarning({
  group,
  onOpenChange,
}: Readonly<{
  group: DefectGroup
  onOpenChange: (force?: boolean) => void
}>) {
  const message =
    group.activeTypesCount > 0
      ? `В группе «${group.code}» ${activeTypesMessage(group.activeTypesCount)}. Сначала архивируйте ${typePronoun(group.activeTypesCount)}.`
      : 'В группе есть активные типы. Сначала архивируйте их.'

  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <TriangleAlertIcon aria-hidden="true" className="size-5 text-amber-500" />
          Нельзя архивировать группу
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
                defectTypesArchived: false,
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

function activeTypesMessage(count: number): string {
  const ending =
    count % 10 === 1 && count % 100 !== 11
      ? 'активный тип'
      : count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 10 || count % 100 >= 20)
        ? 'активных типа'
        : 'активных типов'
  return `есть ${count} ${ending}`
}

function typePronoun(count: number): 'его' | 'их' {
  return count % 10 === 1 && count % 100 !== 11 ? 'его' : 'их'
}
