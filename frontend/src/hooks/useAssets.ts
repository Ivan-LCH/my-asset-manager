import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { assetApi } from '@/lib/api'
import type { Asset, AssetType, ChartParams } from '@/types'

const ASSETS_KEY = ['assets'] as const

export function useAssets() {
  return useQuery({
    queryKey: ASSETS_KEY,
    queryFn: () => assetApi.getAll(),
    staleTime: 5 * 60 * 1000,
  })
}

export function useAssetsByType(type: AssetType): Asset[] {
  const { data } = useAssets()
  return data?.filter((a) => a.type === type) ?? []
}

export function useChart(params: ChartParams) {
  return useQuery({
    queryKey: ['chart', params],
    queryFn: () => assetApi.getChart(params),
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateAsset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => assetApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ASSETS_KEY }),
  })
}

export function useUpdateAsset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      assetApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ASSETS_KEY }),
  })
}

export function useDeleteAsset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => assetApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ASSETS_KEY }),
  })
}
