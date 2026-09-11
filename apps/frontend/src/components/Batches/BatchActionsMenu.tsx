import {
  ArchiveIcon,
  CircleCheckIcon,
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

import { type Batch } from '@/features/batches/batches-api'

import { ArchiveStatusBatch } from './ArchiveStatusBatch'
import { CompleteBatch } from './CompleteBatch'
import { DeleteBatch } from './DeleteBatch'
import { EditBatch } from './EditBatch'

export function BatchActionsMenu({ batch }: Readonly<{ batch: Batch }>) {
  const [open, setOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [completeOpen, setCompleteOpen] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const archived = batch.archivedAt !== null
  const canComplete = !archived && batch.status === 'IN_PRODUCTION'
  const closeMenu = () => setOpen(false)

  return (
    <DropdownMenu onOpenChange={setOpen} open={open}>
      <DropdownMenuTrigger
        render={<Button className="cursor-pointer" size="icon-sm" variant="ghost" />}
      >
        <EllipsisVerticalIcon />
        <span className="sr-only">Действия с партией {batch.name}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuGroup>
          {!archived ? (
            <DropdownMenuItem onClick={() => setEditOpen(true)}>
              <PencilIcon />
              Редактировать
            </DropdownMenuItem>
          ) : null}
          {canComplete ? (
            <DropdownMenuItem onClick={() => setCompleteOpen(true)}>
              <CircleCheckIcon />
              Завершить
            </DropdownMenuItem>
          ) : null}
          <DropdownMenuItem onClick={() => setArchiveOpen(true)}>
            {archived ? <RotateCcwIcon /> : <ArchiveIcon />}
            {archived ? 'Восстановить' : 'Архивировать'}
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => setDeleteOpen(true)} variant="destructive">
          <Trash2Icon />
          Удалить
        </DropdownMenuItem>
      </DropdownMenuContent>
      <EditBatch batch={batch} onOpenChange={setEditOpen} onSuccess={closeMenu} open={editOpen} />
      <CompleteBatch
        batch={batch}
        onOpenChange={setCompleteOpen}
        onSuccess={closeMenu}
        open={completeOpen}
      />
      <ArchiveStatusBatch
        batch={batch}
        onOpenChange={setArchiveOpen}
        onSuccess={closeMenu}
        open={archiveOpen}
      />
      <DeleteBatch
        batch={batch}
        onOpenChange={setDeleteOpen}
        onSuccess={closeMenu}
        open={deleteOpen}
      />
    </DropdownMenu>
  )
}
