import { useEffect, useState } from 'react'

const API_BASE = 'http://localhost:8000'

function Spinner() {
  return (
    <div
      className="mx-auto size-10 animate-spin rounded-full border-2 border-purple-400/30 border-t-purple-300"
      aria-hidden
    />
  )
}

export default function BulkRemoveTagModal({
  selectedCardIds,
  onClose,
  onSuccess,
}) {
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedTagId, setSelectedTagId] = useState(null)
  const [confirming, setConfirming] = useState(false)

  const count = selectedCardIds.size

  useEffect(() => {
    let cancelled = false

    async function fetchTags() {
      setLoading(true)
      try {
        const ids = [...selectedCardIds]
        const responses = await Promise.all(
          ids.map((id) => fetch(`${API_BASE}/cards/${id}`))
        )
        const cards = await Promise.all(
          responses.map(async (res) => {
            if (!res.ok) return null
            return res.json()
          })
        )

        if (cancelled) return

        const tagMap = new Map()
        for (const card of cards) {
          if (!card) continue
          for (const tag of card.tags ?? []) {
            tagMap.set(tag.id, tag)
          }
        }

        setTags(
          [...tagMap.values()].sort((a, b) => a.name.localeCompare(b.name))
        )
      } catch {
        if (!cancelled) setTags([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchTags()
    return () => {
      cancelled = true
    }
  }, [selectedCardIds])

  async function handleConfirm() {
    if (selectedTagId == null) return

    setConfirming(true)
    try {
      const ids = [...selectedCardIds]
      await Promise.all(
        ids.map(async (cardId) => {
          const res = await fetch(
            `${API_BASE}/cards/${cardId}/tags/${selectedTagId}`,
            { method: 'DELETE' }
          )
          if (res.status === 404) return
          if (!res.ok) throw new Error('Failed to remove tag')
        })
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
        className="relative flex max-h-[85vh] w-full max-w-md flex-col rounded-xl bg-[#2B102B] p-6 shadow-2xl ring-1 ring-purple-800/50"
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

        <h2 className="pr-10 text-xl font-bold text-white">
          Remove a tag from {count} selected card{count === 1 ? '' : 's'}
        </h2>

        {loading ? (
          <div className="flex flex-1 items-center justify-center py-12">
            <Spinner />
          </div>
        ) : tags.length === 0 ? (
          <p className="mt-4 text-sm text-purple-200/70">
            No tags found on the selected cards.
          </p>
        ) : (
          <ul className="mt-4 max-h-64 overflow-y-auto rounded-lg border border-purple-800/50">
            {tags.map((tag) => (
              <li key={tag.id}>
                <button
                  type="button"
                  onClick={() => setSelectedTagId(tag.id)}
                  className={`w-full px-4 py-3 text-left text-sm transition ${
                    selectedTagId === tag.id
                      ? 'bg-purple-700 text-white'
                      : 'text-white hover:bg-purple-800/40'
                  }`}
                >
                  {tag.name}
                </button>
              </li>
            ))}
          </ul>
        )}

        <p className="mt-3 text-xs text-purple-200/60">
          The tag will only be removed from selected cards that have it — cards
          without the tag are unaffected
        </p>

        <div className="mt-6 flex gap-2">
          <button
            type="button"
            onClick={handleConfirm}
            disabled={selectedTagId == null || confirming || loading}
            className="rounded-lg border border-purple-600/60 bg-purple-800/60 px-4 py-2 text-sm font-medium text-white transition hover:bg-purple-700/80 disabled:cursor-not-allowed disabled:border-purple-800/30 disabled:bg-purple-950/30 disabled:text-purple-400/50"
          >
            {confirming ? 'Removing…' : 'Confirm'}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={confirming}
            className="rounded-lg border border-purple-600/40 px-4 py-2 text-sm font-medium text-purple-200 transition hover:bg-purple-900/40 disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
