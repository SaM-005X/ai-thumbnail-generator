export default function Header() {
  return (
    <header style={{ textAlign: 'center', marginBottom: '2.5rem', position: 'relative' }}>
      {/* Top Status Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.75rem',
        flexWrap: 'wrap',
        marginBottom: '1.25rem',
      }}>
        <div className="status-beacon">
          <span className="status-dot" />
          <span>Cloudflare CDN · AWS Lambda Online</span>
        </div>
        <span style={{
          fontSize: '0.72rem',
          padding: '0.25rem 0.65rem',
          borderRadius: '9999px',
          background: 'rgba(255, 65, 108, 0.12)',
          border: '1px solid rgba(255, 65, 108, 0.3)',
          color: '#fda4af',
          fontWeight: 600,
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}>
          ⚡ Groq LPU + FLUX.1
        </span>
      </div>

      {/* Radiant Logo mark */}
      <div style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '58px',
        height: '58px',
        borderRadius: '18px',
        background: 'linear-gradient(135deg, #ff416c 0%, #ff4b2b 40%, #8b5cf6 100%)',
        marginBottom: '1rem',
        boxShadow: '0 10px 35px rgba(255, 65, 108, 0.45), 0 0 20px rgba(139, 92, 246, 0.35)',
        fontSize: '1.75rem',
        color: '#ffffff',
        border: '1px solid rgba(255, 255, 255, 0.25)',
      }}>
        ✦
      </div>

      {/* App title */}
      <h1 style={{
        margin: '0 0 0.5rem',
        fontSize: 'clamp(2rem, 5vw, 3rem)',
        fontWeight: 800,
        letterSpacing: '-0.03em',
        lineHeight: 1.15,
      }}>
        <span className="gradient-text">Thumbnail</span>
        <span style={{ color: '#ffffff' }}> AI</span>
        <span style={{
          fontSize: '0.85rem',
          verticalAlign: 'super',
          marginLeft: '0.4rem',
          padding: '0.2rem 0.55rem',
          borderRadius: '6px',
          background: 'rgba(255, 255, 255, 0.08)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          color: '#f8fafc',
          fontWeight: 700,
          letterSpacing: '0.05em',
        }}>
          PRO
        </span>
      </h1>

      {/* Tagline */}
      <p style={{
        margin: '0 auto',
        maxWidth: '560px',
        fontSize: '1rem',
        color: 'var(--text-secondary)',
        fontWeight: 400,
        lineHeight: 1.6,
      }}>
        Craft viral, high-CTR YouTube thumbnails in seconds. Intelligent visual prompt engineering &amp; cinematic 16:9 image synthesis.
      </p>
    </header>
  )
}
