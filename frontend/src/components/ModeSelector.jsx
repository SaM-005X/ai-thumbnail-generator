/**
 * ModeSelector
 *
 * Pill-style toggle that switches between "generate" (text-to-image)
 * and "edit" (image-to-image) modes.
 *
 * Props:
 *   mode     {string}   — current mode: "generate" | "edit"
 *   onChange {function} — called with the new mode string on click
 */
export default function ModeSelector({ mode, onChange }) {
  return (
    <div style={{
      display: 'flex',
      gap: '0.5rem',
      background: 'rgba(255,255,255,0.04)',
      border: '1px solid var(--border)',
      borderRadius: '9999px',
      padding: '4px',
      width: 'fit-content',
      margin: '0 auto 1.75rem',
    }}>
      <button
        id="mode-generate"
        className={`mode-pill${mode === 'generate' ? ' active' : ''}`}
        onClick={() => onChange('generate')}
        aria-pressed={mode === 'generate'}
      >
        ✦ Generate
      </button>
      <button
        id="mode-edit"
        className={`mode-pill${mode === 'edit' ? ' active' : ''}`}
        onClick={() => onChange('edit')}
        aria-pressed={mode === 'edit'}
      >
        ✎ Edit Image
      </button>
    </div>
  )
}
