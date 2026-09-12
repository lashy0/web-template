import { createFileRoute } from '@tanstack/react-router'

import { Batches } from '../batches'

export const Route = createFileRoute('/_layout/admin/production/batches/')({
  component: Batches,
})
