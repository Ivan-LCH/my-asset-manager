import { useState, useEffect, useCallback } from 'react'
import { Plus, Trash2, RotateCcw, Save } from 'lucide-react'
import { useAssets } from '@/hooks/useAssets'
import { useSettings } from '@/hooks/useSettings'
import { useRetirement, useSaveRetirement } from '@/hooks/useRetirement'
import { formatMoney, formatManwon } from '@/lib/utils'
import type {
  Asset, PensionDetail, StockDetail, SavingsDetail,
  RetirementPlan, ExpenseItem, TravelItem, LumpsumItem, EmergencyItem,
} from '@/types'

// ── 연금 시뮬레이션 (PensionPage와 동일 로직) ──────────────
const SIM_START_YEAR = 2029

function calcPensionByYear(assets: Asset[], currentAge: number): Map<number, number> {
  const currentYear = new Date().getFullYear()
  const endYear = currentYear + (100 - currentAge)
  const map = new Map<number, number>()
  for (let year = SIM_START_YEAR; year <= endYear; year++) {
    let monthly = 0
    for (const a of assets) {
      if (a.type === 'PENSION') {
        const d = a.detail as PensionDetail | undefined
        if (!d) continue
        if (year >= d.expectedStartYear && year <= d.expectedEndYear) {
          const elapsed = year - d.expectedStartYear
          monthly += d.expectedMonthlyPayout * Math.pow(1 + (d.annualGrowthRate ?? 0) / 100, elapsed)
        }
      }
      if (a.type === 'STOCK' || a.type === 'SAVINGS') {
        const d = a.detail as (StockDetail & SavingsDetail) | undefined
        if (!d?.isPensionLike) continue
        if (d.pensionStartYear && year >= d.pensionStartYear) monthly += d.pensionMonthly ?? 0
      }
    }
    map.set(year, monthly)
  }
  return map
}

// ── 기본값 (2인 가구) ──────────────────────────────────────
const uid = () => Math.random().toString(36).slice(2, 9)

const DEFAULT_EXPENSES: ExpenseItem[] = [
  { id: uid(), name: '식비',       amount: 600_000 },
  { id: uid(), name: '주거관리비', amount: 200_000 },
  { id: uid(), name: '교통비',     amount: 150_000 },
  { id: uid(), name: '통신비',     amount: 80_000  },
  { id: uid(), name: '문화/여가',  amount: 200_000 },
  { id: uid(), name: '의복/미용',  amount: 100_000 },
  { id: uid(), name: '경조사비',   amount: 100_000 },
  { id: uid(), name: '기타잡비',   amount: 150_000 },
]

const EMPTY_PLAN: RetirementPlan = {
  expenses: DEFAULT_EXPENSES,
  travel: [],
  medicalMonthly: 200_000,
  lumpsum: [],
  emergency: [],
}

// ── 유틸 ───────────────────────────────────────────────────
function numFmt(v: number | string) {
  const n = typeof v === 'string' ? Number(v.replace(/,/g, '')) : v
  return isNaN(n) ? '' : n.toLocaleString()
}
function parseNum(s: string) { return Number(s.replace(/,/g, '')) || 0 }

function pnlColor(v: number) {
  if (v > 0) return 'text-emerald-400'
  if (v < 0) return 'text-red-400'
  return 'text-gray-400'
}

// ── 섹션 래퍼 ─────────────────────────────────────────────
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 space-y-3">
      <h3 className="text-sm font-semibold text-gray-300">{title}</h3>
      {children}
    </div>
  )
}

// ── 인풋 ──────────────────────────────────────────────────
function AmountInput({
  value, onChange, placeholder = '금액',
}: { value: number; onChange: (v: number) => void; placeholder?: string }) {
  const [raw, setRaw] = useState(value > 0 ? numFmt(value) : '')
  useEffect(() => { setRaw(value > 0 ? numFmt(value) : '') }, [value])
  return (
    <input
      type="text"
      inputMode="numeric"
      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-sm text-gray-100
        focus:outline-none focus:border-blue-500 text-right"
      placeholder={placeholder}
      value={raw}
      onChange={(e) => setRaw(e.target.value)}
      onBlur={() => { const n = parseNum(raw); onChange(n); setRaw(n > 0 ? numFmt(n) : '') }}
    />
  )
}

