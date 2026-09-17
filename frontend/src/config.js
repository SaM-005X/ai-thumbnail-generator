/**
 * Frontend Configuration
 *
 * During local development without VITE_API_BASE_URL, API requests use relative
 * URLs (e.g. /api/generate) which Vite proxies to http://localhost:8000.
 *
 * In production or cloud testing, setting VITE_API_BASE_URL in frontend/.env
 * routes API requests directly to Amazon API Gateway (AWS Lambda).
 */
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
