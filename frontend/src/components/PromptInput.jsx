/**
 * PromptInput.jsx
 *
 * Controlled textarea for the user's image generation/edit prompt.
 * Features:
 *   - Category inspiration pills for fast YouTube thumbnail creation
 *   - Art style modifier chips that append style keywords
 *   - Live character counter and guardrail error alert
 *
 * Props:
 *   value     {string}   — current prompt text
 *   onChange  {function} — called with new string value on every keystroke
 *   error     {string}   — guardrail rejection message (or null)
 *   mode      {string}   — "generate" | "edit"
 */

const MAX_CHARS = 500

const PLACEHOLDERS = {
  generate: 'e.g. "A dramatic gaming thumbnail with fiery glowing sword, neon blue lightning bolts, and shocked reaction face…"',
  edit:     'e.g. "Make the background deep purple with glowing neon edges and add bold high-contrast rim lighting"',
}

const CATEGORIES = [
  {
    id: 'gaming',
    label: '🎮 Gaming',
    className: 'chip-gaming',
    prompt: 'Epic gaming battle thumbnail, fiery glowing dragon sword, neon blue lightning crackles, intense cinematic rim lighting, 16:9 composition',
  },
  {
    id: 'tech',
    label: '⚡ Tech & AI',
    className: 'chip-tech',
    prompt: 'Futuristic AI smartphone with glowing holographic circuits, sleek obsidian studio table, laser grid background, sharp 8k focus',
  },
  {
    id: 'podcast',
    label: '🎙️ Podcast',
    className: 'chip-podcast',
    prompt: 'Dramatic split-screen studio podcast interview, warm golden tungsten spotlight vs deep teal backlight, expressive conversation, high CTR',
  },
  {
    id: 'cinema',
    label: '🎬 Cinematic',
    className: 'chip-cinema',
    prompt: 'Breathtaking cinematic movie scene, rain-slicked Tokyo cyberpunk street at midnight, intense neon reflections, atmospheric volumetric haze',
  },
  {
    id: 'finance',
    label: '💰 Finance',
    className: 'chip-finance',
    prompt: 'Massive glowing green candlestick chart blasting toward outer space, golden coin explosion, dramatic upward lighting, bold hype aesthetic',
  },
]

const STYLE_TAGS = [
  'Cinematic 3D render',
  'Cyberpunk Neon glow',
  'Photorealistic 8K studio',
  'Vector Pop-art graphic',
  'Anime high-octane',
]

export default function PromptInput({ value, onChange, error, mode }) {
  const remaining = MAX_CHARS - value.length
  const isNearLimit = remaining <= 60
  const isAtLimit   = remaining <= 0

  const handleCategoryClick = (categoryPrompt) => {
    onChange(categoryPrompt)
  }

  const handleStyleClick = (styleText) => {
    if (!value.trim()) {
      onChange(styleText)
      return
    }
    // Append style if not already present
    if (!value.toLowerCase().includes(styleText.toLowerCase())) {
      const separator = value.trim().endsWith(',') ? ' ' : ', '
      onChange(value.trim() + separator + styleText)
    }
  }

  return (
    <div style={{ marginBottom: '1.25rem' }}>
      {/* Label and Mode Context */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '0.6rem',
      }}>
        <label
          htmlFor="prompt-textarea"
          style={{
            display: 'block',
            fontSize: '0.85rem',
            fontWeight: 700,
            color: 'var(--text-primary)',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}
        >
          {mode === 'edit' ? '✎ Modification Prompt' : '✦ Visual Scene Prompt'}
        </label>

        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          16:9 Landscape Target
        </span>
      </div>

      {/* Category Inspiration Chips (Generate mode) */}
      {mode === 'generate' && (
        <div style={{
          display: 'flex',
          gap: '0.45rem',
          flexWrap: 'wrap',
          marginBottom: '0.75rem',
        }}>
          <span style={{
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
            alignSelf: 'center',
            marginRight: '0.2rem',
            fontWeight: 600,
          }}>
            Ideas:
          </span>
          {CATEGORIES.map(cat => (
            <button
              key={cat.id}
              type="button"
              className={`preset-chip ${cat.className}`}
              onClick={() => handleCategoryClick(cat.prompt)}
              title="Click to use this prompt template"
            >
              {cat.label}
            </button>
          ))}
        </div>
      )}

      {/* Textarea */}
      <textarea
        id="prompt-textarea"
        className={`prompt-textarea${error ? ' error' : ''}`}
        rows={4}
        maxLength={MAX_CHARS}
        placeholder={PLACEHOLDERS[mode]}
        value={value}
        onChange={e => onChange(e.target.value)}
        aria-describedby={error ? 'prompt-error' : undefined}
        aria-invalid={!!error}
      />

      {/* Quick Art Style Tags */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.4rem',
        flexWrap: 'wrap',
        marginTop: '0.6rem',
      }}>
        <span style={{
          fontSize: '0.72rem',
          color: 'var(--text-muted)',
          fontWeight: 600,
        }}>
          Add Style:
        </span>
        {STYLE_TAGS.map(style => (
          <button
            key={style}
            type="button"
            className="style-tag"
            onClick={() => handleStyleClick(style)}
            title={`Append "${style}" to your prompt`}
          >
            + {style}
          </button>
        ))}
      </div>

      {/* Footer row: error or hint + char count */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginTop: '0.6rem',
        gap: '1rem',
      }}>
        {/* Guardrail error or helper */}
        {error ? (
          <p
            id="prompt-error"
            role="alert"
            style={{
              margin: 0,
              fontSize: '0.84rem',
              color: 'var(--error)',
              fontWeight: 500,
              lineHeight: 1.5,
              flex: 1,
            }}
          >
            ⚠ {error}
          </p>
        ) : (
          <p style={{
            margin: 0,
            fontSize: '0.82rem',
            color: 'var(--text-muted)',
            flex: 1,
          }}>
            Specify key subject, bold foreground action, and lighting contrast for maximum click-through rate.
          </p>
        )}

        {/* Char counter */}
        <span style={{
          fontSize: '0.78rem',
          fontFamily: "'JetBrains Mono', monospace",
          color: isAtLimit ? 'var(--error)' : isNearLimit ? 'var(--accent-amber)' : 'var(--text-muted)',
          whiteSpace: 'nowrap',
          flexShrink: 0,
          fontWeight: 600,
        }}>
          {value.length}/{MAX_CHARS}
        </span>
      </div>
    </div>
  )
}
