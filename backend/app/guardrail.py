"""
guardrail.py

Strict prompt validation engine for the AI Thumbnail Generator.

This module enforces that the application is used EXCLUSIVELY for
thumbnail and image generation tasks. It uses a two-layer approach:

  Layer 1 — Keyword Blocklist:
      Instantly rejects prompts containing patterns that indicate
      non-image intent (coding requests, general questions, essays, etc.)
      This is fast, deterministic, and costs zero API calls.

  Layer 2 — Visual Keyword Check:
      Verifies that the prompt contains at least one word or phrase
      that indicates a visual/image intent (scene, background, lighting,
      person, thumbnail, etc.)

If a prompt fails either layer, it is rejected with an educational
message guiding the user back to the correct usage.
"""

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Layer 1: Non-image intent patterns (BLOCKLIST)
# ---------------------------------------------------------------------------
# These patterns detect requests that are clearly NOT image generation.
# Using word boundaries (\b) ensures we match whole words only.
BLOCKLIST_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(write|code|program|script|function|algorithm)\b", re.IGNORECASE),
    re.compile(r"\b(explain|summarize|summarise|describe how|tell me|what is|who is|why is|how does)\b", re.IGNORECASE),
    re.compile(r"\b(essay|article|blog|email|letter|report|story|poem)\b", re.IGNORECASE),
    re.compile(r"\b(calculate|compute|solve|math|equation|formula)\b", re.IGNORECASE),
    re.compile(r"\b(translate|grammar|spell check|proofread)\b", re.IGNORECASE),
    re.compile(r"\b(search|find|look up|google|browse)\b", re.IGNORECASE),
    re.compile(r"\b(recommend|suggest|advice|tips for|guide me)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Layer 2: Visual intent keywords (ALLOWLIST)
# ---------------------------------------------------------------------------
# A prompt must contain at least one of these to pass the visual check.
VISUAL_KEYWORDS: list[str] = [
    # Thumbnail & image specific
    "thumbnail", "image", "picture", "photo", "graphic",
    "illustration", "artwork", "poster", "banner", "cover",
    # Visual scene elements
    "background", "foreground", "scene", "landscape", "portrait",
    "sky", "city", "forest", "ocean", "mountain", "room", "space",
    # People & subjects
    "person", "man", "woman", "face", "character", "gamer", "creator",
    "streamer", "youtuber", "model", "silhouette", "figure",
    # Lighting & style
    "lighting", "light", "dark", "neon", "glow", "shadow", "dramatic",
    "cinematic", "vivid", "vibrant", "color", "bright", "moody",
    # Visual actions
    "generate", "create", "make", "design", "draw", "render",
    "show", "display", "visualize", "edit", "modify", "change",
    # Genre/style descriptors common in thumbnails
    "epic", "horror", "gaming", "reaction", "vs", "before after",
    "fire", "explosion", "impact", "bold", "text overlay",
]

# Pre-build a compiled pattern from the allowlist for efficiency
_VISUAL_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(kw) for kw in VISUAL_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class GuardrailResult:
    """Result of the guardrail validation."""
    is_allowed: bool
    reason: str  # Short internal code for why it was blocked/allowed
    message: str  # User-facing message


# ---------------------------------------------------------------------------
# Public validation function
# ---------------------------------------------------------------------------

def validate_prompt(prompt: str) -> GuardrailResult:
    """
    Validate whether a user prompt is appropriate for thumbnail/image generation.

    Args:
        prompt: The raw text prompt submitted by the user.

    Returns:
        GuardrailResult with is_allowed=True if valid, False if rejected.

    Examples:
        >>> validate_prompt("create a dramatic gaming thumbnail with red neon lights")
        GuardrailResult(is_allowed=True, ...)
        >>> validate_prompt("write me a python script")
        GuardrailResult(is_allowed=False, ...)
    """
    if not prompt or not prompt.strip():
        return GuardrailResult(
            is_allowed=False,
            reason="EMPTY_PROMPT",
            message="Please provide a visual description for your thumbnail.",
        )

    cleaned = prompt.strip()

    # --- Layer 1: Block non-image intent ---
    for pattern in BLOCKLIST_PATTERNS:
        if pattern.search(cleaned):
            return GuardrailResult(
                is_allowed=False,
                reason="NON_IMAGE_INTENT",
                message=(
                    "This application is dedicated strictly to thumbnail and image generation. "
                    "Please provide a visual prompt describing a scene, subject, or image modifications. "
                    f'Example: "A dramatic gaming thumbnail with a dark background and neon blue lighting."'
                ),
            )

    # --- Layer 2: Require at least one visual keyword ---
    if not _VISUAL_PATTERN.search(cleaned):
        return GuardrailResult(
            is_allowed=False,
            reason="NO_VISUAL_INTENT",
            message=(
                "Your prompt doesn't appear to describe a visual scene or image. "
                "Please include what you want to see — for example: subjects, backgrounds, "
                "lighting, colors, or style. "
                f'Example: "Bright landscape thumbnail with a golden sunset and mountain silhouette."'
            ),
        )

    # --- All checks passed ---
    return GuardrailResult(
        is_allowed=True,
        reason="VALID_VISUAL_PROMPT",
        message="Prompt accepted. Generating your thumbnail...",
    )
