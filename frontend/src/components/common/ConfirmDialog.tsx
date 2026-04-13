interface ConfirmDialogProps {
  open:      boolean
  title:     string
  message:   string
  onConfirm: () => void
  onCancel:  () => void
  danger?:   boolean
}

export default function ConfirmDialog({
  open, title, message, onConfirm, onCancel, danger = false,
}: ConfirmDialogProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-80 shadow-2xl">
        <h3 className="text-base font-semibold text-gray-100 mb-2">{title}</h3>
        <p className="text-sm text-gray-400 mb-5">{message}</p>
        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-sm rounded-lg font-medium transition-colors ${
              danger
                ? 'bg-red-600 hover:bg-red-500 text-white'
                : 'bg-blue-600 hover:bg-blue-500 text-white'
            }`}
          >
            확인
          </button>
        </div>
      </div>
    </div>
  )
}