function TextInput({
  value, onChange, placeholder = '',
}: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <input
      type="text"
      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-sm text-gray-100
        focus:outline-none focus:border-blue-500"
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

function YearInput({
  value, onChange,
}: { value: number; onChange: (v: number) => void }) {
  return (
    <input
      type="number"
      className="w-24 bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-sm text-gray-100
        focus:outline-none focus:border-blue-500"
      value={value || ''}
      onChange={(e) => onChange(Number(e.target.value))}
    />
  )
}

// ── 월 생활비 섹션 ─────────────────────────────────────────
function ExpensesSection({
  items, onChange,
}: { items: ExpenseItem[]; onChange: (items: ExpenseItem[]) => void }) {
  const total = items.reduce((s, i) => s + i.amount, 0)

  const update = (id: string, field: keyof ExpenseItem, val: string | number) =>
    onChange(items.map((i) => (i.id === id ? { ...i, [field]: val } : i)))

  return (
    <Section title="💰 월 생활비">
      <div className="space-y-1.5">
        {items.map((item) => (
          <div key={item.id} className="flex items-center gap-2">
            <TextInput
              value={item.name}
              onChange={(v) => update(item.id, 'name', v)}
              placeholder="항목명"
            />
            <div className="w-36 shrink-0">
              <AmountInput value={item.amount} onChange={(v) => update(item.id, 'amount', v)} />
            </div>
            <button
              onClick={() => onChange(items.filter((i) => i.id !== item.id))}
              className="p-1.5 text-gray-600 hover:text-red-400 transition-colors shrink-0"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between pt-1">
        <div className="flex gap-2">
          <button
            onClick={() => onChange([...items, { id: uid(), name: '', amount: 0 }])}
            className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            <Plus className="w-3 h-3" /> 항목 추가
          </button>
          <button
            onClick={() => onChange(DEFAULT_EXPENSES.map((e) => ({ ...e, id: uid() })))}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            <RotateCcw className="w-3 h-3" /> 기본값
          </button>
        </div>
        <p className="text-sm font-bold text-gray-100">
          합계 <span className="text-blue-400">{formatManwon(total)}/월</span>
        </p>
      </div>
    </Section>
  )
}

// ── 여행비 섹션 ────────────────────────────────────────────
function TimesInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <input
      type="number"
      min={0}
      className="w-12 bg-gray-700 border border-gray-600 rounded-lg px-2 py-1.5 text-sm text-gray-100
        focus:outline-none focus:border-blue-500 text-center"
      value={value || ''}
      onChange={(e) => onChange(Number(e.target.value))}
    />
  )
}

function TravelSection({
  items, onChange,
}: { items: TravelItem[]; onChange: (items: TravelItem[]) => void }) {
  const update = (id: string, field: keyof TravelItem, val: string | number) =>
    onChange(items.map((i) => (i.id === id ? { ...i, [field]: val } : i)))

  return (
    <Section title="✈️ 여행비">
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.id} className="bg-gray-750 border border-gray-700 rounded-lg p-3 space-y-2">
            <div className="flex items-center gap-2">
              <TextInput
                value={item.name}
                onChange={(v) => update(item.id, 'name', v)}
                placeholder="여행 종류 (예: 국내여행)"
              />
              <div className="w-32 shrink-0">
                <AmountInput value={item.costPerTrip} onChange={(v) => update(item.id, 'costPerTrip', v)} placeholder="회당 금액" />
              </div>
              <button
                onClick={() => onChange(items.filter((i) => i.id !== item.id))}
                className="p-1.5 text-gray-600 hover:text-red-400 transition-colors shrink-0"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-400 flex-wrap">
              <TimesInput value={item.phase1Times} onChange={(v) => update(item.id, 'phase1Times', v)} />
              <span>회/년</span>
              <YearInput value={item.phase1Until} onChange={(v) => update(item.id, 'phase1Until', v)} />
              <span>년까지, 이후</span>
              <TimesInput value={item.phase2Times} onChange={(v) => update(item.id, 'phase2Times', v)} />
              <span>회/년</span>
            </div>
            {item.costPerTrip > 0 && (
              <p className="text-[11px] text-blue-400">
                → ~{item.phase1Until}년: {formatManwon(item.phase1Times * item.costPerTrip / 12)}/월
                &nbsp;·&nbsp;
                이후: {formatManwon(item.phase2Times * item.costPerTrip / 12)}/월
              </p>
            )}
          </div>
        ))}
      </div>
      <button
        onClick={() => onChange([...items, { id: uid(), name: '', costPerTrip: 0, phase1Times: 4, phase1Until: 2045, phase2Times: 1 }])}
        className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
      >
        <Plus className="w-3 h-3" /> 추가
      </button>
    </Section>
  )
}

