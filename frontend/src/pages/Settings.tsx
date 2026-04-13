import { useState, useEffect } from 'react'
import { useSettings, useSaveSettings } from '@/hooks/useSettings'

export default function Settings() {
  const { data: settings, isLoading } = useSettings()
  const saveMut = useSaveSettings()

  const [currentAge,    setCurrentAge]    = useState(40)
  const [retirementAge, setRetirementAge] = useState(65)
  const [saved,         setSaved]         = useState(false)

  useEffect(() => {
    if (settings) {
      setCurrentAge(settings.currentAge ?? 40)
      setRetirementAge(settings.retirementAge ?? 65)
    }
  }, [settings])

  const handleSave = () => {
    saveMut.mutate({ currentAge, retirementAge }, {
      onSuccess: () => {
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
      },
    })
  }

  const inputCls = 'bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500 w-32'

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-gray-400">로딩 중...</div>
  }

  return (
    <div className="p-6 max-w-lg mx-auto space-y-6">
      <h2 className="text-xl font-bold text-gray-100">⚙️ 설정</h2>

      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 space-y-5">
        <h3 className="text-sm font-semibold text-gray-300">연금 시뮬레이션 기준</h3>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-400 block mb-1">현재 나이</label>
            <input
              type="number"
              className={inputCls}
              value={currentAge}
              min={1} max={100}
              onChange={(e) => setCurrentAge(+e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">은퇴 예정 나이</label>
            <input
              type="number"
              className={inputCls}
              value={retirementAge}
              min={1} max={100}
              onChange={(e) => setRetirementAge(+e.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={saveMut.isPending}
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50"
          >
            저장
          </button>
          {saved && <span className="text-xs text-emerald-400">저장되었습니다.</span>}
        </div>
      </div>
    </div>
  )
}
