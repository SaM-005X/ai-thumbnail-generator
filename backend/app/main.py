"""
main.py

FastAPI application entry point for the AI Thumbnail Generator backend.

API Endpoints:
  GET  /               → Health check
  POST /api/validate   → Validate a prompt through the guardrail
  POST /api/generate   → Validate + generate a thumbnail from a text prompt
  POST /api/edit       → Validate + edit an image with a modification prompt
  GET  /api/history    → Retrieve the last 20 generation history records

The server runs locally on http://localhost:8000
Interactive API docs available at http://localhost:8000/docs
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from groq import APIError, AuthenticationError, RateLimitError
from pydantic import BaseModel, Field
from mangum import Mangum

# Load .env as early as possible so all modules see the environment variables
load_dotenv()


# ---------------------------------------------------------------------------
# Startup Lifespan — fail fast if GROQ_API_KEY or Supabase keys are missing
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Validates that GROQ_API_KEY and Supabase credentials are configured
    before accepting any requests.
    """
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key or groq_key == "your_groq_api_key_here":
        raise RuntimeError(
            "\n\n❌  GROQ_API_KEY is not configured.\n"
            "    Create backend/.env and set:\n"
            "      GROQ_API_KEY=<your_actual_key>\n"
            "    See backend/.env.example for reference.\n"
        )
    print(f"✅  GROQ_API_KEY loaded (ends in ...{groq_key[-6:]})")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if supabase_url and supabase_key:
        print(f"✅  Supabase connected → {supabase_url[:40]}...")
    else:
        print("⚠️   SUPABASE_URL / SUPABASE_KEY not set — history will not be saved.")

    from app.storage import is_s3_configured
    if is_s3_configured():
        bucket = os.getenv("S3_BUCKET_NAME")
        region = os.getenv("AWS_REGION", "us-east-1")
        print(f"✅  Amazon S3 configured → Bucket: {bucket} ({region})")
    else:
        print("ℹ️   Amazon S3 not configured — using local storage fallback (backend/outputs/).")

    yield  # Server runs here


from app.guardrail import validate_prompt
from app.ai_service import generate_thumbnail, edit_thumbnail
from app.database import save_generation, get_history, delete_generation, clear_all_history
from app.storage import is_s3_configured


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Thumbnail Generator API",
    description=(
        "A backend API for generating and editing 16:9 YouTube thumbnails "
        "using Groq (qwen/qwen3.8-27b) prompt engineering and FLUX generation. "
        "Includes strict prompt guardrails and Supabase generation history."
    ),
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------

allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env:
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False if "*" in allowed_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ---------------------------------------------------------------------------
# Validation Error Handler
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Return clean, user-friendly strings for validation errors."""
    errors = exc.errors()
    if errors:
        first = errors[0]
        msg = first.get("msg", "Invalid input.")
        if "at least" in msg:
            msg = "Please enter a prompt with at least 3 characters."
        return JSONResponse(status_code=422, content={"detail": msg})
    return JSONResponse(status_code=422, content={"detail": "Invalid request parameters."})


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class PromptRequest(BaseModel):
    """Schema for a text prompt submission."""
    prompt: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Visual description for the thumbnail to generate or modify.",
        examples=["A dramatic gaming thumbnail with neon blue lighting and dark background."],
    )


class GuardrailResponse(BaseModel):
    """Schema for guardrail validation response."""
    is_allowed: bool
    reason: str
    message: str


class GenerateResponse(BaseModel):
    """Schema for image generation response."""
    success: bool
    message: str
    data: dict


class HistoryItem(BaseModel):
    """Schema for a single history record."""
    id: int
    created_at: str
    prompt: str
    mode: str
    image_b64: str
    mime_type: str
    model: str


class HistoryResponse(BaseModel):
    """Schema for the history list response."""
    success: bool
    count: int
    data: list[dict]


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/", summary="Health Check", tags=["Health"])
async def health_check():
    """Confirms the API is running and healthy."""
    s3_active = is_s3_configured()
    bucket = os.getenv("S3_BUCKET_NAME") if s3_active else None
    return {
        "status": "healthy",
        "service": "AI Thumbnail Generator API",
        "version": "0.5.0",
        "ai_model": "Groq (qwen/qwen3.8-27b) + FLUX",
        "storage": f"Amazon S3 (bucket: {bucket})" if s3_active else "Local File Storage (backend/outputs/)",
        "s3_configured": s3_active,
    }


@app.post(
    "/api/validate",
    response_model=GuardrailResponse,
    summary="Validate a prompt through the guardrail",
    tags=["Guardrail"],
)
async def validate(request: PromptRequest):
    """
    Run a prompt through the strict guardrail without generating an image.

    - **Accepted**: Prompt describes a visual scene, thumbnail, or image modification.
    - **Rejected**: Prompt is a coding request, general question, essay, etc.
    """
    result = validate_prompt(request.prompt)
    return GuardrailResponse(
        is_allowed=result.is_allowed,
        reason=result.reason,
        message=result.message,
    )


@app.post(
    "/api/generate",
    response_model=GenerateResponse,
    summary="Generate a thumbnail from a text prompt",
    tags=["Generation"],
)
async def generate(request: PromptRequest):
    """
    Validate the prompt, generate a 16:9 thumbnail, and persist to history.

    Flow:
      1. Guardrail validates the prompt.
      2. Groq enhances the prompt; FLUX renders the image.
      3. Record is saved to Supabase generation_history table.
    """
    # Step 1: Guardrail
    result = validate_prompt(request.prompt)
    if not result.is_allowed:
        raise HTTPException(status_code=400, detail=result.message)

    # Step 2: Generate
    try:
        generation_result = await generate_thumbnail(request.prompt)
    except AuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Groq API key. Check GROQ_API_KEY in backend/.env"
        )
    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Groq API rate limit reached. Please wait a moment and try again."
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"Groq API error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Step 3: Persist to Supabase (non-blocking — don't fail the request if DB is down)
    try:
        await save_generation(
            prompt=request.prompt,
            mode="generate",
            image_b64=generation_result["image_base64"],
            mime_type=generation_result.get("mime_type", "image/jpeg"),
            model=generation_result.get("model", "Groq + FLUX"),
            saved_path=generation_result.get("saved_path"),
        )
    except Exception as db_err:
        print(f"⚠️  DB save failed (non-fatal): {db_err}")

    return GenerateResponse(
        success=True,
        message=result.message,
        data=generation_result,
    )


@app.post(
    "/api/edit",
    response_model=GenerateResponse,
    summary="Edit an existing image with a modification prompt",
    tags=["Generation"],
)
async def edit(
    request: Request,
    prompt: str | None = Form(None, description="Visual modification instruction."),
    image: UploadFile = File(..., description="Reference image to modify (JPG, PNG, WEBP)."),
):
    """
    Validate the modification prompt, edit the uploaded image, and persist to history.

    Upload an existing thumbnail or photo and describe the modifications you want.
    """
    # Step 0: Resolve prompt from Form-data or Query Params
    effective_prompt = (prompt or request.query_params.get("prompt") or "").strip()
    if not effective_prompt:
        raise HTTPException(status_code=400, detail="Modification prompt cannot be empty.")
    prompt = effective_prompt

    # Step 1: Guardrail
    result = validate_prompt(prompt)
    if not result.is_allowed:
        raise HTTPException(status_code=400, detail=result.message)

    # Step 2: Read image bytes
    image_bytes = await image.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded image file is empty.")

    # Step 3: Edit
    try:
        edit_result = await edit_thumbnail(prompt, image_bytes)
    except AuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Groq API key. Check GROQ_API_KEY in backend/.env"
        )
    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Groq API rate limit reached. Please wait a moment and try again."
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"Groq API error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Step 4: Persist to Supabase (non-fatal)
    try:
        await save_generation(
            prompt=prompt,
            mode="edit",
            image_b64=edit_result["image_base64"],
            mime_type=edit_result.get("mime_type", "image/jpeg"),
            model=edit_result.get("model", "Groq + FLUX"),
            saved_path=edit_result.get("saved_path"),
        )
    except Exception as db_err:
        print(f"⚠️  DB save failed (non-fatal): {db_err}")

    return GenerateResponse(
        success=True,
        message=result.message,
        data=edit_result,
    )


@app.get(
    "/api/history",
    response_model=HistoryResponse,
    summary="Get generation history",
    tags=["History"],
)
async def history(limit: int = 20):
    """
    Retrieve the most recent generation history records.

    Returns up to `limit` records (default 20), ordered newest first.
    Each record includes the prompt, mode, model, timestamp, and image data.
    """
    try:
        records = await get_history(limit=min(limit, 50))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")

    return HistoryResponse(
        success=True,
        count=len(records),
        data=records,
    )


@app.delete(
    "/api/history/{item_id}",
    summary="Delete a single history record",
    tags=["History"],
)
async def delete_history_item(item_id: int):
    """
    Delete a specific generation history item by ID.
    """
    try:
        deleted = await delete_generation(item_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"History item {item_id} not found.")
        return {"success": True, "message": f"Deleted history item {item_id}."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete item: {str(e)}")


@app.delete(
    "/api/history",
    summary="Clear all history records",
    tags=["History"],
)
async def clear_history():
    """
    Delete all generation history records.
    """
    try:
        count = await clear_all_history()
        return {"success": True, "message": f"Cleared {count} history records.", "deleted_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")


# ---------------------------------------------------------------------------
# AWS Lambda Handler (Phase 7)
# ---------------------------------------------------------------------------

handler = Mangum(app, lifespan="off")
