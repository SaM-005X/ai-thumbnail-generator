"""
ai_service.py

Groq AI integration service for YouTube thumbnail prompt engineering
and image generation using FLUX.

Architecture:
  1. Groq (qwen/qwen3.8-27b):
     Rewrites the user's concept into a tightly-scoped, subject-faithful FLUX
     image prompt. The subject of the user's request is ALWAYS preserved.
  2. FLUX Image Generator (via Pollinations):
     Renders a 16:9 landscape (1280×720) thumbnail with enhanced quality.

All generated images are:
  - Returned as base64-encoded data
  - Automatically saved to backend/outputs/ via storage.py
"""

import asyncio
import base64
import os
import random
import re
import urllib.parse
from datetime import datetime

import httpx
from dotenv import load_dotenv
from groq import Groq

from app.storage import (
    is_s3_configured,
    save_image,
    save_image_locally,
)

# Load environment variables from backend/.env
load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TEXT_MODEL = "qwen/qwen3.8-27b"
_MODEL_NAME = "Groq (Qwen) + FLUX"

# Quality suffix appended to every FLUX prompt
_FLUX_QUALITY_SUFFIX = (
    ", professional YouTube thumbnail, wide landscape format 16:9, "
    "cinematic photography, dramatic lighting, sharp focus, vivid colors, "
    "high resolution, 4k, photorealistic"
)

# System prompt: strict single-output instruction
_SYSTEM_GENERATE = (
    "You are a text-to-image prompt writer for FLUX, a photorealistic image model. "
    "Your job: take the user's subject and rewrite it as a single, concise FLUX image prompt. "
    "RULES:\n"
    "- ALWAYS keep the user's subject exactly as described (e.g. if they say 'banana', the prompt must show a banana)\n"
    "- Write ONE prompt only, no lists, no options, no headers, no markdown\n"
    "- Add vivid visual details: lighting, colors, background, style, mood\n"
    "- Frame it as a dramatic, eye-catching 16:9 YouTube thumbnail composition\n"
    "- Output ONLY the raw prompt text, nothing else — no quotes, no intro, no explanation\n"
    "- Max 60 words\n"
)

_SYSTEM_EDIT = (
    "You are a text-to-image prompt writer for FLUX. "
    "The user wants to modify an existing YouTube thumbnail. "
    "Rewrite their edit instruction as a single concise FLUX image prompt. "
    "RULES:\n"
    "- Keep all requested changes from the user\n"
    "- ONE prompt only, no lists, no markdown, no headers\n"
    "- Describe the full scene with the edit applied, dramatic 16:9 composition\n"
    "- Output ONLY the raw prompt text, nothing else — no quotes, no intro\n"
    "- Max 60 words\n"
)


def _get_client() -> Groq:
    """
    Create and return a configured Groq API client.

    Raises:
        RuntimeError: If GROQ_API_KEY is not set in the environment.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. "
            "Create backend/.env with GROQ_API_KEY=<your_key>. "
            "See backend/.env.example for reference."
        )
    return Groq(api_key=api_key)


def _make_filename(prefix: str) -> str:
    """Generate a timestamped filename for saved output images."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.jpg"


def _strip_thinking_tags(text: str) -> str:
    """
    Strip <think>...</think> reasoning blocks that Qwen models sometimes output.
    Also removes markdown formatting if the model disregards instructions.
    """
    # Remove <think>...</think> blocks (including multiline)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Remove markdown headers like ### Option 1:
    text = re.sub(r"#+\s+.*?\n", "", text)
    # Remove markdown bold/italic/code
    text = re.sub(r"[*_`>]", "", text)
    # Remove "Prompt:" prefixes
    text = re.sub(r"(?i)prompt\s*:\s*", "", text)
    # Extract only the first paragraph/sentence block
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if lines:
        return lines[0]
    return text.strip()


def _enhance_prompt_with_groq(prompt: str, is_edit: bool = False) -> str:
    """
    Use Groq's Qwen model to rewrite the user's prompt as a clean FLUX image prompt.

    The subject from the user's prompt is always preserved faithfully.

    Args:
        prompt: User's visual prompt or edit instruction.
        is_edit: Whether this is an edit/modification instruction.

    Returns:
        A single, clean prompt string optimized for FLUX image generation.
    """
    client = _get_client()

    system_instruction = _SYSTEM_EDIT if is_edit else _SYSTEM_GENERATE
    user_message = f"Subject: {prompt.strip()}"

    try:
        completion = client.chat.completions.create(
            model=_TEXT_MODEL,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            temperature=0.5,
            max_completion_tokens=128,
            top_p=0.85,
            stream=False,
            stop=None,
        )
        raw = completion.choices[0].message.content or ""
        cleaned = _strip_thinking_tags(raw)
        if cleaned and len(cleaned) > 10:
            return cleaned + _FLUX_QUALITY_SUFFIX
    except Exception as e:
        print(f"Warning: Groq prompt enhancement failed ({e}), using direct prompt.")

    # Fallback: use the user's prompt directly with quality suffix
    return prompt.strip() + _FLUX_QUALITY_SUFFIX


