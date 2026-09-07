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
  DropdownMenuTrigger,
} from '@web-app/ui/components/dropdown-menu'

import { DeleteKgPrefix } from '@/components/Kg/Prefixes/DeleteKgPrefix'
import { ArchiveKgPrefix } from '@/components/Kg/Prefixes/ArchiveKgPrefix'
import { EditKgPrefix } from '@/components/Kg/Prefixes/EditKgPrefix'
import { type KgPrefix } from '@/features/kg/kg-prefixes-api'

export function KgPrefixActionsMenu({ prefix }: Readonly<{ prefix: KgPrefix }>) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const closeMenu = () => setMenuOpen(false)

  return (
    <DropdownMenu onOpenChange={setMenuOpen} open={menuOpen}>
      <DropdownMenuTrigger
        render={<Button className="cursor-pointer" size="icon-sm" variant="ghost" />}
      >
        <EllipsisVerticalIcon />
        <span className="sr-only">Действия с префиксом {prefix.prefix}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuGroup>
          <DropdownMenuItem onClick={() => setEditOpen(true)}>
            <PencilIcon />
            Изменить
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setArchiveOpen(true)}>
            {prefix.archivedAt ? <RotateCcwIcon /> : <ArchiveIcon />}
            {prefix.archivedAt ? 'Восстановить' : 'Архивировать'}
          </DropdownMenuItem>
          <DropdownMenuItem
            className="data-[variant=destructive]:hover:bg-destructive/10 data-[variant=destructive]:focus:bg-destructive/10"
            onClick={() => setDeleteOpen(true)}
            variant="destructive"
          >
            <Trash2Icon />
            Удалить
          </DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
      <EditKgPrefix
        onOpenChange={setEditOpen}
        onSuccess={closeMenu}
        open={editOpen}
        prefix={prefix}
      />
      <DeleteKgPrefix
        onOpenChange={setDeleteOpen}
        onSuccess={closeMenu}
        open={deleteOpen}
        prefix={prefix}
      />
      <ArchiveKgPrefix onOpenChange={setArchiveOpen} open={archiveOpen} prefix={prefix} />
    </DropdownMenu>
  )
}
