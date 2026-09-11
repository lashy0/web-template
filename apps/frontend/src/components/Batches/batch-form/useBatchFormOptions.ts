import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import type { SelectOption, SelectOptionsState } from './types'
import { formatDevEuiPrefix } from '@/features/kg/kg-prefix-format'
import { listKgPrefixes } from '@/features/kg/kg-prefixes-api'
import { listKgVersions } from '@/features/kg/kg-versions-api'
import {
  listProductionOrders,
  productionOrderQueryKeys,
} from '@/features/production-orders/production-order-api'

export function useBatchFormOptions(enabled: boolean) {
  const prefixes = useQuery({
    enabled,
    queryFn: () =>
      listKgPrefixes({ archived: false, order: 'asc', page: 1, pageSize: 100, sort: 'name' }),
    queryKey: ['kg', 'prefixes', 'batch-form'],
    select: (data) =>
      data.items.map((prefix) => ({
        label: prefix.name
          ? formatDevEuiPrefix(prefix.prefix) + ' (' + prefix.name + ')'
          : formatDevEuiPrefix(prefix.prefix),
        value: prefix.prefix,
      })),
  })
  const versions = useQuery({
    enabled,
    queryFn: () =>
      listKgVersions({ archived: false, order: 'asc', page: 1, pageSize: 100, sort: 'name' }),
    queryKey: ['kg', 'versions', 'batch-form'],
    select: (data) =>
      data.items.map((version) => ({
        label: version.name ? version.code + ' (' + version.name + ')' : version.code,
        value: version.id,
      })),
  })
  const orders = useQuery({
    enabled,
    queryFn: () =>
      listProductionOrders({
        archived: false,
        order: 'asc',
        page: 1,
        pageSize: 100,
        sort: 'name',
      }),
    select: (data) => data.items.map((order) => ({ label: order.name, value: order.id })),
    queryKey: productionOrderQueryKeys.list({
      archived: false,
      page: 1,
      pageSize: 100,
      sort: 'name',
    }),
  })

  return {
    prefixes: optionsState(prefixes),
    versions: optionsState(versions),
    orders: optionsState(orders),
  }
}

function optionsState(query: UseQueryResult<SelectOption[]>): SelectOptionsState {
  return {
    items: query.data ?? [],
    loading: query.isPending || (query.isError && query.isFetching),
    error: query.isError,
    retry: () => {
      void query.refetch()
    },
  }
}
