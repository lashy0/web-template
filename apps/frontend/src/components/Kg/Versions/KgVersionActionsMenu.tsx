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

import { ArchiveStatusKgVersion } from '@/components/Kg/Versions/ArchiveStatusKgVersion'
import { DeleteKgVersion } from '@/components/Kg/Versions/DeleteKgVersion'
import { EditKgVersion } from '@/components/Kg/Versions/EditKgVersion'
import { ViewKgVersion } from '@/components/Kg/Versions/ViewKgVersion'
import { type KgVersion } from '@/features/kg/kg-versions-api'

export function KgVersionActionsMenu({ version }: Readonly<{ version: KgVersion }>) {
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
        <span className="sr-only">Действия с версией КГ {version.code}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuGroup>
          <DropdownMenuItem onClick={() => setDetailsOpen(true)}>
            <EyeIcon />
            Подробнее
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setEditOpen(true)}>
            <PencilIcon />
            Редактировать
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setArchiveOpen(true)}>
            {version.archivedAt ? <RotateCcwIcon /> : <ArchiveIcon />}
            {version.archivedAt ? 'Восстановить' : 'Архивировать'}
          </DropdownMenuItem>
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
      <ViewKgVersion onOpenChange={setDetailsOpen} open={detailsOpen} version={version} />
      <EditKgVersion
        onOpenChange={setEditOpen}
        onSuccess={closeMenu}
        open={editOpen}
        version={version}
      />
      <ArchiveStatusKgVersion
        onOpenChange={setArchiveOpen}
        onSuccess={closeMenu}
        open={archiveOpen}
        version={version}
      />
      <DeleteKgVersion
        onOpenChange={setDeleteOpen}
        onSuccess={closeMenu}
        open={deleteOpen}
        version={version}
      />
    </DropdownMenu>
  )
}
