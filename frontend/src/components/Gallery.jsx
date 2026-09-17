/**
 * Gallery.jsx
 *
 * Displays the user's generation history fetched from GET /api/history.
 * Features:
 *   - Responsive grid of past thumbnails with prompts and timestamps
 *   - Individual delete button on each thumbnail card
 *   - Bulk "Clear All" button in header
 *   - Full-screen modal lightbox inspector with delete option
 */

import { useState, useEffect, useCallback } from 'react'
import { API_BASE_URL } from '../config'

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function truncate(str, max = 85) {
  if (!str) return ''
  return str.length > max ? str.slice(0, max).trimEnd() + '…' : str
}

// ─── Lightbox Modal ──────────────────────────────────────────────────────────

function Lightbox({ item, onClose, onDelete }) {
  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const src = item.image_b64
    ? `data:${item.mime_type || 'image/jpeg'};base64,${item.image_b64}`
    : item.url

  return (
    <div
      className="lightbox-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Thumbnail preview"
    >
      <div className="lightbox-content" onClick={e => e.stopPropagation()}>
        <button className="lightbox-close" onClick={onClose} aria-label="Close preview">✕</button>
        <img src={src} alt={item.prompt} className="lightbox-image" />
        <div className="lightbox-meta">
          <p className="lightbox-prompt">"{item.prompt}"</p>
          <div className="lightbox-tags">
            <span className={item.mode === 'edit' ? 'gallery-badge gallery-badge-edit' : 'gallery-badge'}>
              {item.mode === 'edit' ? '✎ Edit' : '✦ Generated'}
            </span>
            <span className="gallery-badge gallery-badge--dim">{formatDate(item.created_at)}</span>
            
            <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    fontSize: '0.78rem',
                    color: 'var(--accent-pink)',
                    textDecoration: 'none',
                    fontWeight: 600,
                  }}
                >
                  ↗ Open S3
                </a>
              )}
              <button
                type="button"
                onClick={() => {
                  if (window.confirm('Are you sure you want to delete this thumbnail?')) {
                    onDelete(item.id)
                    onClose()
                  }
                }}
                style={{
                  background: 'rgba(244, 63, 94, 0.15)',
                  border: '1px solid rgba(244, 63, 94, 0.35)',
                  color: '#fda4af',
                  borderRadius: '6px',
                  padding: '0.25rem 0.65rem',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.3rem',
                }}
              >
                🗑️ Delete
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Gallery Card ────────────────────────────────────────────────────────────

function GalleryCard({ item, onClick, onDelete }) {
  const src = item.image_b64
    ? `data:${item.mime_type || 'image/jpeg'};base64,${item.image_b64}`
    : item.url

  return (
    <div
      className="gallery-card"
      onClick={() => onClick(item)}
      role="button"
      tabIndex={0}
      onKeyDown={e => { if (e.key === 'Enter') onClick(item) }}
      aria-label={`View thumbnail: ${item.prompt}`}
    >
      {/* Individual Delete Button */}
      <button
        type="button"
        className="gallery-card__delete"
        onClick={(e) => {
          e.stopPropagation()
          if (window.confirm('Delete this thumbnail?')) {
            onDelete(item.id)
          }
        }}
        title="Delete thumbnail"
        aria-label="Delete thumbnail"
      >
        ✕
      </button>

      <div className="gallery-card__thumb canvas-16-9">
        <img src={src} alt={item.prompt} loading="lazy" />
      </div>
      <div className="gallery-card__body">
        <p className="gallery-card__prompt">{truncate(item.prompt)}</p>
        <div className="gallery-card__footer">
          <span className={item.mode === 'edit' ? 'gallery-badge gallery-badge-edit' : 'gallery-badge'}>
            {item.mode === 'edit' ? '✎ Edit' : '✦ Generate'}
          </span>
          <span className="gallery-card__date">{formatDate(item.created_at)}</span>
        </div>
      </div>
    </div>
  )
}

