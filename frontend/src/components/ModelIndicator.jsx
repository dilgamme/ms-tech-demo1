export const ModelIndicator = ({ modelUsed, reason }) => {
  if (!modelUsed) return null

  const getModelStyle = (model) => {
    const normalized = model.toLowerCase()
    if (normalized.includes('pro')) return 'border-violet-500/40 bg-violet-500/10 text-violet-200'
    if (normalized.includes('gpt') || normalized.includes('mini')) return 'border-sky-500/40 bg-sky-500/10 text-sky-200'
    if (normalized.includes('deepseek')) return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200'
    if (normalized.includes('realtime')) return 'border-amber-500/40 bg-amber-500/10 text-amber-200'
    return 'border-slate-600 bg-slate-800 text-slate-200'
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
      <span className={`rounded-full border px-2.5 py-1 font-medium ${getModelStyle(modelUsed)}`}>
        Model: {modelUsed}
      </span>
      {reason && (
        <span className="rounded-full border border-slate-700 bg-slate-900 px-2.5 py-1 text-slate-400">
          Route: {reason}
        </span>
      )}
    </div>
  )
}