// ── 목돈 수입 섹션 ─────────────────────────────────────────
function LumpsumSection({
  items, onChange,
}: { items: LumpsumItem[]; onChange: (items: LumpsumItem[]) => void }) {
  const update = (id: string, field: keyof LumpsumItem, val: string | number) =>
    onChange(items.map((i) => (i.id === id ? { ...i, [field]: val } : i)))

  return (
    <Section title="💎 목돈 수입 (전세금·퇴직금 등)">
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.id} className="bg-gray-750 rounded-lg border border-gray-700 p-3 space-y-2">
            <div className="flex items-center gap-2">
              <TextInput
                value={item.name}
                onChange={(v) => update(item.id, 'name', v)}
                placeholder="항목명 (예: 전세금 반환)"
              />
              <button
                onClick={() => onChange(items.filter((i) => i.id !== item.id))}
                className="p-1.5 text-gray-600 hover:text-red-400 transition-colors shrink-0"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <p className="text-[10px] text-gray-500 mb-1">수령 연도</p>
                <YearInput value={item.receiveYear} onChange={(v) => update(item.id, 'receiveYear', v)} />
              </div>
              <div>
                <p className="text-[10px] text-gray-500 mb-1">사용 종료 연도</p>
                <YearInput value={item.useEndYear} onChange={(v) => update(item.id, 'useEndYear', v)} />
              </div>
              <div>
                <p className="text-[10px] text-gray-500 mb-1">금액</p>
                <AmountInput value={item.amount} onChange={(v) => update(item.id, 'amount', v)} />
              </div>
            </div>
            {item.receiveYear > 0 && item.useEndYear >= item.receiveYear && item.amount > 0 && (
              <p className="text-[11px] text-blue-400">
                → 월 {formatManwon(item.amount / ((item.useEndYear - item.receiveYear + 1) * 12))} 환산
                ({item.useEndYear - item.receiveYear + 1}년간)
              </p>
            )}
          </div>
        ))}
      </div>
      <button
        onClick={() => onChange([...items, { id: uid(), name: '', receiveYear: 2030, amount: 0, useEndYear: 2040 }])}
        className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
      >
        <Plus className="w-3 h-3" /> 추가
      </button>
    </Section>
  )
}

