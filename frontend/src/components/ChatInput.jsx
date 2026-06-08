import { useState, useRef, useEffect } from 'react'

export const ChatInput = ({
  onSend,
  isLoading,
  isVoiceActive,
  voiceStatus,
  onToggleVoice,
  isRagMode,
  onToggleRag,
  onImageSend,
}) => {
  const [input, setInput] = useState('')
  const [selectedImage, setSelectedImage] = useState(null)
  const [imagePreviewUrl, setImagePreviewUrl] = useState('')
  const inputRef = useRef(null)
  const imageInputRef = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    if (!selectedImage) {
      setImagePreviewUrl('')
      return undefined
    }

    const previewUrl = URL.createObjectURL(selectedImage)
    setImagePreviewUrl(previewUrl)
    return () => URL.revokeObjectURL(previewUrl)
  }, [selectedImage])

  const handleSubmit = (e) => {
    e.preventDefault()
    const prompt = input.trim()
    if (isLoading || (!prompt && !selectedImage)) {
      return
    }

    if (selectedImage) {
      onImageSend(selectedImage, prompt)
      setSelectedImage(null)
    } else {
      onSend(prompt)
    }
    setInput('')
  }

  const handleImageChange = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedImage(file)
      window.requestAnimationFrame(() => inputRef.current?.focus())
    }
    e.target.value = ''
  }

  const removeSelectedImage = () => {
    setSelectedImage(null)
    window.requestAnimationFrame(() => inputRef.current?.focus())
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="border-t border-slate-800 bg-slate-950 px-4 py-4 sm:px-6">
      <div className="mx-auto w-full max-w-4xl">
        <form onSubmit={handleSubmit} className="rounded-lg border border-slate-800 bg-slate-900 p-2 shadow-2xl shadow-black/20">
          {selectedImage && (
            <div className="mx-2 mt-1 flex items-center gap-3 border-b border-slate-800 pb-3">
              <img
                src={imagePreviewUrl}
                alt={`Preview of ${selectedImage.name}`}
                className="h-16 w-16 shrink-0 rounded-md border border-slate-700 bg-slate-950 object-cover"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-200">{selectedImage.name}</p>
                <p className="mt-1 text-xs text-slate-500">Image attached</p>
              </div>
              <button
                type="button"
                onClick={removeSelectedImage}
                disabled={isLoading}
                className="control-button shrink-0"
                title="Remove image"
                aria-label="Remove attached image"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4">
                  <path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
            </div>
          )}
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={selectedImage ? 'What would you like to know about this image?' : 'Message the Azure AI router'}
            disabled={isLoading}
            rows={1}
            className="max-h-36 min-h-12 w-full resize-none bg-transparent px-3 py-3 text-sm leading-6 text-white outline-none placeholder:text-slate-500 disabled:opacity-60 sm:text-base"
          />

          <div className="flex items-center justify-between gap-3 border-t border-slate-800 pt-2">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onToggleRag}
                disabled={isLoading}
                className={`inline-flex h-9 items-center gap-2 rounded-lg border px-3 text-xs font-medium transition ${
                  isRagMode
                    ? 'border-emerald-400/50 bg-emerald-500/15 text-emerald-100'
                    : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-600 hover:bg-slate-800'
                } disabled:cursor-not-allowed disabled:opacity-50`}
                title={isRagMode ? 'Internal Search is on' : 'Internal Search is off'}
                aria-label="Toggle Internal Search"
                aria-pressed={isRagMode}
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4">
                  <path d="M6 4h9l3 3v13H6z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
                  <path d="M15 4v4h4M9 12h6M9 16h6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <span>Internal Search</span>
                <span className={`h-2 w-2 rounded-full ${isRagMode ? 'bg-emerald-300' : 'bg-slate-600'}`} />
              </button>
              <button
                type="button"
                onClick={onToggleVoice}
                disabled={isLoading}
                className={isVoiceActive ? 'control-button-active' : 'control-button'}
                title={isVoiceActive ? 'Stop voice session' : 'Start voice session'}
                aria-label="Microphone"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4">
                  <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Z" fill="none" stroke="currentColor" strokeWidth="2" />
                  <path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
              {voiceStatus && (
                <span className="hidden text-xs text-emerald-300 sm:inline">
                  {voiceStatus}
                </span>
              )}
              <button
                type="button"
                onClick={() => imageInputRef.current?.click()}
                disabled={isLoading}
                className="control-button"
                title="Upload an image for recognition"
                aria-label="Image upload"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4">
                  <rect x="4" y="5" width="16" height="14" rx="2" fill="none" stroke="currentColor" strokeWidth="2" />
                  <path d="m7 16 4-4 3 3 2-2 3 3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="9" cy="9" r="1.5" fill="currentColor" />
                </svg>
              </button>
              <input
                ref={imageInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={handleImageChange}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading || (!input.trim() && !selectedImage)}
              className="inline-flex h-10 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              {isLoading ? 'Sending' : 'Send'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
