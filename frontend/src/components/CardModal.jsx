import { useCallback, useEffect, useMemo, useState } from 'react'

const API_BASE = 'http://localhost:8000'

function parseJsonArray(value) {
  if (!value) return []
  if (Array.isArray(value)) return value
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function formatList(value) {
  const arr = parseJsonArray(value)
  return arr.length ? arr.join(', ') : '—'
}

function parseImageUrls(imageUrl) {
  if (imageUrl == null) return []
  return imageUrl
    .split('|')
    .map((s) => s.trim())
    .filter(Boolean)
}

/** Cards API has no image_url column; derive pipe-separated URLs from card or Scryfall JSON. */
function resolveCardImageUrl(card, imageUrlFallback) {
  if (card?.image_url != null && String(card.image_url).trim()) {
    return card.image_url
  }
  if (card?.raw_scryfall_json) {
    try {
      const raw =
        typeof card.raw_scryfall_json === 'string'
          ? JSON.parse(card.raw_scryfall_json)
          : card.raw_scryfall_json
      if (raw.image_uris?.normal) {
        return raw.image_uris.normal
      }
      if (raw.card_faces?.length) {
        const urls = raw.card_faces
          .map((face) => face.image_uris?.normal)
          .filter(Boolean)
        if (urls.length) return urls.join('|')
      }
    } catch {
      // ignore malformed JSON
    }
  }
  return imageUrlFallback ?? null
}

function Spinner() {
  return (
    <div
      className="size-10 animate-spin rounded-full border-2 border-purple-400/30 border-t-purple-300"
      aria-hidden
    />
  )
}

function DetailRow({ label, children }) {
  return (
    <p className="text-sm">
      <span className="font-medium text-purple-200/90">{label}: </span>
      <span className="text-white">{children}</span>
    </p>
  )
}

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

function TagAutocomplete({ cardId, disabled, setTagBusy, onCardRefresh }) {
  const [allTags, setAllTags] = useState([])
  const [input, setInput] = useState('')
  const [focused, setFocused] = useState(false)
  const [showNewForm, setShowNewForm] = useState(false)
  const [description, setDescription] = useState('')
  const [openDescriptionTagId, setOpenDescriptionTagId] = useState(null)

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

  const filtered = useMemo(() => filterTags(allTags, input), [allTags, input])
  const showDropdown = focused && input.length >= 1 && !showNewForm
  const trimmedInput = input.trim()

  async function attachTag(name, desc) {
    setTagBusy(true)
    try {
      const res = await fetch(`${API_BASE}/cards/${cardId}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description: desc }),
      })
      if (!res.ok) throw new Error('Failed to add tag')
      setInput('')
      setDescription('')
      setShowNewForm(false)
      setFocused(false)
      await onCardRefresh()
    } catch {
      // keep state for retry
    } finally {
      setTagBusy(false)
    }
  }

  function handleSelectExisting(tag) {
    attachTag(tag.name, '')
  }

  function handleCreateNewClick() {
    setShowNewForm(true)
    setFocused(false)
  }

  function handleCancelNew() {
    setShowNewForm(false)
    setDescription('')
    setInput('')
  }

  function handleSaveNew(e) {
    e.preventDefault()
    if (!trimmedInput) return
    attachTag(trimmedInput, description.trim())
  }

  const isDisabled = disabled

  return (
    <div className="mt-4">
      <div className="relative">
        <input
          type="text"
          value={input}
          onChange={(e) => {
            setInput(e.target.value)
            if (showNewForm) setShowNewForm(false)
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Add a tag…"
          disabled={isDisabled || showNewForm}
          className="w-full rounded-lg border border-purple-800/60 bg-[#1a081a] px-3 py-2 text-sm text-white placeholder:text-purple-300/50 focus:border-purple-400 focus:outline-none focus:ring-1 focus:ring-purple-400 disabled:opacity-50"
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
                {openDescriptionTagId === tag.id && tag.description?.trim() ? (
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

      {showNewForm && (
        <form
          onSubmit={handleSaveNew}
          className="mt-3 rounded-lg border border-purple-800/50 bg-[#1a081a]/80 p-4"
        >
          <p className="text-sm text-white">
            <span className="font-medium text-purple-200/90">Tag name: </span>
            {trimmedInput || input}
          </p>
          <label className="mt-3 block text-sm text-purple-200/90">
            Description (optional)
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              disabled={isDisabled}
              className="mt-1 w-full resize-y rounded-lg border border-purple-800/60 bg-[#2B102B] px-3 py-2 text-sm text-white placeholder:text-purple-300/50 focus:border-purple-400 focus:outline-none focus:ring-1 focus:ring-purple-400 disabled:opacity-50"
            />
          </label>
          <div className="mt-3 flex gap-2">
            <button
              type="submit"
              disabled={!trimmedInput || isDisabled}
              className="rounded-lg border border-purple-600/60 bg-purple-800/60 px-4 py-2 text-sm font-medium text-white transition hover:bg-purple-700/80 disabled:cursor-not-allowed disabled:border-purple-800/30 disabled:bg-purple-950/30 disabled:text-purple-400/50"
            >
              Save Tag
            </button>
            <button
              type="button"
              onClick={handleCancelNew}
              disabled={isDisabled}
              className="rounded-lg border border-purple-600/40 px-4 py-2 text-sm font-medium text-purple-200 transition hover:bg-purple-900/40 disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

export default function CardModal({ cardId, imageUrl: imageUrlProp, onClose }) {
  const [card, setCard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [tagBusy, setTagBusy] = useState(false)
  const [currentFaceIndex, setCurrentFaceIndex] = useState(0)

  const fetchCard = useCallback(async (silent = false) => {
    if (!silent) {
      setLoading(true)
      setError(null)
    }
    try {
      const res = await fetch(`${API_BASE}/cards/${cardId}`)
      if (!res.ok) throw new Error('Failed to load card')
      const data = await res.json()
      setCard(data)
    } catch (err) {
      if (!silent) {
        setError(err.message ?? 'Failed to load card')
        setCard(null)
      }
    } finally {
      if (!silent) setLoading(false)
    }
  }, [cardId])

  useEffect(() => {
    fetchCard()
  }, [fetchCard])

  useEffect(() => {
    setCurrentFaceIndex(0)
  }, [cardId])

  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [])

  async function handleRemoveTag(tagId) {
    setTagBusy(true)
    try {
      const res = await fetch(`${API_BASE}/cards/${cardId}/tags/${tagId}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error('Failed to remove tag')
      await fetchCard(true)
    } catch {
      // keep UI state; user can retry
    } finally {
      setTagBusy(false)
    }
  }

  const keywords = parseJsonArray(card?.keywords)
  const hasPowerToughness =
    (card?.power != null && card.power !== '') ||
    (card?.toughness != null && card.toughness !== '')
  const imageUrlString = useMemo(
    () => resolveCardImageUrl(card, imageUrlProp),
    [card, imageUrlProp],
  )
  const urls = useMemo(() => parseImageUrls(imageUrlString), [imageUrlString])
  const hasImage = urls.length > 0
  const displayUrl = urls[currentFaceIndex]
  const canFlip = urls.length >= 2

  useEffect(() => {
    console.log('[CardModal] parsed urls', urls)
  }, [urls])

  function handleFlip(e) {
    e.stopPropagation()
    setCurrentFaceIndex((i) => (i + 1) % urls.length)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="card-modal-title"
    >
      <div
        className="relative flex max-h-[min(100vh-2rem,900px)] w-full max-w-4xl flex-col overflow-hidden rounded-xl bg-[#2B102B] shadow-2xl ring-1 ring-purple-800/50 md:max-h-[90vh] md:flex-row"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3 z-10 flex size-9 items-center justify-center rounded-lg bg-purple-900/80 text-xl leading-none text-white transition hover:bg-purple-700"
          aria-label="Close"
        >
          ×
        </button>

        {loading ? (
          <div className="flex min-h-[280px] w-full items-center justify-center py-16">
            <Spinner />
          </div>
        ) : error ? (
          <div className="flex min-h-[200px] w-full items-center justify-center p-8 text-center text-red-300">
            {error}
          </div>
        ) : (
          <>
            <div className="flex shrink-0 items-start justify-center bg-[#1a081a]/50 p-4 pt-12 md:w-[42%] md:p-6 md:pt-6">
              <div className="relative inline-block w-full max-w-xs">
                {hasImage ? (
                  <>
                    <img
                      src={displayUrl}
                      alt={card.name}
                      className="max-h-[50vh] w-full rounded-lg object-contain shadow-lg md:max-h-full"
                    />
                    {canFlip && (
                      <button
                        type="button"
                        onClick={handleFlip}
                        onMouseDown={(e) => e.stopPropagation()}
                        className="absolute bottom-2 left-2 z-10 flex size-7 items-center justify-center rounded-full bg-black/60 text-sm text-white opacity-70 transition-opacity hover:opacity-100"
                        aria-label="Flip card face"
                      >
                        ↺
                      </button>
                    )}
                  </>
                ) : (
                  <div className="flex aspect-[5/7] w-full items-center justify-center rounded-lg bg-[#1a081a] p-4">
                    <span className="text-center text-purple-200/70">{card.name}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto p-4 pt-2 md:p-6 md:pt-6">
              <h2
                id="card-modal-title"
                className="pr-10 text-2xl font-bold text-white"
              >
                {card.name}
              </h2>

              <div className="mt-4 space-y-2">
                <DetailRow label="Mana cost">{card.mana_cost || '—'}</DetailRow>
                <DetailRow label="Type">{card.type_line || '—'}</DetailRow>

                {card.oracle_text ? (
                  <div className="text-sm">
                    <span className="font-medium text-purple-200/90">
                      Oracle text:{' '}
                    </span>
                    <p className="mt-1 whitespace-pre-wrap text-white">
                      {card.oracle_text}
                    </p>
                  </div>
                ) : (
                  <DetailRow label="Oracle text">—</DetailRow>
                )}

                {hasPowerToughness && (
                  <DetailRow label="Power / Toughness">
                    {card.power ?? '—'} / {card.toughness ?? '—'}
                  </DetailRow>
                )}

                <DetailRow label="CMC">{card.cmc ?? '—'}</DetailRow>
                <DetailRow label="Colours">
                  {formatList(card.colours)}
                </DetailRow>
                <DetailRow label="Colour identity">
                  {formatList(card.colour_identity)}
                </DetailRow>

                {keywords.length > 0 && (
                  <DetailRow label="Keywords">{keywords.join(', ')}</DetailRow>
                )}
              </div>

              <section className="mt-8 border-t border-purple-800/40 pt-6">
                <h3 className="text-lg font-semibold text-white">Tags</h3>

                <div className="mt-3 flex flex-wrap gap-2">
                  {(card.tags ?? []).length === 0 ? (
                    <p className="text-sm text-purple-200/60">No tags yet</p>
                  ) : (
                    card.tags.map((tag) => (
                      <span
                        key={tag.id}
                        className="inline-flex items-center gap-1 rounded-full bg-purple-700 px-3 py-1 text-sm text-white"
                      >
                        {tag.name}
                        <button
                          type="button"
                          onClick={() => handleRemoveTag(tag.id)}
                          disabled={tagBusy}
                          className="ml-0.5 rounded-full px-1 text-purple-200 transition hover:bg-purple-600 hover:text-white disabled:opacity-50"
                          aria-label={`Remove tag ${tag.name}`}
                        >
                          ×
                        </button>
                      </span>
                    ))
                  )}
                </div>

                <TagAutocomplete
                  cardId={cardId}
                  disabled={tagBusy}
                  setTagBusy={setTagBusy}
                  onCardRefresh={() => fetchCard(true)}
                />
              </section>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
