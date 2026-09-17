/**
 * GenerateButton
 *
 * Full-width gradient CTA button with an animated spinner during loading.
 * Disabled when prompt is empty or a request is in flight.
 *
 * Props:
 *   onClick   {function} — called when user clicks and button is enabled
 *   loading   {boolean}  — true while awaiting the API response
 *   disabled  {boolean}  — true when prompt is empty
 *   mode      {string}   — "generate" | "edit" (affects label text)
 */
export default function GenerateButton({ onClick, loading, disabled, mode }) {
  const label = mode === 'edit' ? 'Edit Thumbnail' : 'Generate Thumbnail'
  const isDisabled = disabled || loading

  return (
    <button
      id="generate-btn"
      className="btn-gradient"
      onClick={onClick}
      disabled={isDisabled}
      aria-busy={loading}
      style={{
        width: '100%',
        padding: '0.85rem 1.5rem',
        borderRadius: '0.6rem',
        fontSize: '0.95rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.6rem',
        letterSpacing: '0.01em',
      }}
    >
      {loading ? (
        <>
          <span className="spinner" aria-hidden="true" />
          Generating…
        </>
      ) : (
        <>
          <span aria-hidden="true">✦</span>
          {label}
        </>
      )}
    </button>
  )
}
