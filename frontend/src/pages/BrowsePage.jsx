import { useEffect, useState } from 'react'
import BulkAddTagModal from '../components/BulkAddTagModal.jsx'
import BulkRemoveTagModal from '../components/BulkRemoveTagModal.jsx'
import CardModal from '../components/CardModal.jsx'
import CardTile from '../components/CardTile.jsx'

const API_BASE = 'http://localhost:8000'
const PAGE_SIZE = 60

export default function BrowsePage() {
  const [searchInput, setSearchInput] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [includeArena, setIncludeArena] = useState(false)
  const [includePlanes, setIncludePlanes] = useState(false)
  const [includeTokens, setIncludeTokens] = useState(false)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [warnings, setWarnings] = useState([])
  const [cards, setCards] = useState([])
  const [selectedCardId, setSelectedCardId] = useState(null)
  const [selectedImageUrl, setSelectedImageUrl] = useState(null)
  const [isSelectMode, setIsSelectMode] = useState(false)
  const [selectedCardIds, setSelectedCardIds] = useState(() => new Set())
  const [bulkModal, setBulkModal] = useState(null)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchInput)
      setPage(0)
    }, 400)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    let cancelled = false

    async function fetchCards() {
      setLoading(true)
      try {
        const params = new URLSearchParams({
          q: debouncedQuery,
          include_arena: String(includeArena),
          include_planes: String(includePlanes),
          include_tokens: String(includeTokens),
          page: String(page),
          page_size: String(PAGE_SIZE),
        })
        const res = await fetch(`${API_BASE}/cards/search?${params}`)
        if (!res.ok) throw new Error('Search failed')
        const data = await res.json()
        if (!cancelled) {
          setTotal(data.total ?? 0)
          setWarnings(data.warnings ?? [])
          setCards(data.cards ?? [])
        }
      } catch {
        if (!cancelled) {
          setTotal(0)
          setWarnings([])
          setCards([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchCards()
    return () => {
      cancelled = true
    }
  }, [debouncedQuery, includeArena, includePlanes, includeTokens, page])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const isLastPage = page >= totalPages - 1
  const selectedCount = selectedCardIds.size

  function goToPage(nextPage) {
    setPage(nextPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function handleFilterChange(setter) {
    return (e) => {
      setter(e.target.checked)
      setPage(0)
    }
  }

  function enterSelectMode() {
    setSelectedCardId(null)
    setSelectedImageUrl(null)
    setIsSelectMode(true)
  }

  function exitSelectMode() {
    setIsSelectMode(false)
    setSelectedCardIds(new Set())
    setBulkModal(null)
  }

  function toggleCardSelection(cardId) {
    setSelectedCardIds((prev) => {
      const next = new Set(prev)
      if (next.has(cardId)) next.delete(cardId)
      else next.add(cardId)
      return next
    })
  }

  function selectAllOnPage() {
    setSelectedCardIds(new Set(cards.map((c) => c.id)))
  }

  function deselectAll() {
    setSelectedCardIds(new Set())
  }

  return (
    <div
      className={`min-h-screen bg-[#2B102B] text-white ${isSelectMode ? 'pb-24' : ''}`}
    >
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex gap-3">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search cards… (e.g. t:creature c:rg mv<=3)"
            className="min-w-0 flex-1 rounded-lg border border-purple-800/60 bg-[#1a081a] px-4 py-3 text-white placeholder:text-purple-300/50 focus:border-purple-400 focus:outline-none focus:ring-1 focus:ring-purple-400"
          />
          {!isSelectMode && (
            <button
              type="button"
              onClick={enterSelectMode}
              className="shrink-0 rounded-lg border border-purple-600/60 bg-purple-900/40 px-4 py-3 text-sm font-medium whitespace-nowrap transition hover:bg-purple-800/60"
            >
              Select Multiple
            </button>
          )}
        </div>

        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={includeArena}
              onChange={handleFilterChange(setIncludeArena)}
              className="size-4 rounded border-purple-600 bg-[#1a081a] text-purple-500 focus:ring-purple-400"
            />
            Include Arena cards
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={includePlanes}
              onChange={handleFilterChange(setIncludePlanes)}
              className="size-4 rounded border-purple-600 bg-[#1a081a] text-purple-500 focus:ring-purple-400"
            />
            Include Plane cards
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={includeTokens}
              onChange={handleFilterChange(setIncludeTokens)}
              className="size-4 rounded border-purple-600 bg-[#1a081a] text-purple-500 focus:ring-purple-400"
            />
            Include Tokens
          </label>
        </div>

        {loading ? (
          <p className="mt-8 text-center text-purple-200/80">Loading…</p>
        ) : (
          <>
            <p className="mt-6 text-sm text-purple-200/90">
              {total.toLocaleString()} results
            </p>

            {warnings.length > 0 && (
              <div className="mt-3 space-y-2">
                {warnings.map((warning, i) => (
                  <p
                    key={i}
                    className="rounded-lg border border-yellow-600/40 bg-yellow-500/15 px-4 py-2 text-sm text-yellow-100"
                  >
                    {warning}
                  </p>
                ))}
              </div>
            )}

            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3 md:gap-4 lg:grid-cols-6 lg:gap-4">
              {cards.map((card) => (
                <CardTile
                  key={card.id}
                  card={card}
                  isSelectMode={isSelectMode}
                  isSelected={selectedCardIds.has(card.id)}
                  onSelect={() => toggleCardSelection(card.id)}
                  onClick={(imageUrl) => {
                    setSelectedCardId(card.id)
                    setSelectedImageUrl(imageUrl ?? null)
                  }}
                />
              ))}
            </div>

            <div className="mt-8 flex items-center justify-center gap-4">
              <button
                type="button"
                onClick={() => goToPage(page - 1)}
                disabled={page === 0}
                className="rounded-lg border border-purple-600/60 bg-purple-900/40 px-4 py-2 text-sm font-medium transition hover:bg-purple-800/60 disabled:cursor-not-allowed disabled:border-purple-800/30 disabled:bg-purple-950/30 disabled:text-purple-400/50"
              >
                Previous
              </button>
              <span className="text-sm text-purple-200/90">
                Page {page + 1} of {totalPages}
              </span>
              <button
                type="button"
                onClick={() => goToPage(page + 1)}
                disabled={isLastPage}
                className="rounded-lg border border-purple-600/60 bg-purple-900/40 px-4 py-2 text-sm font-medium transition hover:bg-purple-800/60 disabled:cursor-not-allowed disabled:border-purple-800/30 disabled:bg-purple-950/30 disabled:text-purple-400/50"
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>

      {isSelectMode && (
        <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-purple-700/50 bg-[#3a1540] shadow-[0_-4px_24px_rgba(0,0,0,0.4)]">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-3 px-4 py-3 sm:gap-4">
            <span className="rounded-full bg-purple-800/80 px-3 py-1 text-sm font-medium text-white">
              {selectedCount} card{selectedCount === 1 ? '' : 's'} selected
            </span>
            <button
              type="button"
              onClick={selectAllOnPage}
              className="rounded-lg border border-purple-600/60 bg-purple-900/40 px-4 py-2 text-sm font-medium transition hover:bg-purple-800/60"
            >
              Select All
            </button>
            <button
              type="button"
              onClick={deselectAll}
              className="rounded-lg border border-purple-600/60 bg-purple-900/40 px-4 py-2 text-sm font-medium transition hover:bg-purple-800/60"
            >
              Deselect All
            </button>
            <button
              type="button"
              onClick={() => setBulkModal('add')}
              className="rounded-lg border border-purple-600/60 bg-purple-800/60 px-4 py-2 text-sm font-medium transition hover:bg-purple-700/80"
            >
              Add Tag
            </button>
            <button
              type="button"
              onClick={() => setBulkModal('remove')}
              disabled={selectedCount === 0}
              className="rounded-lg border border-purple-600/60 bg-purple-900/40 px-4 py-2 text-sm font-medium transition hover:bg-purple-800/60 disabled:cursor-not-allowed disabled:border-purple-800/30 disabled:bg-purple-950/30 disabled:text-purple-400/50"
            >
              Remove Tag
            </button>
            <button
              type="button"
              onClick={exitSelectMode}
              className="flex size-9 items-center justify-center rounded-lg border border-purple-600/40 text-lg leading-none transition hover:bg-purple-900/40"
              aria-label="Exit selection mode"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {bulkModal === 'add' && (
        <BulkAddTagModal
          selectedCardIds={selectedCardIds}
          onClose={() => setBulkModal(null)}
          onSuccess={() => {}}
        />
      )}

      {bulkModal === 'remove' && (
        <BulkRemoveTagModal
          selectedCardIds={selectedCardIds}
          onClose={() => setBulkModal(null)}
          onSuccess={() => {}}
        />
      )}

      {selectedCardId != null && !isSelectMode && (
        <CardModal
          cardId={selectedCardId}
          imageUrl={selectedImageUrl}
          onClose={() => {
            setSelectedCardId(null)
            setSelectedImageUrl(null)
          }}
        />
      )}
    </div>
  )
}

