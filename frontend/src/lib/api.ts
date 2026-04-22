import axios from 'axios'
import { deepCamel, deepSnake } from './utils'
import type { Asset, AssetType, ChartDataPoint, ChartParams, HistoryItem, Settings, RetirementPlan } from '@/types'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// 응답: snake_case → camelCase
api.interceptors.response.use((res) => {
  res.data = deepCamel(res.data)
  return res
})

// 요청: camelCase → snake_case
api.interceptors.request.use((config) => {
  if (config.data) config.data = deepSnake(config.data)
  return config
})

// ── Assets ────────────────────────────────────────────────
export const assetApi = {
  getAll: (type?: AssetType) =>
    api.get<Asset[]>('/assets', { params: type ? { type } : {} }).then((r) => r.data),

  getChart: (params: ChartParams) =>
    api.get<ChartDataPoint[]>('/assets/chart', { params }).then((r) => r.data),

  create: (data: Record<string, unknown>) =>
    api.post<{ id: string; message: string }>('/assets', data).then((r) => r.data),

  update: (id: string, data: Record<string, unknown>) =>
    api.put<{ message: string }>(`/assets/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    api.delete<{ message: string }>(`/assets/${id}`).then((r) => r.data),
}

// ── History ───────────────────────────────────────────────
export const historyApi = {
  add: (assetId: string, data: HistoryItem) =>
    api.post(`/assets/${assetId}/history`, data).then((r) => r.data),

  update: (assetId: string, date: string, data: Partial<HistoryItem>) =>
    api.put(`/assets/${assetId}/history/${date}`, data).then((r) => r.data),

  delete: (assetId: string, date: string) =>
    api.delete(`/assets/${assetId}/history/${date}`).then((r) => r.data),
}

// ── Stocks ────────────────────────────────────────────────
export const stockApi = {
  update: () =>
    api.post<{ updatedCount: number; failedTickers: string[]; message: string }>(
      '/stocks/update'
    ).then((r) => r.data),
}

// ── Settings ──────────────────────────────────────────────
export const settingsApi = {
  get: () => api.get<Settings>('/settings').then((r) => r.data),
  save: (data: Partial<Settings>) =>
    api.put<{ message: string }>('/settings', data).then((r) => r.data),
}

// ── Retirement ────────────────────────────────────────────
export const retirementApi = {
  get:  () => api.get<RetirementPlan>('/retirement').then((r) => r.data),
  save: (data: RetirementPlan) => api.put<{ message: string }>('/retirement', data).then((r) => r.data),
}
