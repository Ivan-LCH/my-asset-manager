import { useMutation, useQueryClient } from '@tanstack/react-query'
import { stockApi } from '@/lib/api'

export function useUpdateStocks() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => stockApi.update(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['assets'] }),
  })
}
