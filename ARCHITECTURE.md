# AI Thumbnail Generator — System Architecture & Design Blueprint

## 1. Project Overview
An AI-powered web application specifically engineered for generating, editing, and managing 16:9 YouTube thumbnails.
The application provides:
- **Text-to-Thumbnail**: Transforming raw concepts into click-optimized, cinematic 16:9 YouTube thumbnails.
- **Image-to-Image Editing**: Uploading an existing thumbnail or subject image and instructing the AI to modify visual attributes (lighting, composition, scene background).
- **Strict Visual Intent Guardrail**: Rejecting non-image requests (e.g. general questions, coding requests) at the backend API layer.
- **Persistent Cloud History**: Auto-syncing generated thumbnails to PostgreSQL database with interactive modal previews and granular/bulk deletion.

---

## 2. Technology Stack & Architectural Decisions

| Component | Technology | Rationale & Responsibility |
| :--- | :--- | :--- |
| **Frontend** | React 19 + Vite 8 + CSS Design System | Pure client-side SPA. Zero server runtime, sub-150ms builds, hosted on S3 and edge-cached globally via Cloudflare CDN. |
| **Backend API** | Python 3.12 (FastAPI) + Mangum | Asynchronous REST framework with native Pydantic data validation and auto-generated Swagger UI (`/docs`). Mangum adapts ASGI to AWS Lambda. |
| **Serverless Compute**| AWS Lambda (`ap-south-1`) | Scales to zero ($0 idle cost), executes backend logic in an isolated containerized environment without EC2 server maintenance. |
| **API Gateway** | Amazon API Gateway (HTTP API) | Serverless ingress proxy routing `$default` requests to AWS Lambda with explicit CORS preflight support. |
| **Edge CDN & SSL** | Cloudflare Global CDN + Universal SSL | Global edge caching across 300+ cities, DDoS mitigation, and instant HTTPS termination on custom domain `https://samratdev.fun`. |
| **Database** | Supabase (PostgreSQL) | Serverless PostgreSQL database with real-time REST client, zero-config connection pooling, storing generation history and prompt metadata. |
| **Object Storage**| Amazon S3 (`ap-south-1`) | 100% private bucket (`ai-thumbnails-samrat-1234`) storing user uploads and generated thumbnails. Generates 24-hour cryptographically signed Presigned URLs. |
| **AI Prompt Engine**| Groq Cloud LPU (`qwen/qwen3.8-27b`) | Hardware-accelerated inference running Qwen-2.5-32b to expand user prompts into professional cinematography directions in ~300ms. |
| **AI Image Engine** | FLUX.1-schnell Engine | Open-weights state-of-the-art diffusion model generating crisp, high-CTR 16:9 landscape (1280×720) thumbnails with vivid color grading. |

---

## 3. Architecture Evolution & Technology Pivots

During development, two major technology pivots were engineered to guarantee production stability, eliminate account holds, and optimize generation latency:

### Pivot 1: AWS CloudFront ➔ Cloudflare CDN & Universal SSL
- **Initial Blueprint:** Use AWS CloudFront edge distributions linked to AWS Certificate Manager (ACM) certificates in `us-east-1` to distribute the S3 frontend.
- **The Roadblock:** Newly created AWS accounts triggered an automated CloudFront resource freeze:
  `AccessDenied: Your account must be verified before you can add new CloudFront resources. To verify your account, please contact AWS Support.`
  Basic AWS support tickets can take 24 to 48 hours to resolve, blocking public HTTPS launch.
- **The Modern Solution:** Pivoted to **Cloudflare CDN**:
  1. Updated Hostinger nameservers to Cloudflare (`edward.ns.cloudflare.com`, `lexi.ns.cloudflare.com`).
  2. Routed custom domain `samratdev.fun` to S3 static website hosting via Cloudflare CNAME with **Orange Cloud (Proxied)**.
  3. Activated Cloudflare Universal SSL (Flexible mode) for immediate, zero-latency HTTPS.
  4. Configured apex domain bucket `samratdev.fun` and `www.samratdev.fun` with HTTP 301 redirection.
