import { cn } from '@/lib/utils'

export type Period = 'all' | '10y' | '3y' | '1y' | '3m' | '1m'

const OPTIONS: { value: Period; label: string }[] = [
  { value: 'all', label: '전체' },
  { value: '10y', label: '10년' },
  { value: '3y',  label: '3년'  },
  { value: '1y',  label: '1년'  },
  { value: '3m',  label: '3개월' },
  { value: '1m',  label: '1개월' },
]

interface PeriodFilterProps {
  value:    Period
  onChange: (p: Period) => void
  options?: Period[]
}

export default function PeriodFilter({ value, onChange, options }: PeriodFilterProps) {
  const shown = options
    ? OPTIONS.filter((o) => options.includes(o.value))
    : OPTIONS

  return (
    <div className="flex gap-1 bg-gray-800 rounded-lg p-1">
      {shown.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            'px-3 py-1 text-xs font-medium rounded-md transition-colors',
            value === o.value
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-gray-200'
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
