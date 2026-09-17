"""
test_ai_service.py

Unit tests for the Groq + FLUX AI service module.

These tests use unittest.mock to patch the Groq client and HTTP rendering
so no real API calls are made and no GROQ_API_KEY is required to run tests.
"""

import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# A tiny 1x1 transparent PNG to use as a fake image in tests
_FAKE_IMAGE_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00"
    b"\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8"
    b"\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)
_FAKE_IMAGE_B64 = base64.b64encode(_FAKE_IMAGE_BYTES).decode("utf-8")

_VALID_PROMPT = "A dramatic gaming thumbnail with red neon lights and dark background"
_ENHANCED_PROMPT = "A vibrant 16:9 YouTube gaming thumbnail featuring neon red highlights"


def _make_mock_groq_completion(text: str = _ENHANCED_PROMPT) -> MagicMock:
    """Build a mock Groq chat completion response."""
    choice = MagicMock()
    choice.message.content = text
    completion = MagicMock()
    completion.choices = [choice]
    return completion


# ---------------------------------------------------------------------------
# generate_thumbnail tests
# ---------------------------------------------------------------------------

class TestGenerateThumbnail:

    @pytest.mark.asyncio
    @patch("app.ai_service._render_image_from_prompt", new_callable=AsyncMock)
    @patch("app.ai_service.save_image_locally", new_callable=AsyncMock)
    @patch("app.ai_service._get_client")
    async def test_returns_expected_dict_shape(self, mock_get_client, mock_save, mock_render):
        """generate_thumbnail should return a dict with all expected keys."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_groq_completion()
        mock_get_client.return_value = mock_client
        mock_save.return_value = "/fake/outputs/generated_20260915_120000.jpg"
        mock_render.return_value = (_FAKE_IMAGE_BYTES, "image/jpeg")

        from app.ai_service import generate_thumbnail
        result = await generate_thumbnail(_VALID_PROMPT)

        assert result["image_base64"] == _FAKE_IMAGE_B64
        assert result["mime_type"] == "image/jpeg"
        assert "saved_path" in result
        assert "Groq" in result["model"]
        assert "FLUX" in result["model"]
        assert result["prompt_used"].startswith(_ENHANCED_PROMPT)

    @pytest.mark.asyncio
    @patch("app.ai_service._render_image_from_prompt", new_callable=AsyncMock)
    @patch("app.ai_service.save_image_locally", new_callable=AsyncMock)
    @patch("app.ai_service._get_client")
    async def test_uses_groq_to_enhance_prompt(self, mock_get_client, mock_save, mock_render):
        """generate_thumbnail should call Groq chat completions to enhance the prompt."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_groq_completion()
        mock_get_client.return_value = mock_client
        mock_save.return_value = "/fake/path.jpg"
        mock_render.return_value = (_FAKE_IMAGE_BYTES, "image/jpeg")

        from app.ai_service import generate_thumbnail
        await generate_thumbnail(_VALID_PROMPT)

        assert mock_client.chat.completions.create.called
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "qwen/qwen3.8-27b"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    async def test_raises_runtime_error_when_no_api_key(self):
        """generate_thumbnail should raise RuntimeError if GROQ_API_KEY is unset."""
        os.environ.pop("GROQ_API_KEY", None)

        from app.ai_service import generate_thumbnail
        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            await generate_thumbnail(_VALID_PROMPT)

    @pytest.mark.asyncio
    @patch("app.ai_service._render_image_from_prompt", new_callable=AsyncMock)
    @patch("app.ai_service._get_client")
    async def test_raises_value_error_when_render_fails(self, mock_get_client, mock_render):
        """generate_thumbnail should propagate ValueError if rendering fails."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_groq_completion()
        mock_get_client.return_value = mock_client
        mock_render.side_effect = ValueError("Image generation failed")

        from app.ai_service import generate_thumbnail
        with pytest.raises(ValueError, match="Image generation failed"):
            await generate_thumbnail(_VALID_PROMPT)


# ---------------------------------------------------------------------------
# edit_thumbnail tests
# ---------------------------------------------------------------------------

class TestEditThumbnail:

    @pytest.mark.asyncio
    @patch("app.ai_service._render_image_from_prompt", new_callable=AsyncMock)
    @patch("app.ai_service.save_image_locally", new_callable=AsyncMock)
    @patch("app.ai_service._get_client")
    async def test_returns_expected_dict_shape(self, mock_get_client, mock_save, mock_render):
        """edit_thumbnail should return a dict with all expected keys."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_groq_completion("Edited prompt")
        mock_get_client.return_value = mock_client
        mock_save.return_value = "/fake/outputs/edited_20260915_120000.jpg"
        mock_render.return_value = (_FAKE_IMAGE_BYTES, "image/jpeg")

        from app.ai_service import edit_thumbnail
        result = await edit_thumbnail(_VALID_PROMPT, _FAKE_IMAGE_BYTES)

        assert result["image_base64"] == _FAKE_IMAGE_B64
        assert result["mime_type"] == "image/jpeg"
        assert "saved_path" in result
        assert "Groq" in result["model"]
        assert result["input_image_bytes"] == len(_FAKE_IMAGE_BYTES)

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    async def test_raises_runtime_error_when_no_api_key(self):
        """edit_thumbnail should raise RuntimeError if GROQ_API_KEY is unset."""
        os.environ.pop("GROQ_API_KEY", None)

        from app.ai_service import edit_thumbnail
        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            await edit_thumbnail(_VALID_PROMPT, _FAKE_IMAGE_BYTES)
