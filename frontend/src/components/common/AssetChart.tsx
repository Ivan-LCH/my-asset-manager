import { useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { useChart } from '@/hooks/useAssets'
import PeriodFilter, { Period } from './PeriodFilter'
import type { AssetType, ChartDataPoint } from '@/types'
import { TYPE_COLORS, formatManwon } from '@/lib/utils'

interface CustomTooltipProps {
  active?:  boolean
  payload?: { name: string; value: number; color: string }[]
  label?:   string
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null

  const total = payload.reduce((s, p) => s + (p.value ?? 0), 0)
  const hasMultiple = payload.length > 1

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-3 shadow-2xl min-w-[160px]">
      <p className="text-xs text-gray-400 mb-2 font-medium">{label}</p>
      <div className="space-y-1.5">
        {payload.map((p) => (
          <div key={p.name} className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-1.5 min-w-0">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ background: p.color }} />
              <span className="text-xs text-gray-400 truncate">{p.name}</span>
            </div>
            <span className="text-xs font-semibold text-gray-100 shrink-0">{formatManwon(p.value)}</span>
          </div>
        ))}
      </div>
      {hasMultiple && (
        <div className="mt-2 pt-2 border-t border-gray-700 flex items-center justify-between">
          <span className="text-xs text-gray-400 font-medium">합계</span>
          <span className="text-sm font-bold text-blue-400">{formatManwon(total)}</span>
        </div>
      )}
      {!hasMultiple && (
        <div className="mt-1.5 pt-1.5 border-t border-gray-700 flex items-center justify-between">
          <span className="text-xs text-gray-500">합계</span>
          <span className="text-sm font-bold text-blue-400">{formatManwon(total)}</span>
        </div>
      )}
    </div>
  )
}

// recharts용: label별 색상 반환
const LABEL_COLOR_MAP: Record<string, string> = {
  '🏠 부동산':   TYPE_COLORS.REAL_ESTATE,
  '📈 주식':     TYPE_COLORS.STOCK,
  '🛡️ 연금':    TYPE_COLORS.PENSION,
  '💰 예적금':   TYPE_COLORS.SAVINGS,
  '💎 실물자산': TYPE_COLORS.PHYSICAL,
  '🎸 기타':     TYPE_COLORS.ETC,
}
const FALLBACK_COLORS = ['#60a5fa', '#34d399', '#fb923c', '#c084fc', '#f87171', '#a3e635', '#fbbf24']

interface AssetChartProps {
  type?:          AssetType
  groupBy?:       'type' | 'name' | 'account'
  account?:       string
  height?:        number
  periodOptions?: Period[]
  defaultPeriod?: Period
}

// recharts 데이터 변환: [{date, label, value}] → [{date, [label]: value}]
function pivot(data: ChartDataPoint[]) {
  const map = new Map<string, Record<string, number | string>>()
  for (const d of data) {
    if (!map.has(d.date)) map.set(d.date, { date: d.date })
    map.get(d.date)![d.label] = d.value
  }
  return Array.from(map.values())
}

function getLabels(data: ChartDataPoint[]): string[] {
  const labels = [...new Set(data.map((d) => d.label))]
  // 가장 최근 날짜 기준 값 합산 후 내림차순 정렬
  const lastDate = data.reduce((max, d) => (d.date > max ? d.date : max), '')
  const lastValues = new Map<string, number>()
  for (const d of data) {
    if (d.date === lastDate) lastValues.set(d.label, (lastValues.get(d.label) ?? 0) + d.value)
  }
  return labels.sort((a, b) => (lastValues.get(b) ?? 0) - (lastValues.get(a) ?? 0))
}

export default function AssetChart({
  type,
  groupBy = 'type',
  account,
  height = 280,
  periodOptions,
  defaultPeriod = 'all',
}: AssetChartProps) {
  const [period, setPeriod] = useState<Period>(defaultPeriod)
  const { data = [], isLoading } = useChart({ type, period, group_by: groupBy, account })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center text-gray-500 text-sm" style={{ height }}>
        로딩 중...
      </div>
    )
  }
  if (!data.length) {
    return (
      <div className="flex items-center justify-center text-gray-500 text-sm" style={{ height }}>
        데이터 없음
      </div>
    )
  }

  const pivoted = pivot(data)
  const labels  = getLabels(data)

  return (
    <div>
      <div className="flex justify-end mb-3">
        <PeriodFilter value={period} onChange={setPeriod} options={periodOptions} />
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={pivoted} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <defs>
            {labels.map((label, i) => {
              const color = LABEL_COLOR_MAP[label] ?? FALLBACK_COLORS[i % FALLBACK_COLORS.length]
              return (
                <linearGradient key={label} id={`grad-${i}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={color} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={color} stopOpacity={0}   />
                </linearGradient>
              )
            })}
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fill: '#6b7280', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: string) => v.slice(2, 7)}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#6b7280', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `${Math.round(v / 1000).toLocaleString()}천`}
            width={60}
          />
          <Tooltip content={<CustomTooltip />} />
          {labels.length > 1 && (
            <Legend
              wrapperStyle={{ fontSize: 12, color: '#9ca3af', paddingTop: 8 }}
            />
          )}
          {labels.map((label, i) => {
            const color = LABEL_COLOR_MAP[label] ?? FALLBACK_COLORS[i % FALLBACK_COLORS.length]
            return (
              <Area
                key={label}
                type="monotone"
                dataKey={label}
                stackId="1"
                stroke={color}
                strokeWidth={1.5}
                fill={`url(#grad-${i})`}
              />
            )
          })}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
