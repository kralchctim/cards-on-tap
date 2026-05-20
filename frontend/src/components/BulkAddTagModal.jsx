import { useEffect, useMemo, useState } from 'react'

const API_BASE = 'http://localhost:8000'

function filterTags(tags, query) {
  const q = query.toLowerCase()
  const matching = tags.filter((t) => t.name.toLowerCase().includes(q))
  matching.sort((a, b) => {
    const aStarts = a.name.toLowerCase().startsWith(q)
    const bStarts = b.name.toLowerCase().startsWith(q)
    if (aStarts && !bStarts) return -1
    if (!aStarts && bStarts) return 1
    return a.name.localeCompare(b.name)
  })
  return matching
}

export default function BulkAddTagModal({ selectedCardIds, onClose, onSuccess }) {
  const [allTags, setAllTags] = useState([])
  const [step, setStep] = useState('pick')
  const [input, setInput] = useState('')
  const [focused, setFocused] = useState(false)
  const [tagName, setTagName] = useState('')
  const [tagDescription, setTagDescription] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [openDescriptionTagId, setOpenDescriptionTagId] = useState(null)

  const count = selectedCardIds.size
  const trimmedInput = input.trim()
  const filtered = useMemo(() => filterTags(allTags, input), [allTags, input])
  const showDropdown = step === 'pick' && focused && input.length >= 1

  useEffect(() => {
    let cancelled = false
    async function fetchTags() {
      try {
        const res = await fetch(`${API_BASE}/tags`)
        if (!res.ok) return
        const data = await res.json()
        if (!cancelled) setAllTags(data)
      } catch {
        // ignore
      }
    }
    fetchTags()
    return () => {
      cancelled = true
    }
  }, [])

  function handleSelectExisting(tag) {
    setTagName(tag.name)
    setTagDescription('')
    setInput('')
    setFocused(false)
    setStep('confirm')
  }

  function handleCreateNewClick() {
    setTagName(trimmedInput || input)
    setTagDescription('')
    setFocused(false)
    setStep('newTag')
  }

  function handleContinueNew(e) {
    e.preventDefault()
    if (!tagName.trim()) return
    setStep('confirm')
  }

  function handleBack() {
    setStep('pick')
    setTagName('')
    setTagDescription('')
  }

  async function handleConfirm() {
    setConfirming(true)
    try {
      const ids = [...selectedCardIds]
      await Promise.all(
        ids.map((cardId) =>
          fetch(`${API_BASE}/cards/${cardId}/tags`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              name: tagName,
              description: tagDescription,
            }),
          }).then((res) => {
            if (!res.ok) throw new Error('Failed to add tag')
          })
        )
      )
      onSuccess()
      onClose()
    } catch {
      // keep modal open for retry
    } finally {
      setConfirming(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="relative w-full max-w-md rounded-xl bg-[#2B102B] p-6 shadow-2xl ring-1 ring-purple-800/50"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3 flex size-9 items-center justify-center rounded-lg bg-purple-900/80 text-xl leading-none text-white transition hover:bg-purple-700"
          aria-label="Close"
        >
          ×
        </button>

        <h2 className="pr-10 text-xl font-bold text-white">Add tag to cards</h2>

        {step === 'pick' && (
          <div className="mt-4">
            <div className="relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                placeholder="Add a tag…"
                className="w-full rounded-lg border border-purple-800/60 bg-[#1a081a] px-3 py-2 text-sm text-white placeholder:text-purple-300/50 focus:border-purple-400 focus:outline-none focus:ring-1 focus:ring-purple-400"
              />

              {showDropdown && (
                <ul
                  className="absolute z-20 mt-1 max-h-48 w-full overflow-y-auto rounded-lg border border-purple-800/50 bg-[#1f0c1f] py-1 shadow-lg"
                  role="listbox"
                >
                  {filtered.map((tag) => (
                    <li key={tag.id} role="option">
                      <button
                        type="button"
                        className="flex w-full items-center px-3 py-2 text-left text-sm text-white hover:bg-purple-800/50"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => handleSelectExisting(tag)}
                      >
                        {tag.description?.trim() ? (
                          <span
                            className="mr-2 cursor-pointer text-sm text-purple-300"
                            onMouseDown={(e) => {
                              e.preventDefault()
                              e.stopPropagation()
                            }}
                            onClick={(e) => {
                              e.stopPropagation()
                              setOpenDescriptionTagId((id) =>
                                id === tag.id ? null : tag.id
                              )
                            }}
                          >
                            ⓘ
                          </span>
                        ) : null}
                        {tag.name}
                      </button>
                      {openDescriptionTagId === tag.id &&
                      tag.description?.trim() ? (
                        <div className="px-3 pb-2">
                          <div className="max-w-[220px] rounded bg-[#3a1540] p-2 text-sm text-white">
                            {tag.description}
                          </div>
                        </div>
                      ) : null}
                    </li>
                  ))}
                  <li role="option" className="border-t border-purple-800/40">
                    <button
                      type="button"
                      className="w-full px-3 py-2 text-left text-sm italic text-purple-300 hover:bg-purple-800/50"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={handleCreateNewClick}
                    >
                      ＋ Create new tag: {input}
                    </button>
                  </li>
                </ul>
              )}
            </div>
          </div>
        )}

        {step === 'newTag' && (
          <form onSubmit={handleContinueNew} className="mt-4">
            <p className="text-sm text-white">
              <span className="font-medium text-purple-200/90">Tag name: </span>
              {tagName}
            </p>
            <label className="mt-3 block text-sm text-purple-200/90">
              Description (optional)
              <textarea
                value={tagDescription}
                onChange={(e) => setTagDescription(e.target.value)}
                rows={3}
                className="mt-1 w-full resize-y rounded-lg border border-purple-800/60 bg-[#1a081a] px-3 py-2 text-sm text-white placeholder:text-purple-300/50 focus:border-purple-400 focus:outline-none focus:ring-1 focus:ring-purple-400"
              />
            </label>
            <div className="mt-4 flex gap-2">
              <button
                type="submit"
                className="rounded-lg border border-purple-600/60 bg-purple-800/60 px-4 py-2 text-sm font-medium text-white transition hover:bg-purple-700/80"
              >
                Continue
              </button>
              <button
                type="button"
                onClick={() => {
                  setStep('pick')
                  setTagName('')
                  setTagDescription('')
                }}
                className="rounded-lg border border-purple-600/40 px-4 py-2 text-sm font-medium text-purple-200 transition hover:bg-purple-900/40"
              >
                Back
              </button>
            </div>
          </form>
        )}

        {step === 'confirm' && (
          <div className="mt-4">
            <p className="text-white">
              Add tag <span className="font-semibold">{tagName}</span> to{' '}
              {count} card{count === 1 ? '' : 's'}?
            </p>
            <div className="mt-6 flex gap-2">
              <button
                type="button"
                onClick={handleConfirm}
                disabled={confirming}
                className="rounded-lg border border-purple-600/60 bg-purple-800/60 px-4 py-2 text-sm font-medium text-white transition hover:bg-purple-700/80 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {confirming ? 'Adding…' : 'Confirm'}
              </button>
              <button
                type="button"
                onClick={handleBack}
                disabled={confirming}
                className="rounded-lg border border-purple-600/40 px-4 py-2 text-sm font-medium text-purple-200 transition hover:bg-purple-900/40 disabled:opacity-50"
              >
                Back
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
