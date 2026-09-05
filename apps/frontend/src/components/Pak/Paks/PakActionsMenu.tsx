import {
  ArchiveIcon,
  CircleCheckIcon,
  EllipsisVerticalIcon,
  EyeIcon,
  PencilIcon,
  PowerIcon,
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

import { ArchiveStatusPak } from '@/components/Pak/Paks/ArchiveStatusPak'
import { DeletePak } from '@/components/Pak/Paks/DeletePak'
import { EditPak } from '@/components/Pak/Paks/EditPak'
import { StatusPak } from '@/components/Pak/Paks/StatusPak'
import { ViewPakAccessKey } from '@/components/Pak/Paks/ViewPakAccessKey'
import { type Pak } from '@/features/paks/paks-api'

export function PakActionsMenu({ pak }: Readonly<{ pak: Pak }>) {
  const [open, setOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [statusOpen, setStatusOpen] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const archived = pak.archivedAt !== null
  const closeMenu = () => setOpen(false)
  return (
    <DropdownMenu onOpenChange={setOpen} open={open}>
      <DropdownMenuTrigger
        render={<Button className="cursor-pointer" size="icon-sm" variant="ghost" />}
      >
        <EllipsisVerticalIcon />
        <span className="sr-only">Действия с ПАК {pak.code}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuGroup>
          {archived ? (
            <>
              <DropdownMenuItem onClick={() => setDetailsOpen(true)}>
                <EyeIcon />
                Просмотр
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setArchiveOpen(true)}>
                <RotateCcwIcon />
                Восстановить
              </DropdownMenuItem>
            </>
          ) : (
            <>
              <DropdownMenuItem onClick={() => setDetailsOpen(true)}>
                <EyeIcon />
                Просмотр
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setEditOpen(true)}>
                <PencilIcon />
                Изменить
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusOpen(true)}>
                {pak.status === 'active' ? <PowerIcon /> : <CircleCheckIcon />}
                {pak.status === 'active' ? 'Деактивировать' : 'Активировать'}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setArchiveOpen(true)}>
                <ArchiveIcon />
                Архивировать
              </DropdownMenuItem>
            </>
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
      <EditPak onOpenChange={setEditOpen} onSuccess={closeMenu} open={editOpen} pak={pak} />
      <ViewPakAccessKey onOpenChange={setDetailsOpen} open={detailsOpen} pak={pak} />
      <StatusPak onOpenChange={setStatusOpen} onSuccess={closeMenu} open={statusOpen} pak={pak} />
      <ArchiveStatusPak
        onOpenChange={setArchiveOpen}
        onSuccess={closeMenu}
        open={archiveOpen}
        pak={pak}
      />
      <DeletePak onOpenChange={setDeleteOpen} onSuccess={closeMenu} open={deleteOpen} pak={pak} />
    </DropdownMenu>
  )
}