- **Architectural Benefits:** Zero waiting time, global Anycast caching across 300+ cities, automatic HTTP-to-HTTPS upgrade, free DDoS shielding, and zero infrastructure cost.

### Pivot 2: Google Gemini / Imagen ➔ Groq LPU (Qwen) + FLUX.1-schnell
- **Initial Blueprint:** Use Google Gemini API and Google Imagen for prompt generation and image rendering.
- **The Roadblock:** Google Imagen required complex Google Cloud Vertex AI project configurations, billing activation hurdles, regional quotas, and multi-second latency per request.
- **The Modern Solution:** Decoupled into a 2-stage high-speed pipeline:
  1. **Groq LPU (Language Processing Unit):** Uses dedicated LPUs to process `qwen/qwen3.8-27b` in ~300ms, strictly preserving the user's core subject while injecting cinematography lighting, framing, and YouTube thumbnail contrast rules.
  2. **FLUX.1-schnell Diffusion Engine:** Directly generates 16:9 photorealistic landscape images with sharp focus, high color depth, and exceptional prompt adherence in ~2-3 seconds.
- **Architectural Benefits:** Sub-3-second total generation lifecycle, zero GPU quota bottlenecks, and subject-faithful outputs.

---

## 4. High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph Client["User Browser"]
        U["User Device"]
    end

    subgraph CDN_Layer["Edge CDN & Security (Cloudflare)"]
        CF["Cloudflare Global Edge Proxy\n• Universal SSL/TLS (HTTPS)\n• Edge Cache (300+ Cities)\n• Custom Domain: samratdev.fun"]
    end

    subgraph AWS_Cloud["AWS Cloud (Region: ap-south-1)"]
        S3_Apex["S3 Website Bucket: samratdev.fun\n(Hosts SPA Production Bundle)"]
        S3_Www["S3 Website Bucket: www.samratdev.fun\n(301 Redirect to Apex)"]
        APIGW["Amazon API Gateway (HTTP API)\n• Route: $default (Proxy)\n• CORS: GET, POST, DELETE, OPTIONS"]
        Lambda["AWS Lambda (Python 3.12)\n• FastAPI + Mangum Adapter\n• Visual Intent Guardrail"]
        S3_Img["S3 Storage Bucket: ai-thumbnails-samrat-1234\n(Private Storage + 24h Presigned URLs)"]
    end

    subgraph External_Services["External Cloud Services"]
        Groq["Groq Cloud LPU\n(Qwen Fast Prompt Engineering)"]
        Flux["FLUX.1-schnell Engine\n(16:9 Landscape Thumbnail Synthesis)"]
        Supabase[("Supabase Cloud\n(PostgreSQL Generation History)")]
    end

    U -->|"1. HTTPS Request (samratdev.fun)"| CF
    CF -->|"2. Fetch Static Assets (Origin)"| S3_Apex
    CF -.->|"Redirect www requests"| S3_Www
    U -->|"3. REST API Requests (/api/*)"| APIGW
    APIGW -->|"4. Proxy Event"| Lambda
    Lambda -->|"5. Validate & Expand Prompt (300ms)"| Groq
    Lambda -->|"6. Synthesize 16:9 Thumbnail"| Flux
    Lambda -->|"7. Save/Delete Record Metadata"| Supabase
    Lambda -->|"8. Upload Binary & Sign Presigned URL"| S3_Img
    Lambda -->|"9. Return JSON Response"| APIGW
    APIGW -->|"10. JSON Payload"| U
```

---

## 5. API Reference & Endpoint Specifications

All endpoints are hosted live at:  
`https://78jpzfhwr4.execute-api.ap-south-1.amazonaws.com`

