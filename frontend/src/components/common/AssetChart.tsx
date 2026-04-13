import { useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { useChart } from '@/hooks/useAssets'
import PeriodFilter, { Period } from './PeriodFilter'
import type { AssetType, ChartDataPoint } from '@/types'
import { TYPE_COLORS, formatManwon } from '@/lib/utils'

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
  return [...new Set(data.map((d) => d.label))]
}

export default function AssetChart({
  type,
  groupBy = 'type',
  height = 280,
  periodOptions,
  defaultPeriod = 'all',
}: AssetChartProps) {
  const [period, setPeriod] = useState<Period>(defaultPeriod)
  const { data = [], isLoading } = useChart({ type, period, group_by: groupBy })

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
            tickFormatter={(v: number) => `${Math.round(v / 10000).toLocaleString()}만`}
            width={60}
          />
          <Tooltip
            contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
            labelStyle={{ color: '#9ca3af', fontSize: 12 }}
            formatter={(value: number, name: string) => [formatManwon(value), name]}
          />
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
