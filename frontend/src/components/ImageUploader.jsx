import { useCallback, useState } from 'react'

/**
 * ImageUploader
 *
 * Drag-and-drop zone with click-to-browse fallback.
 * Shows an inline preview of the selected image.
 * Only rendered in "edit" mode.
 *
 * Props:
 *   file     {File|null} — currently selected File object
 *   onChange {function}  — called with the new File when user selects one
 */
export default function ImageUploader({ file, onChange }) {
  const [isDragging, setIsDragging] = useState(false)

  const handleDrop = useCallback(e => {
    e.preventDefault()
    setIsDragging(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped && dropped.type.startsWith('image/')) {
      onChange(dropped)
    }
  }, [onChange])

  const handleDragOver = e => { e.preventDefault(); setIsDragging(true) }
  const handleDragLeave = () => setIsDragging(false)

  const handleFileInput = e => {
    const selected = e.target.files?.[0]
    if (selected) onChange(selected)
  }

  const previewUrl = file ? URL.createObjectURL(file) : null

  return (
    <div style={{ marginBottom: '1rem' }}>
      {/* Label */}
      <label
        style={{
          display: 'block',
          fontSize: '0.82rem',
          fontWeight: 600,
          color: 'var(--text-secondary)',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          marginBottom: '0.5rem',
        }}
      >
        Reference Image
      </label>

      {/* Drop zone */}
      <div
        id="image-drop-zone"
        className={`drop-zone${isDragging ? ' active' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => document.getElementById('file-input').click()}
        role="button"
        tabIndex={0}
        aria-label="Upload reference image — click or drag and drop"
        onKeyDown={e => e.key === 'Enter' && document.getElementById('file-input').click()}
        style={{
          padding: file ? '0.5rem' : '2rem 1rem',
          minHeight: file ? 'auto' : '120px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem',
          userSelect: 'none',
        }}
      >
        {file && previewUrl ? (
          /* Preview */
          <div style={{ width: '100%', position: 'relative' }}>
            <div className="canvas-16-9" style={{ borderRadius: '0.5rem', overflow: 'hidden' }}>
              <img
                src={previewUrl}
                alt="Reference image preview"
                style={{ objectFit: 'cover', width: '100%', height: '100%', display: 'block' }}
              />
            </div>
            <p style={{
              margin: '0.5rem 0 0',
              fontSize: '0.8rem',
              color: 'var(--text-secondary)',
              textAlign: 'center',
            }}>
              {file.name} · {(file.size / 1024).toFixed(0)} KB — click to change
            </p>
          </div>
        ) : (
          /* Empty state */
          <>
            <div style={{ fontSize: '2rem', opacity: 0.5 }}>⬆</div>
            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem', textAlign: 'center' }}>
              <strong style={{ color: 'var(--text-primary)' }}>Drop an image here</strong>
              <br />
              or click to browse &nbsp;·&nbsp; JPG, PNG, WEBP
            </p>
          </>
        )}
      </div>

      {/* Hidden file input */}
      <input
        id="file-input"
        type="file"
        accept="image/png,image/jpeg,image/webp"
        style={{ display: 'none' }}
        onChange={handleFileInput}
        aria-hidden="true"
      />
    </div>
  )
}