| Method | Path | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Health and status check | None | `{ "status": "ok", "timestamp": ... }` |
| `POST` | `/api/generate` | Generate 16:9 thumbnail from text | `{ "prompt": "..." }` | `{ "image_base64": "...", "mime_type": "image/jpeg" }` |
| `POST` | `/api/edit` | Image-to-image editing | Multipart form: `prompt` + `image` | `{ "image_base64": "...", "mime_type": "image/jpeg" }` |
| `GET` | `/api/history` | Retrieve past generations | None | `[ { "id": 1, "prompt": "...", "image_url": "..." } ]` |
| `DELETE` | `/api/history/{id}` | Delete specific generation item | URL Parameter: `id` | `{ "deleted": true, "id": 1 }` |
| `DELETE` | `/api/history` | Clear entire generation history | None | `{ "cleared": true }` |

### CORS Preflight Architecture
To allow browser deletions and cross-origin calls from `https://samratdev.fun`:
- **API Gateway CORS:** Configured with `AllowMethods: ['GET', 'POST', 'DELETE', 'OPTIONS', 'HEAD']` and `AllowHeaders: ['*']`.
- **FastAPI Middleware:** CORSMiddleware with `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`.

---

## 6. Project Directory Structure

```text
ai-thumbnail-generator/
├── ARCHITECTURE.md                  # System design & technology blueprint
├── MASTER_GUIDE.md                  # Comprehensive beginner-to-pro engineering guide
├── PROJECT_DOCS.txt                 # Detailed engineering logbook & phase milestones
├── ROADMAP.md                       # Phase checklist and progress tracker
├── .gitignore                       # Strict exclusion of .env, .venv, node_modules
├── backend/                         # Python FastAPI serverless backend
│   ├── app/
│   │   ├── __init__.py              # Package initializer
│   │   ├── main.py                  # FastAPI app, routes, Mangum handler, CORS
│   │   ├── ai_service.py            # Groq (Qwen) & FLUX.1 generation pipeline
│   │   ├── guardrail.py             # 2-layer visual prompt intent guardrail
│   │   ├── database.py              # Supabase PostgreSQL client & query methods
│   │   └── storage.py               # Amazon S3 upload & presigned URL signing
│   ├── tests/                       # Automated test suite (32 tests passing)
│   │   ├── test_ai_service.py       # Mocked AI prompt expansion & generation tests
│   │   ├── test_guardrail.py        # Content moderation & guardrail tests
│   │   └── test_storage.py          # S3 presigned URL & local fallback tests
│   ├── deploy_lambda.py             # AWS Lambda & API Gateway provisioning script
│   ├── package_lambda.py            # Linux x86_64 binary wheel packager
│   ├── requirements.txt             # Full dependencies for local development
│   ├── requirements-lambda.txt      # Lightweight production dependencies for Lambda
│   ├── run.py                       # Local Uvicorn server entrypoint
│   └── .env.example                 # Environment configuration template
└── frontend/                        # React 19 + Vite client application
    ├── src/
    │   ├── components/              # UI components
    │   │   ├── Gallery.jsx          # History grid, modal lightbox, item/bulk deletion
    │   │   ├── GenerateButton.jsx   # Dynamic submit button with loading animations
    │   │   ├── Header.jsx           # Studio Pro status beacon and header
    │   │   ├── ImageUploader.jsx    # Drag-and-drop reference image uploader
    │   │   ├── ModeSelector.jsx     # Generate vs Edit mode switcher
    │   │   ├── PromptInput.jsx      # Auto-focusing prompt textarea with suggestions
    │   │   └── ResultPanel.jsx      # 16:9 canvas preview, download, and copy buttons
    │   ├── config.js                # Environment API endpoint resolver
    │   ├── index.css                # Curated Studio Pro design system
    │   ├── App.jsx                  # Root state management & API coordinator
    │   └── main.jsx                 # React root renderer
    ├── public/                      # Static branding assets (favicon.svg, icons.svg)
    ├── deploy_frontend.py           # Automated S3 sync & website configuration script
    ├── request_cert.py              # AWS ACM certificate validation helper
    ├── package.json                 # Node dependencies (React 19, Tailwind CSS v4)
    ├── vite.config.js               # Vite bundler & local dev proxy configuration
    └── .env.example                 # Frontend environment template
```


