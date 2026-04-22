import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { retirementApi } from '@/lib/api'
import type { RetirementPlan } from '@/types'

const KEY = ['retirement']

export function useRetirement() {
  return useQuery<RetirementPlan>({
    queryKey: KEY,
    queryFn: () => retirementApi.get(),
    staleTime: 5 * 60 * 1000,
  })
}

export function useSaveRetirement() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: RetirementPlan) => retirementApi.save(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}
