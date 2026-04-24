import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dividendApi } from '@/lib/api'
import type { DividendRecord } from '@/types'

export function useDividends(assetId: string) {
  return useQuery<DividendRecord[]>({
    queryKey: ['dividends', assetId],
    queryFn:  () => dividendApi.getByAsset(assetId),
    enabled:  !!assetId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useDividendSummary() {
  return useQuery({
    queryKey: ['dividends', 'summary'],
    queryFn:  () => dividendApi.getSummary(),
    staleTime: 5 * 60 * 1000,
  })
}

export function useAddDividend(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Omit<DividendRecord, 'id' | 'assetId'>) => dividendApi.add(assetId, data),
    onSuccess:  () => {
      qc.invalidateQueries({ queryKey: ['dividends', assetId] })
      qc.invalidateQueries({ queryKey: ['dividends', 'summary'] })
    },
  })
}

export function useDeleteDividend(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => dividendApi.remove(assetId, id),
    onSuccess:  () => {
      qc.invalidateQueries({ queryKey: ['dividends', assetId] })
      qc.invalidateQueries({ queryKey: ['dividends', 'summary'] })
    },
  })
}

export function useUpdateDividendSettings(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { dividendYield?: number; dividendDps?: number; dividendCycle?: string }) =>
      dividendApi.updateSettings(assetId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] })
      qc.invalidateQueries({ queryKey: ['dividends', 'summary'] })
    },
  })
}
