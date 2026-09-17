"""
test_guardrail.py

Unit tests for the prompt guardrail validation engine.

Tests verify:
  - Valid image/thumbnail prompts are ACCEPTED.
  - Coding requests are REJECTED.
  - General knowledge questions are REJECTED.
  - Essay / writing requests are REJECTED.
  - Empty prompts are REJECTED.
  - Prompts with no visual keywords are REJECTED.
"""

import pytest
from app.guardrail import validate_prompt


# ---------------------------------------------------------------------------
# Tests: Prompts that SHOULD be ACCEPTED (is_allowed=True)
# ---------------------------------------------------------------------------

class TestAcceptedPrompts:

    def test_gaming_thumbnail(self):
        result = validate_prompt("A dramatic gaming thumbnail with neon blue lights and dark background")
        assert result.is_allowed is True, f"Expected ACCEPTED but got: {result.message}"

    def test_youtube_thumbnail_request(self):
        result = validate_prompt("Create a bold YouTube thumbnail with fire effects and a person reacting")
        assert result.is_allowed is True, f"Expected ACCEPTED but got: {result.message}"

    def test_landscape_scene(self):
        result = validate_prompt("A cinematic mountain landscape at golden hour with vibrant colors")
        assert result.is_allowed is True, f"Expected ACCEPTED but got: {result.message}"

    def test_portrait_thumbnail(self):
        result = validate_prompt("A dramatic portrait of a gamer with neon glow lighting")
        assert result.is_allowed is True, f"Expected ACCEPTED but got: {result.message}"

    def test_image_edit_prompt(self):
        result = validate_prompt("Change the background to a dark forest with moody lighting")
        assert result.is_allowed is True, f"Expected ACCEPTED but got: {result.message}"

    def test_simple_image_request(self):
        result = validate_prompt("Generate a thumbnail with bold text and a red background")
        assert result.is_allowed is True, f"Expected ACCEPTED but got: {result.message}"

    def test_reaction_thumbnail(self):
        result = validate_prompt("Make an epic reaction thumbnail with bright colors and a shocked face")
        assert result.is_allowed is True, f"Expected ACCEPTED but got: {result.message}"


# ---------------------------------------------------------------------------
# Tests: Prompts that SHOULD be REJECTED (is_allowed=False)
# ---------------------------------------------------------------------------

class TestRejectedPrompts:

    def test_coding_request_python(self):
        result = validate_prompt("write me a python script to sort a list")
        assert result.is_allowed is False
        assert result.reason == "NON_IMAGE_INTENT"

    def test_coding_request_function(self):
        result = validate_prompt("write a function that reverses a string")
        assert result.is_allowed is False
        assert result.reason == "NON_IMAGE_INTENT"

    def test_general_question(self):
        result = validate_prompt("what is the capital of France")
        assert result.is_allowed is False
        assert result.reason == "NON_IMAGE_INTENT"

    def test_essay_request(self):
        result = validate_prompt("write an essay about climate change")
        assert result.is_allowed is False
        assert result.reason == "NON_IMAGE_INTENT"

    def test_explanation_request(self):
        result = validate_prompt("explain how machine learning works")
        assert result.is_allowed is False
        assert result.reason == "NON_IMAGE_INTENT"

    def test_translation_request(self):
        result = validate_prompt("translate this sentence to Spanish")
        assert result.is_allowed is False
        assert result.reason == "NON_IMAGE_INTENT"

    def test_math_request(self):
        result = validate_prompt("calculate the area of a circle with radius 5")
        assert result.is_allowed is False
        assert result.reason == "NON_IMAGE_INTENT"

    def test_empty_prompt(self):
        result = validate_prompt("")
        assert result.is_allowed is False
        assert result.reason == "EMPTY_PROMPT"

    def test_whitespace_only_prompt(self):
        result = validate_prompt("   ")
        assert result.is_allowed is False
        assert result.reason == "EMPTY_PROMPT"

    def test_no_visual_keywords(self):
        result = validate_prompt("something fast and powerful")
        assert result.is_allowed is False
        assert result.reason == "NO_VISUAL_INTENT"
