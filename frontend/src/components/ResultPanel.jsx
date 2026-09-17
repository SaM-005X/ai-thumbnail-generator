/**
 * ResultPanel.jsx
 *
 * Displays the generated/edited thumbnail in a strict 16:9 frame.
 * Features:
 *   - 1280x720 HD badge & S3 storage status
 *   - Quick-action buttons: Download PNG, Open S3 Link, Copy Link
 *   - Animated multi-stage loading indicator
 *   - Polished empty canvas with 16:9 grid overlay
 *
 * Props:
 *   imageBase64 {string|null} — base64 PNG data (without data URI prefix)
 *   mimeType    {string}      — image MIME type (default: "image/png")
 *   url         {string|null} — S3 presigned URL
 *   loading     {boolean}     — true while generation is in progress
 */

import { useState } from 'react'

export default function ResultPanel({ imageBase64, mimeType = 'image/png', url = null, loading }) {
  const [copied, setCopied] = useState(false)
  const dataUri = imageBase64 ? `data:${mimeType};base64,${imageBase64}` : null

  const handleDownload = () => {
    const downloadSource = dataUri || url
    if (!downloadSource) return
    const a = document.createElement('a')
    a.href = downloadSource
    a.download = `youtube_thumbnail_${Date.now()}.png`
    if (url && !dataUri) {
      a.target = '_blank'
    }
    a.click()
  }

  const handleCopyLink = () => {
    if (!url) return
    navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  return (
    <div style={{ marginTop: '2.5rem' }}>
      {/* Header bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem',
        marginBottom: '0.85rem',
      }}>
        {/* Left Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{
            fontSize: '0.82rem',
            fontWeight: 700,
            color: 'var(--text-primary)',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}>
            Render Canvas
          </span>

          <span style={{
            fontSize: '0.72rem',
            fontWeight: 600,
            background: 'rgba(255, 255, 255, 0.06)',
            border: '1px solid var(--border)',
            color: 'var(--text-secondary)',
            padding: '0.2rem 0.55rem',
            borderRadius: '9999px',
          }}>
            1280 × 720 · 16:9
          </span>

          {url && (
            <span style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              background: 'rgba(16, 185, 129, 0.14)',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              color: '#34d399',
              padding: '0.2rem 0.55rem',
              borderRadius: '9999px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}>
              ☁️ AWS S3 Presigned
            </span>
          )}
        </div>

        {/* Right Actions */}
        {(imageBase64 || url) && (
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            {url && (
              <>
                <button
                  type="button"
                  onClick={handleCopyLink}
                  style={{
                    background: 'rgba(255, 255, 255, 0.06)',
                    border: '1px solid var(--border)',
                    color: copied ? '#34d399' : 'var(--text-secondary)',
                    borderRadius: '8px',
                    padding: '0.35rem 0.75rem',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  title="Copy S3 presigned URL to clipboard"
                >
                  {copied ? '✓ Link Copied!' : '🔗 Copy Link'}
                </button>

                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    background: 'rgba(255, 255, 255, 0.06)',
                    border: '1px solid var(--border)',
                    color: 'var(--text-secondary)',
                    borderRadius: '8px',
                    padding: '0.35rem 0.75rem',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    textDecoration: 'none',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                    transition: 'all 0.2s',
                  }}
                >
                  ↗ Direct URL
                </a>
              </>
            )}

            <button
              id="download-btn"
              onClick={handleDownload}
              className="btn-gradient"
              style={{
                borderRadius: '8px',
                padding: '0.4rem 1rem',
                fontSize: '0.82rem',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
              }}
            >
              ↓ Download HD PNG
            </button>
          </div>
        )}
      </div>

      {/* 16:9 Canvas Frame */}
      <div
        className="canvas-16-9 glass-card"
        style={{
          border: '1px solid rgba(255, 255, 255, 0.12)',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
        }}
      >
        {loading ? (
          /* Multi-stage loading */
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '1.25rem',
            height: '100%',
            background: 'radial-gradient(circle at 50% 50%, rgba(255, 65, 108, 0.1) 0%, rgba(9, 10, 22, 0.95) 100%)',
          }}>
            <div className="spinner" style={{ width: '40px', height: '40px', borderWidth: '3.5px' }} />
            <div style={{ textAlign: 'center' }}>
              <p style={{
                margin: '0 0 0.35rem',
                color: 'var(--text-primary)',
                fontSize: '1.05rem',
                fontWeight: 700,
              }}>
                Synthesizing YouTube Thumbnail…
              </p>
              <p style={{
                margin: 0,
                color: 'var(--text-secondary)',
                fontSize: '0.85rem',
              }}>
                Groq Qwen optimizing visual prompt · FLUX.1 rendering 16:9 canvas
              </p>
            </div>
          </div>
        ) : dataUri ? (
          /* Output thumbnail */
          <img
            src={dataUri}
            alt="Generated YouTube thumbnail"
            className="fade-in-up"
            style={{
              objectFit: 'contain',
              width: '100%',
              height: '100%',
              display: 'block',
            }}
          />
        ) : (
          /* Empty placeholder */
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            gap: '0.75rem',
            background: 'radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.05) 0%, rgba(9, 10, 22, 0.8) 100%)',
          }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '20px',
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '2rem',
              opacity: 0.6,
            }}>
              🖼️
            </div>
            <p style={{
              margin: '0.2rem 0 0',
              color: 'var(--text-primary)',
              fontSize: '1rem',
              fontWeight: 600,
            }}>
              Your 16:9 masterpiece will render here
            </p>
            <p style={{
              margin: 0,
              color: 'var(--text-muted)',
              fontSize: '0.82rem',
            }}>
              Type a prompt or choose an idea above, then tap Generate
            </p>
          </div>
        )}
      </div>

      {/* Attribution footer */}
      {imageBase64 && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '0.65rem',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
        }}>
          <span>Aspect Ratio: 16:9 (Landscape)</span>
          <span>Engine: Groq Qwen-2.5-32b · FLUX.1-schnell</span>
        </div>
      )}
    </div>
  )
}
