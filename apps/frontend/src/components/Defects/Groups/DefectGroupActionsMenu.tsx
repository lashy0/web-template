import {
  ArchiveIcon,
  EllipsisVerticalIcon,
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

import { ArchiveStatusDefectGroup } from '@/components/Defects/Groups/ArchiveStatusDefectGroup'
import { DeleteDefectGroup } from '@/components/Defects/Groups/DeleteDefectGroup'
import { EditDefectGroup } from '@/components/Defects/Groups/EditDefectGroup'
import { type DefectGroup } from '@/features/defects/defects-api'

export function DefectGroupActionsMenu({ group }: Readonly<{ group: DefectGroup }>) {
  const [open, setOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const closeMenu = () => setOpen(false)
  return (
    <DropdownMenu onOpenChange={setOpen} open={open}>
      <DropdownMenuTrigger
        render={<Button className="cursor-pointer" size="icon-sm" variant="ghost" />}
      >
        <EllipsisVerticalIcon />
        <span className="sr-only">Действия с группой {group.code}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuGroup>
          <DropdownMenuItem onClick={() => setEditOpen(true)}>
            <PencilIcon />
            Изменить
          </DropdownMenuItem>
          {group.archivedAt ? (
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
      <EditDefectGroup
        group={group}
        onOpenChange={setEditOpen}
        onSuccess={closeMenu}
        open={editOpen}
      />
      <ArchiveStatusDefectGroup
        group={group}
        onOpenChange={setArchiveOpen}
        onSuccess={closeMenu}
        open={archiveOpen}
      />
      <DeleteDefectGroup
        group={group}
        onOpenChange={setDeleteOpen}
        onSuccess={closeMenu}
        open={deleteOpen}
      />
    </DropdownMenu>
  )
}
