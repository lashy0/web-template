import { zProductionOrderCreate } from '@web-app/api-client'
import { z } from 'zod'

import { optionalText, trimmed } from '@/lib/validation'

export const productionOrderFormSchema = z.object({
  description: optionalText(zProductionOrderCreate.shape.description),
  name: trimmed(zProductionOrderCreate.shape.name),
})