async def _render_image_from_prompt(enhanced_prompt: str) -> tuple[bytes, str]:
    """
    Render a 16:9 thumbnail image using FLUX via Pollinations AI with automatic
    retry, seed rotation, and safe encoding to prevent transient HTTP 500 errors.

    Args:
        enhanced_prompt: The detailed visual prompt.

    Returns:
        tuple of (image_bytes: bytes, mime_type: str)

    Raises:
        ValueError: If image generation fails after all retry attempts.
    """
    # Clean whitespace and strictly encode special characters (including slashes)
    cleaned_prompt = " ".join(enhanced_prompt.split())
    encoded_prompt = urllib.parse.quote(cleaned_prompt, safe="")

    # Try FLUX first; if transient error occurs on free cluster, retry with a fresh seed, then fallback
    attempts = [
        {"model": "flux", "timeout": 60.0},
        {"model": "flux", "timeout": 60.0},
        {"model": None,   "timeout": 45.0},  # Pollinations default high-speed engine
    ]

    last_error = None
    async with httpx.AsyncClient(follow_redirects=True) as http_client:
        for idx, config in enumerate(attempts):
            seed = random.randint(10000, 9999999)
            model_query = f"&model={config['model']}" if config["model"] else ""
            url = (
                f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                f"?width=1280&height=720{model_query}&nologo=true&seed={seed}"
            )

            try:
                response = await http_client.get(url, timeout=config["timeout"])
                if response.status_code == 200:
                    image_bytes = response.content
                    if len(image_bytes) >= 5000:
                        mime_type = response.headers.get("content-type", "image/jpeg").split(";")[0]
                        return image_bytes, mime_type
                    else:
                        last_error = "Insufficient image bytes received from render engine."
                else:
                    last_error = f"HTTP {response.status_code}"
            except Exception as exc:
                last_error = str(exc)

            # Pause briefly before retry if not on the last attempt
            if idx < len(attempts) - 1:
                await asyncio.sleep(1.5)

    raise ValueError(
        f"Image generation service temporarily unavailable ({last_error}). "
        "Please try again in a moment."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_thumbnail(prompt: str) -> dict:
    """
    Generate a 16:9 YouTube thumbnail from a validated text prompt.

    Flow:
      1. Groq (qwen/qwen3.8-27b) rewrites the prompt faithfully into a FLUX prompt.
      2. FLUX renders a 1280×720 enhanced thumbnail.
      3. Saves image locally to backend/outputs/.

    Args:
        prompt: A validated visual prompt (already passed through the guardrail).

    Returns:
        dict with keys: image_base64, mime_type, saved_path, model, prompt_used.

    Raises:
        RuntimeError: If GROQ_API_KEY is not configured.
        ValueError: If image generation fails.
    """
    # Validate API key is present upfront
    _get_client()

    enhanced_prompt = _enhance_prompt_with_groq(prompt, is_edit=False)
    print(f"[ai_service] Enhanced prompt: {enhanced_prompt}")

    image_bytes, mime_type = await _render_image_from_prompt(enhanced_prompt)

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    filename = _make_filename("generated")
    if is_s3_configured():
        storage_res = await save_image(image_bytes, filename, content_type=mime_type)
        saved_path = storage_res["saved_path"]
        s3_url = storage_res.get("url")
    else:
        saved_path = await save_image_locally(image_bytes, filename)
        s3_url = None

    return {
        "image_base64": image_b64,
        "mime_type": mime_type,
        "saved_path": saved_path,
        "url": s3_url,
        "model": _MODEL_NAME,
        "prompt_used": enhanced_prompt,
    }


async def edit_thumbnail(prompt: str, image_bytes: bytes) -> dict:
    """
    Generate a new edited thumbnail from a validated modification prompt.

    Args:
        prompt:      A validated modification prompt.
        image_bytes: Raw bytes of the reference image uploaded by the user.

    Returns:
        dict with keys: image_base64, mime_type, saved_path, url, model, prompt_used, input_image_bytes.

    Raises:
        RuntimeError: If GROQ_API_KEY is not configured.
        ValueError: If image generation fails.
    """
    _get_client()

    enhanced_prompt = _enhance_prompt_with_groq(prompt, is_edit=True)
    print(f"[ai_service] Edit prompt: {enhanced_prompt}")

    out_bytes, mime_type = await _render_image_from_prompt(enhanced_prompt)

    output_b64 = base64.b64encode(out_bytes).decode("utf-8")
    filename = _make_filename("edited")
    if is_s3_configured():
        storage_res = await save_image(out_bytes, filename, content_type=mime_type)
        saved_path = storage_res["saved_path"]
        s3_url = storage_res.get("url")
    else:
        saved_path = await save_image_locally(out_bytes, filename)
        s3_url = None

    return {
        "image_base64": output_b64,
        "mime_type": mime_type,
        "saved_path": saved_path,
        "url": s3_url,
        "model": _MODEL_NAME,
        "prompt_used": enhanced_prompt,
        "input_image_bytes": len(image_bytes),
    }
