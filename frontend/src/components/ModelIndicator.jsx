export const ModelIndicator = ({ modelUsed, reason }) => {
  if (!modelUsed) return null

  const getModelColor = (model) => {
    if (model.includes('gpt-5-pro')) return 'bg-purple-600'
    if (model.includes('gpt-5') || model.includes('mini')) return 'bg-blue-600'
    if (model.includes('DeepSeek')) return 'bg-green-600'
    return 'bg-gray-600'
  }

  return (
    <div className="mt-2 text-xs text-gray-400 space-y-1">
      <div className={`${getModelColor(modelUsed)} px-3 py-1 rounded inline-block text-white`}>
        {modelUsed}
      </div>
      {reason && (
        <div className="italic text-gray-500">
          Reason: {reason}
        </div>
      )}
    </div>
  )
}
