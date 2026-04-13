import { useMutation, useQueryClient } from '@tanstack/react-query'
import { historyApi } from '@/lib/api'
import type { HistoryItem } from '@/types'

export function useAddHistory(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: HistoryItem) => historyApi.add(assetId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['assets'] }),
  })
}

export function useUpdateHistory(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ date, data }: { date: string; data: Partial<HistoryItem> }) =>
      historyApi.update(assetId, date, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['assets'] }),
  })
}

export function useDeleteHistory(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (date: string) => historyApi.delete(assetId, date),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['assets'] }),
  })
}
