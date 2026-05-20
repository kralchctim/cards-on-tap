import { useEffect, useState } from 'react'

function parseImageUrls(imageUrl) {
  if (imageUrl == null) return []
  return imageUrl
    .split('|')
    .map((s) => s.trim())
    .filter(Boolean)
}

export default function CardTile({
  card,
  isSelectMode,
  isSelected,
  onSelect,
  onClick,
}) {
  const urls = parseImageUrls(card.image_url)
  const hasImage = urls.length > 0
  const [currentFaceIndex, setCurrentFaceIndex] = useState(0)

  useEffect(() => {
    setCurrentFaceIndex(0)
  }, [card.id])

  const displayUrl = urls[currentFaceIndex]
  const canFlip = urls.length >= 2

  function handleClick() {
    if (isSelectMode) onSelect()
    else if (hasImage) onClick(displayUrl)
  }

  function handleFlip(e) {
    e.stopPropagation()
    setCurrentFaceIndex((i) => (i + 1) % urls.length)
  }

  const content = hasImage ? (
    <img
      src={displayUrl}
      alt=""
      className={`w-full rounded-lg shadow-md transition-transform duration-200 ${
        isSelectMode ? '' : 'hover:scale-105'
      }`}
    />
  ) : (
    <div
      className={`flex aspect-[5/7] w-full items-center justify-center rounded-lg bg-[#1a081a] p-2 shadow-md transition-transform duration-200 ${
        isSelectMode ? '' : 'hover:scale-105'
      }`}
    >
      <span className="text-center text-xs text-purple-200/70">{card.name}</span>
    </div>
  )

  return (
    <div
      className={`relative ${isSelectMode ? 'cursor-pointer' : hasImage ? 'cursor-pointer' : ''}`}
      onClick={isSelectMode || !hasImage ? handleClick : undefined}
      role={isSelectMode ? 'button' : undefined}
      tabIndex={isSelectMode ? 0 : undefined}
      onKeyDown={
        isSelectMode
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onSelect()
              }
            }
          : undefined
      }
    >
      {isSelectMode ? (
        <div onClick={handleClick}>{content}</div>
      ) : hasImage ? (
        <div onClick={() => onClick(displayUrl)}>{content}</div>
      ) : (
        content
      )}

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

      {isSelectMode && (
        <label
          className="absolute top-2 right-2 z-10"
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onSelect}
            className="size-5 rounded border-purple-400 bg-[#1a081a] text-purple-500 focus:ring-purple-400 focus:ring-offset-0"
          />
        </label>
      )}
    </div>
  )
}
