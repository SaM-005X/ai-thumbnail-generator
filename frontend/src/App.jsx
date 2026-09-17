import { useState } from 'react'
import Header from './components/Header'
import ModeSelector from './components/ModeSelector'
import PromptInput from './components/PromptInput'
import ImageUploader from './components/ImageUploader'
import GenerateButton from './components/GenerateButton'
import ResultPanel from './components/ResultPanel'
import Gallery from './components/Gallery'
import { API_BASE_URL } from './config'

/**
 * App
 *
 * Root component — owns all application state and API communication.
 *
 * Tabs:
 *   "create"  — the generation / edit form
 *   "gallery" — history of past generations (fetched from Supabase)
 *
 * State:
 *   tab         — "create" | "gallery"
 *   mode        — "generate" | "edit"
 *   prompt      — current prompt text
 *   file        — selected reference image File (edit mode only)
 *   loading     — true while API request is in flight
 *   error       — guardrail rejection message or API error string
 *   result      — { image_base64, mime_type } from the backend
 *   newGalleryItem — most recently generated item, forwarded to Gallery
 *
 * API:
 *   Generate: POST /api/generate  { prompt }
 *   Edit:     POST /api/edit      multipart/form-data { prompt, image }
 *   History:  GET  /api/history
 */
export default function App() {
  const [tab,            setTab]            = useState('create')
  const [mode,           setMode]           = useState('generate')
  const [prompt,         setPrompt]         = useState('')
  const [file,           setFile]           = useState(null)
  const [loading,        setLoading]        = useState(false)
  const [error,          setError]          = useState(null)
  const [result,         setResult]         = useState(null)
  const [newGalleryItem, setNewGalleryItem] = useState(null)

  /* ── Tab switch ── */
  const handleTabChange = newTab => {
    setTab(newTab)
    setError(null)
  }

  /* ── Mode switch: clear edit-specific state ── */
  const handleModeChange = newMode => {
    setMode(newMode)
    setError(null)
    if (newMode === 'generate') setFile(null)
  }

  /* ── Prompt change: clear previous error ── */
  const handlePromptChange = value => {
    setPrompt(value)
    if (error) setError(null)
  }

  /* ── Main generation / edit handler ── */
  const handleGenerate = async () => {
    if (!prompt.trim()) return
    if (mode === 'edit' && !file) {
      setError('Please upload a reference image to edit.')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      let response

      if (mode === 'generate') {
        response = await fetch(`${API_BASE_URL}/api/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: prompt.trim() }),
        })
      } else {
        const formData = new FormData()
        formData.append('prompt', prompt.trim())
        formData.append('image', file)
        response = await fetch(`${API_BASE_URL}/api/edit`, {
          method: 'POST',
          body: formData,
        })
      }


      const json = await response.json()

      if (!response.ok) {
        let detail = json?.detail ?? 'Something went wrong. Please try again.'
        if (Array.isArray(detail)) {
          detail = detail.map(d => d.msg || JSON.stringify(d)).join('. ')
        } else if (typeof detail === 'object' && detail !== null) {
          detail = detail.msg || JSON.stringify(detail)
        }
        setError(detail)
        return
      }

      const imageData = {
        image_base64: json.data.image_base64,
        mime_type:    json.data.mime_type ?? 'image/jpeg',
        url:          json.data.url ?? null,
      }
      setResult(imageData)

      // Forward to gallery as an optimistic entry (no refetch needed)
      setNewGalleryItem({
        id:         Date.now(),           // temp id until DB assigns one
        created_at: new Date().toISOString(),
        prompt:     prompt.trim(),
        mode,
        image_b64:  json.data.image_base64,
        mime_type:  json.data.mime_type ?? 'image/jpeg',
        model:      json.data.model ?? 'Groq + FLUX',
      })
    } catch (err) {
      setError(
        'Could not reach the backend. ' +
        'Make sure the FastAPI server is running on http://localhost:8000.'
      )
    } finally {
      setLoading(false)
    }
  }

  const isGenerateDisabled = !prompt.trim() || (mode === 'edit' && !file)

  return (
    <div style={{
      minHeight: '100vh',
      padding: 'clamp(1.5rem, 4vw, 3rem) 1rem',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
    }}>
      <div style={{ width: '100%', maxWidth: '900px' }}>

        {/* ── Header ── */}
        <Header />

        {/* ── Tab Bar ── */}
        <div className="tab-bar">
          <button
            id="tab-create"
            className={`tab-pill ${tab === 'create' ? 'active' : ''}`}
            onClick={() => handleTabChange('create')}
            aria-selected={tab === 'create'}
            role="tab"
          >
            ✦ Create
          </button>
          <button
            id="tab-gallery"
            className={`tab-pill ${tab === 'gallery' ? 'active' : ''}`}
            onClick={() => handleTabChange('gallery')}
            aria-selected={tab === 'gallery'}
            role="tab"
          >
            🖼 Gallery
          </button>
        </div>

        {/* ── Create Tab ── */}
        {tab === 'create' && (
          <>
            <div className="glass-card" style={{ padding: 'clamp(1.25rem, 4vw, 2rem)' }}>

              {/* Mode toggle */}
              <ModeSelector mode={mode} onChange={handleModeChange} />

              {/* Image uploader (edit mode only) */}
              {mode === 'edit' && (
                <ImageUploader file={file} onChange={setFile} />
              )}

              {/* Prompt input */}
              <PromptInput
                value={prompt}
                onChange={handlePromptChange}
                error={mode === 'edit' && !file && error === 'Please upload a reference image to edit.'
                  ? null
                  : error
                }
                mode={mode}
              />

              {/* File-missing error (edit mode) */}
              {mode === 'edit' && error === 'Please upload a reference image to edit.' && (
                <p role="alert" style={{
                  margin: '-0.5rem 0 0.75rem',
                  fontSize: '0.82rem',
                  color: 'var(--error)',
                }}>
                  ⚠ {error}
                </p>
              )}

              {/* Generate / Edit button */}
              <div style={{ marginTop: '0.75rem' }}>
                <GenerateButton
                  onClick={handleGenerate}
                  loading={loading}
                  disabled={isGenerateDisabled}
                  mode={mode}
                />
              </div>
            </div>

            {/* ── Result panel ── */}
            <ResultPanel
              imageBase64={result?.image_base64 ?? null}
              mimeType={result?.mime_type}
              url={result?.url ?? null}
              loading={loading}
            />
          </>
        )}

        {/* ── Gallery Tab ── */}
        {tab === 'gallery' && (
          <Gallery newItem={newGalleryItem} />
        )}

        {/* ── Footer ── */}
        <footer style={{
          marginTop: '2.5rem',
          textAlign: 'center',
          fontSize: '0.75rem',
          color: 'var(--text-secondary)',
          opacity: 0.5,
        }}>
          AI Thumbnail Generator · Powered by Groq (Qwen) & FLUX · History by Supabase
        </footer>
      </div>
    </div>
  )
}