// ── 긴급자금 섹션 ──────────────────────────────────────────
function EmergencySection({
  items, onChange,
}: { items: EmergencyItem[]; onChange: (items: EmergencyItem[]) => void }) {
  const update = (id: string, field: keyof EmergencyItem, val: string | number) =>
    onChange(items.map((i) => (i.id === id ? { ...i, [field]: val } : i)))

  return (
    <Section title="🚨 긴급자금 (일회성 지출)">
      <div className="space-y-1.5">
        {items.map((item) => (
          <div key={item.id} className="flex items-center gap-2">
            <TextInput
              value={item.name}
              onChange={(v) => update(item.id, 'name', v)}
              placeholder="항목명 (예: 아들 결혼)"
            />
            <YearInput value={item.year} onChange={(v) => update(item.id, 'year', v)} />
            <div className="w-36 shrink-0">
              <AmountInput value={item.amount} onChange={(v) => update(item.id, 'amount', v)} />
            </div>
            <button
              onClick={() => onChange(items.filter((i) => i.id !== item.id))}
              className="p-1.5 text-gray-600 hover:text-red-400 transition-colors shrink-0"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
      <button
        onClick={() => onChange([...items, { id: uid(), name: '', year: 2030, amount: 0 }])}
        className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
      >
        <Plus className="w-3 h-3" /> 추가
      </button>
    </Section>
  )
}

// ── 연도별 현금흐름 테이블 ─────────────────────────────────
interface CashFlowRow {
  year:            number
  age:             number
  pensionMonthly:  number
  expenseMonthly:  number
  travelMonthly:   number
  medicalMonthly:  number
  totalExpense:    number
  lumpsumMonthly:  number
  totalIncome:     number
  balance:         number
  emergencyAnnual: number
  cumulative:      number  // 누적자금 (전년도 이월 + 당해 연간여유 - 긴급지출)
}

function buildCashFlow(
  plan: RetirementPlan,
  pensionMap: Map<number, number>,
  currentAge: number,
): CashFlowRow[] {
  const currentYear = new Date().getFullYear()
  const endYear = currentYear + (100 - currentAge)
  const rows: CashFlowRow[] = []

  const expenseMonthly = plan.expenses.reduce((s, e) => s + e.amount, 0)

  let cumulative = 0

  for (let year = SIM_START_YEAR; year <= endYear; year++) {
    const age = currentAge + (year - currentYear)

    // 여행비: phase1Until 이하면 phase1Times, 이후면 phase2Times
    const travelMonthly = plan.travel.reduce((s, t) => {
      const times = year <= t.phase1Until ? t.phase1Times : t.phase2Times
      return s + (times * t.costPerTrip) / 12
    }, 0)

    const pensionMonthly = pensionMap.get(year) ?? 0

    const lumpsumMonthly = plan.lumpsum.reduce((s, l) => {
      if (l.receiveYear > 0 && l.useEndYear >= l.receiveYear && year >= l.receiveYear && year <= l.useEndYear) {
        return s + l.amount / ((l.useEndYear - l.receiveYear + 1) * 12)
      }
      return s
    }, 0)

    const emergencyAnnual = plan.emergency.reduce((s, e) => (e.year === year ? s + e.amount : s), 0)

    const totalExpense = expenseMonthly + travelMonthly + plan.medicalMonthly
    const totalIncome  = pensionMonthly + lumpsumMonthly
    const balance      = totalIncome - totalExpense

    // 누적자금: 월 여유/부족 × 12 - 긴급지출
    cumulative += balance * 12 - emergencyAnnual

    rows.push({
      year, age,
      pensionMonthly, expenseMonthly, travelMonthly,
      medicalMonthly: plan.medicalMonthly,
      totalExpense, lumpsumMonthly, totalIncome, balance,
      emergencyAnnual, cumulative,
    })
  }
  return rows
}

// ── 메인 페이지 ────────────────────────────────────────────
export default function RetirementPage() {
  const { data: allAssets = [] } = useAssets()
  const { data: settings }       = useSettings()
  const { data: saved }          = useRetirement()
  const saveMut                  = useSaveRetirement()

  const currentAge    = settings?.currentAge    ?? 40
  const retirementAge = settings?.retirementAge ?? 65

  const [plan, setPlan] = useState<RetirementPlan>(EMPTY_PLAN)
  const [dirty, setDirty] = useState(false)

  // 저장된 데이터 로드
  useEffect(() => {
    if (saved && Object.keys(saved).length > 0) {
      setPlan({
        expenses:       saved.expenses       ?? DEFAULT_EXPENSES,
        travel:         saved.travel         ?? [],
        medicalMonthly: saved.medicalMonthly ?? 200_000,
        lumpsum:        saved.lumpsum        ?? [],
        emergency:      saved.emergency      ?? [],
      })
    }
  }, [saved])

  const update = useCallback(<K extends keyof RetirementPlan>(key: K, val: RetirementPlan[K]) => {
    setPlan((p) => ({ ...p, [key]: val }))
    setDirty(true)
  }, [])

  const handleSave = () => {
    saveMut.mutate(plan, { onSuccess: () => setDirty(false) })
  }

  // 연금 수입 맵
  const pensionLikeAssets = allAssets.filter((a) => {
    if (a.type === 'PENSION') return true
    if ((a.type === 'STOCK' || a.type === 'SAVINGS') && (a.detail as StockDetail & SavingsDetail)?.isPensionLike) return true
    return false
  })
  const pensionMap = calcPensionByYear(pensionLikeAssets, currentAge)
  const cashFlow   = buildCashFlow(plan, pensionMap, currentAge)

  // KPI
  const retirementYear = new Date().getFullYear() + (retirementAge - currentAge)
  const retirementRow  = cashFlow.find((r) => r.year >= retirementYear)
  const totalExpenseMonthly = (plan.expenses.reduce((s, e) => s + e.amount, 0))
    + plan.travel.reduce((s, t) => s + (t.phase1Times * t.costPerTrip) / 12, 0)
    + plan.medicalMonthly

  return (
    <div className="p-4 md:p-6 space-y-5 max-w-5xl mx-auto">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-100">🌅 은퇴 생활비 계획</h2>
        <button
          onClick={handleSave}
          disabled={!dirty || saveMut.isPending}
          className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-500
            text-white transition-colors disabled:opacity-40"
        >
          <Save className="w-4 h-4" />
          {saveMut.isPending ? '저장 중...' : dirty ? '저장' : '저장됨'}
        </button>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">월 예상 지출</p>
          <p className="text-lg font-bold text-gray-100">{formatManwon(totalExpenseMonthly)}</p>
          <p className="text-[11px] text-gray-600 mt-0.5">생활비 + 여행 + 의료</p>
        </div>
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">은퇴 시 연금 수령</p>
          <p className="text-lg font-bold text-gray-100">
            {retirementRow ? formatManwon(retirementRow.pensionMonthly) : '-'}
          </p>
          <p className="text-[11px] text-gray-600 mt-0.5">{retirementAge}세 ({retirementYear}년)</p>
        </div>
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">은퇴 시 월 여유/부족</p>
          <p className={`text-lg font-bold ${pnlColor(retirementRow?.balance ?? 0)}`}>
            {retirementRow
              ? `${retirementRow.balance >= 0 ? '+' : ''}${formatManwon(retirementRow.balance)}`
              : '-'}
          </p>
          <p className="text-[11px] text-gray-600 mt-0.5">목돈 제외 기준</p>
        </div>
      </div>

      {/* 설정 패널 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ExpensesSection items={plan.expenses} onChange={(v) => update('expenses', v)} />

        <div className="space-y-4">
          <TravelSection items={plan.travel} onChange={(v) => update('travel', v)} />

          <Section title="🏥 의료비 적립">
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-400">월 적립액</span>
              <div className="w-40">
                <AmountInput
                  value={plan.medicalMonthly}
                  onChange={(v) => update('medicalMonthly', v)}
                />
              </div>
              <span className="text-xs text-gray-500">/월</span>
            </div>
          </Section>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <LumpsumSection  items={plan.lumpsum}   onChange={(v) => update('lumpsum', v)} />
        <EmergencySection items={plan.emergency} onChange={(v) => update('emergency', v)} />
      </div>

      {/* 연도별 현금흐름 테이블 */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-300 mb-4">📊 연도별 현금흐름</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-gray-700">
                <th className="text-left py-2 pr-3 font-medium">연도</th>
                <th className="text-right py-2 px-2 font-medium">나이</th>
                <th className="text-right py-2 px-2 font-medium">연금/월</th>
                <th className="text-right py-2 px-2 font-medium">목돈/월</th>
                <th className="text-right py-2 px-2 font-medium">총수입/월</th>
                <th className="text-right py-2 px-2 font-medium">생활비/월</th>
                <th className="text-right py-2 px-2 font-medium">여행/월</th>
                <th className="text-right py-2 px-2 font-medium">의료/월</th>
                <th className="text-right py-2 px-2 font-medium">총지출/월</th>
                <th className="text-right py-2 px-2 font-medium">여유/부족</th>
                <th className="text-right py-2 px-2 font-medium">긴급지출</th>
                <th className="text-right py-2 pl-2 font-medium">누적자금</th>
              </tr>
            </thead>
            <tbody>
              {cashFlow.map((row) => {
                const isRetirementYear = row.year === retirementYear
                const hasEmergency     = row.emergencyAnnual > 0
                return (
                  <tr
                    key={row.year}
                    className={`border-b border-gray-700/50 ${
                      isRetirementYear ? 'bg-blue-500/10' : 'hover:bg-gray-700/30'
                    }`}
                  >
                    <td className={`py-2 pr-3 font-medium ${isRetirementYear ? 'text-blue-400' : 'text-gray-300'}`}>
                      {row.year}
                      {isRetirementYear && <span className="ml-1 text-[10px] text-blue-500">은퇴</span>}
                    </td>
                    <td className="text-right py-2 px-2 text-gray-400">{row.age}세</td>
                    <td className="text-right py-2 px-2 text-gray-300">
                      {row.pensionMonthly > 0 ? formatManwon(row.pensionMonthly) : '—'}
                    </td>
                    <td className="text-right py-2 px-2 text-gray-300">
                      {row.lumpsumMonthly > 0 ? formatManwon(row.lumpsumMonthly) : '—'}
                    </td>
                    <td className="text-right py-2 px-2 font-semibold text-gray-100">
                      {formatManwon(row.totalIncome)}
                    </td>
                    <td className="text-right py-2 px-2 text-gray-400">{formatManwon(row.expenseMonthly)}</td>
                    <td className="text-right py-2 px-2 text-gray-400">
                      {row.travelMonthly > 0 ? formatManwon(row.travelMonthly) : '—'}
                    </td>
                    <td className="text-right py-2 px-2 text-gray-400">
                      {row.medicalMonthly > 0 ? formatManwon(row.medicalMonthly) : '—'}
                    </td>
                    <td className="text-right py-2 px-2 font-semibold text-gray-100">
                      {formatManwon(row.totalExpense)}
                    </td>
                    <td className={`text-right py-2 px-2 font-bold ${pnlColor(row.balance)}`}>
                      {row.balance >= 0 ? '+' : ''}{formatManwon(row.balance)}
                    </td>
                    <td className={`text-right py-2 px-2 ${hasEmergency ? 'text-orange-400 font-semibold' : 'text-gray-600'}`}>
                      {hasEmergency ? formatManwon(row.emergencyAnnual) : '—'}
                    </td>
                    <td className={`text-right py-2 pl-2 font-semibold ${pnlColor(row.cumulative)}`}>
                      {row.cumulative >= 0 ? '+' : ''}{formatManwon(row.cumulative)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