// ─── Empty State ─────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="gallery-empty">
      <div className="gallery-empty__icon">🖼️</div>
      <p className="gallery-empty__title">No thumbnails saved yet</p>
      <p className="gallery-empty__sub">Generate your first 16:9 thumbnail and it will appear here.</p>
    </div>
  )
}

// ─── Main Gallery Component ──────────────────────────────────────────────────

export default function Gallery({ newItem }) {
  const [items,    setItems]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [clearing, setClearing] = useState(false)
  const [error,    setError]    = useState(null)
  const [active,   setActive]   = useState(null)

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res  = await fetch(`${API_BASE_URL}/api/history?limit=50`)
      const json = await res.json()
      if (!res.ok) throw new Error(json?.detail ?? 'Failed to load history')
      setItems(json.data ?? [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // Delete a single item
  const handleDeleteItem = async (itemId) => {
    try {
      // Optimistic removal from UI
      setItems(prev => prev.filter(i => i.id !== itemId))
      const res = await fetch(`${API_BASE_URL}/api/history/${itemId}`, {
        method: 'DELETE',
      })
      if (!res.ok) {
        if (res.status === 404) return // Record already deleted or unsaved client temporary ID
        const json = await res.json().catch(() => ({}))
        throw new Error(json?.detail ?? 'Failed to delete item')
      }
    } catch (err) {
      console.error('Delete thumbnail error:', err)
      setError(err.message)
      // Refetch on failure
      fetchHistory()
    }
  }

  // Clear all items
  const handleClearAll = async () => {
    if (!window.confirm('Are you sure you want to delete ALL thumbnails from your gallery? This cannot be undone.')) {
      return
    }

    setClearing(true)
    setError(null)
    try {
      // Optimistic clear
      setItems([])
      const res = await fetch(`${API_BASE_URL}/api/history`, {
        method: 'DELETE',
      })
      if (!res.ok) {
        const json = await res.json().catch(() => ({}))
        throw new Error(json?.detail ?? 'Failed to clear gallery')
      }
    } catch (err) {
      console.error('Clear gallery error:', err)
      setError(err.message)
      fetchHistory()
    } finally {
      setClearing(false)
    }
  }

  // Fetch on mount
  useEffect(() => { fetchHistory() }, [fetchHistory])

  // Prepend newly generated item
  useEffect(() => {
    if (!newItem) return
    setItems(prev => [newItem, ...prev])
  }, [newItem])

  return (
    <section className="gallery-section fade-in-up" aria-label="Generation history">
      {/* ── Header ── */}
      <div className="gallery-header">
        <div>
          <h2 className="gallery-title gradient-text">Creator Gallery</h2>
          <p className="gallery-sub">Past creations stored in Supabase &amp; AWS S3</p>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
          {items.length > 0 && (
            <button
              type="button"
              className="gallery-clear-btn"
              onClick={handleClearAll}
              disabled={clearing || loading}
              title="Delete all thumbnails from gallery"
            >
              🗑️ Clear All
            </button>
          )}

          <button
            type="button"
            className="gallery-refresh-btn"
            onClick={fetchHistory}
            disabled={loading || clearing}
            aria-label="Refresh gallery"
          >
            <span className={loading ? 'refresh-icon spinning' : 'refresh-icon'}>↻</span>
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* ── Error ── */}
      {error && (
        <p role="alert" style={{ color: 'var(--error)', textAlign: 'center', marginBottom: '1rem' }}>
          ⚠ {error}
        </p>
      )}

      {/* ── Grid ── */}
      {!loading && !error && items.length === 0 && <EmptyState />}

      {items.length > 0 && (
        <div className="gallery-grid">
          {items.map(item => (
            <GalleryCard
              key={item.id}
              item={item}
              onClick={setActive}
              onDelete={handleDeleteItem}
            />
          ))}
        </div>
      )}

      {/* ── Lightbox ── */}
      {active && (
        <Lightbox
          item={active}
          onClose={() => setActive(null)}
          onDelete={handleDeleteItem}
        />
      )}
    </section>
  )
}
