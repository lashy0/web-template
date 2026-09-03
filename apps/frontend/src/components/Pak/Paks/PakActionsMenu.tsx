import {
  ArchiveIcon,
  CircleCheckIcon,
  EllipsisVerticalIcon,
  EyeIcon,
  KeyRoundIcon,
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

import { ArchivePak } from '@/components/Pak/Paks/ArchivePak'
import { DeletePak } from '@/components/Pak/Paks/DeletePak'
import { EditPak } from '@/components/Pak/Paks/EditPak'
import { RestorePak } from '@/components/Pak/Paks/RestorePak'
import { RotatePakAccessKey } from '@/components/Pak/Paks/RotatePakAccessKey'
import { StatusPak } from '@/components/Pak/Paks/StatusPak'
import { ViewPakAccessKey } from '@/components/Pak/Paks/ViewPakAccessKey'
import { type Pak } from '@/features/paks/paks-api'

export function PakActionsMenu({ pak }: Readonly<{ pak: Pak }>) {
  const [open, setOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [accessKeyOpen, setAccessKeyOpen] = useState(false)
  const [rotateAccessKeyOpen, setRotateAccessKeyOpen] = useState(false)
  const [statusOpen, setStatusOpen] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [restoreOpen, setRestoreOpen] = useState(false)
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
            <DropdownMenuItem onClick={() => setRestoreOpen(true)}>
              <RotateCcwIcon />
              Восстановить
            </DropdownMenuItem>
          ) : (
            <>
              <DropdownMenuItem onClick={() => setAccessKeyOpen(true)}>
                <EyeIcon />
                Показать ключ
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setRotateAccessKeyOpen(true)}>
                <KeyRoundIcon />
                Ротировать ключ
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setEditOpen(true)}>
                <PencilIcon />
                Изменить
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusOpen(true)}>
                {pak.status === 'active' ? <PowerIcon /> : <CircleCheckIcon />}
                {pak.status === 'active' ? 'Отключить' : 'Активировать'}
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
      <ViewPakAccessKey onOpenChange={setAccessKeyOpen} open={accessKeyOpen} pak={pak} />
      <RotatePakAccessKey
        onOpenChange={setRotateAccessKeyOpen}
        open={rotateAccessKeyOpen}
        pak={pak}
      />
      <StatusPak onOpenChange={setStatusOpen} onSuccess={closeMenu} open={statusOpen} pak={pak} />
      <ArchivePak
        onOpenChange={setArchiveOpen}
        onSuccess={closeMenu}
        open={archiveOpen}
        pak={pak}
      />
      <RestorePak
        onOpenChange={setRestoreOpen}
        onSuccess={closeMenu}
        open={restoreOpen}
        pak={pak}
      />
      <DeletePak onOpenChange={setDeleteOpen} onSuccess={closeMenu} open={deleteOpen} pak={pak} />
    </DropdownMenu>
  )
}
