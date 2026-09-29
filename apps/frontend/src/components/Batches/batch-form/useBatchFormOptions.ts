import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import {
  listKgPrefixesOptions,
  listKgVersionsOptions,
  listProductionOrdersOptions,
} from '@web-app/api-client'

import type { SelectOption, SelectOptionsState } from './types'
import { formatDevEuiPrefix } from '@/features/kg/kg-prefix-format'

/** Current catalog entries sorted by name, the first hundred of each. */
const catalogQuery = {
  archived: false,
  orderBy: 'name',
  pageSize: 100,
  sortOrder: 'asc',
} as const

export function useBatchFormOptions(enabled: boolean) {
  const prefixes = useQuery({
    ...listKgPrefixesOptions({ query: catalogQuery }),
    enabled,
    select: (data) =>
      data.items.map((prefix) => ({
        label: prefix.name
          ? `${formatDevEuiPrefix(prefix.prefix)} (${prefix.name})`
          : formatDevEuiPrefix(prefix.prefix),
        value: prefix.id,
      })),
  })
  const versions = useQuery({
    ...listKgVersionsOptions({ query: catalogQuery }),
    enabled,
    select: (data) =>
      data.items.map((version) => ({
        label: `${version.code} (${version.name})`,
        value: version.id,
      })),
  })
  const orders = useQuery({
    ...listProductionOrdersOptions({ query: catalogQuery }),
    enabled,
    select: (data) => data.items.map((order) => ({ label: order.name, value: order.id })),
  })

  return {
    prefixes: optionsState(prefixes),
    versions: optionsState(versions),
    orders: optionsState(orders),
  }
}

function optionsState(query: UseQueryResult<SelectOption[], unknown>): SelectOptionsState {
  return {
    items: query.data ?? [],
    loading: query.isPending || (query.isError && query.isFetching),
    error: query.isError,
    retry: () => {
      void query.refetch()
    },
  }
}
