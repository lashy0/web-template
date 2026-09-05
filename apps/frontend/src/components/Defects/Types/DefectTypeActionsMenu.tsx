import {
  ArchiveIcon,
  EllipsisVerticalIcon,
  EyeIcon,
  PencilIcon,
  RotateCcwIcon,
  Trash2Icon,
} from 'lucide-react'
import { useState } from 'react'

import { Button } from '@web-app/ui/components/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@web-app/ui/components/dropdown-menu'

import { ArchiveStatusDefectType } from '@/components/Defects/Types/ArchiveStatusDefectType'
import { DeleteDefectType } from '@/components/Defects/Types/DeleteDefectType'
import { EditDefectType } from '@/components/Defects/Types/EditDefectType'
import { ViewDefectType } from '@/components/Defects/Types/ViewDefectType'
import { type DefectType } from '@/features/defects/defects-api'

export function DefectTypeActionsMenu({ type }: Readonly<{ type: DefectType }>) {
  const [open, setOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const closeMenu = () => setOpen(false)
  return (
    <DropdownMenu onOpenChange={setOpen} open={open}>
      <DropdownMenuTrigger
        render={<Button className="cursor-pointer" size="icon-sm" variant="ghost" />}
      >
        <EllipsisVerticalIcon />
        <span className="sr-only">Действия с типом {type.code}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuGroup>
          <DropdownMenuItem onClick={() => setDetailsOpen(true)}>
            <EyeIcon />
            Подробнее
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setEditOpen(true)}>
            <PencilIcon />
            Изменить
          </DropdownMenuItem>
          {type.archivedAt ? (
            <DropdownMenuItem onClick={() => setArchiveOpen(true)}>
              <RotateCcwIcon />
              Восстановить
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem onClick={() => setArchiveOpen(true)}>
              <ArchiveIcon />
              Архивировать
            </DropdownMenuItem>
          )}
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="data-[variant=destructive]:hover:bg-destructive/10 data-[variant=destructive]:focus:bg-destructive/10"
          onClick={() => setDeleteOpen(true)}
          variant="destructive"
        >
          <Trash2Icon />
          Удалить
        </DropdownMenuItem>
      </DropdownMenuContent>
      <EditDefectType
        onOpenChange={setEditOpen}
        onSuccess={closeMenu}
        open={editOpen}
        type={type}
      />
      <ViewDefectType onOpenChange={setDetailsOpen} open={detailsOpen} type={type} />
      <ArchiveStatusDefectType
        onOpenChange={setArchiveOpen}
        onSuccess={closeMenu}
        open={archiveOpen}
        type={type}
      />
      <DeleteDefectType
        onOpenChange={setDeleteOpen}
        onSuccess={closeMenu}
        open={deleteOpen}
        type={type}
      />
    </DropdownMenu>
  )
}
