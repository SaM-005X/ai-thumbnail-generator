# AI Thumbnail Generator — Frontend (React 19 + Vite)

A modern, high-performance web interface designed for creating and managing YouTube thumbnails. Built with **React 19**, **Vite**, and customized **Studio Pro Dark Theme** styling.

---

## ⚡ Tech Stack

- **Framework:** React 19 (Hooks, Functional Components)
- **Build Tool:** Vite 8 (Ultra-fast HMR and bundling)
- **Styling:** Custom Studio Pro CSS (`src/index.css`) with Tailwind CSS v4 support
- **Hosting:** Amazon S3 Static Website Hosting
- **CDN & Security:** Cloudflare Global CDN + Universal SSL/TLS (HTTPS)
- **Custom Domain:** [https://samratdev.fun](https://samratdev.fun)

---

## 🚀 Key Features

1. **Text-to-Thumbnail:** Enter any concept; Groq LPU enhances the prompt into a cinematography prompt and FLUX renders a 16:9 thumbnail.
2. **Image-to-Image Editing:** Upload a reference image with targeted modification instructions.
3. **Strict Intent Guardrails:** Visual prompt enforcement rejects non-image requests instantly.
4. **Cloud History & Gallery:** Persistent gallery synchronized with Supabase PostgreSQL and Amazon S3.
5. **Interactive Gallery Management:** Fullscreen modal previews, instant downloads, individual thumbnail deletion, and bulk history clearing.

---

## 🛠️ Local Development

```bash
# Install dependencies
npm install

# Run local development server (with /api proxy to localhost:8000)
npm run dev

# Build production bundle
npm run build

# Deploy bundle to S3 and Cloudflare
backend\.venv\Scripts\python.exe frontend\deploy_frontend.py
```
