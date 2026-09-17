"""
test_storage.py

Unit tests for Phase 6 storage module (Amazon S3 + Local Fallback).

Uses unittest.mock to mock boto3 S3 client so tests do not require real AWS credentials.
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from app.storage import (
    is_s3_configured,
    get_s3_client,
    upload_to_s3,
    generate_presigned_url,
    save_image,
    save_image_locally,
)

_SAMPLE_BYTES = b"sample-thumbnail-image-bytes-phase6"
_SAMPLE_FILENAME = "test_thumbnail_20260916.jpg"


# ---------------------------------------------------------------------------
# S3 Configuration Tests
# ---------------------------------------------------------------------------

class TestS3Configuration:

    @patch.dict(os.environ, {}, clear=True)
    def test_is_s3_configured_returns_false_when_unset(self):
        """Should return False if AWS environment variables are missing."""
        assert is_s3_configured() is False

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "your_aws_access_key_id",
            "AWS_SECRET_ACCESS_KEY": "your_aws_secret_access_key",
            "S3_BUCKET_NAME": "your_s3_bucket_name",
        },
        clear=True,
    )
    def test_is_s3_configured_returns_false_for_placeholder_values(self):
        """Should return False if environment variables still contain placeholder text."""
        assert is_s3_configured() is False

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "S3_BUCKET_NAME": "my-thumbnails-bucket",
        },
        clear=True,
    )
    def test_is_s3_configured_returns_true_when_valid(self):
        """Should return True when all required credentials are set and non-placeholder."""
        assert is_s3_configured() is True

    @patch.dict(os.environ, {}, clear=True)
    def test_get_s3_client_raises_when_unconfigured(self):
        """get_s3_client should raise RuntimeError when S3 is not configured."""
        with pytest.raises(RuntimeError, match="AWS S3 is not configured"):
            get_s3_client()


# ---------------------------------------------------------------------------
# Local Storage Fallback Tests
# ---------------------------------------------------------------------------

class TestLocalStorage:

    @pytest.mark.asyncio
    async def test_save_image_locally_writes_file(self, tmp_path):
        """save_image_locally should write bytes to disk and return the path."""
        with patch("app.storage._OUTPUTS_DIR", str(tmp_path)):
            saved_path = await save_image_locally(_SAMPLE_BYTES, _SAMPLE_FILENAME)

            assert os.path.exists(saved_path)
            with open(saved_path, "rb") as f:
                content = f.read()
            assert content == _SAMPLE_BYTES

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    async def test_save_image_falls_back_to_local(self, tmp_path):
        """When S3 is unconfigured, save_image should fall back to local disk storage."""
        with patch("app.storage._OUTPUTS_DIR", str(tmp_path)):
            result = await save_image(_SAMPLE_BYTES, _SAMPLE_FILENAME)

            assert result["storage"] == "local"
            assert result["url"] is None
            assert result["s3_key"] is None
            assert os.path.exists(result["saved_path"])


# ---------------------------------------------------------------------------
# Amazon S3 Storage Operations Tests (Mocked)
# ---------------------------------------------------------------------------

class TestS3StorageOperations:

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "S3_BUCKET_NAME": "my-thumbnails-bucket",
            "AWS_REGION": "us-east-1",
        },
        clear=True,
    )
    @patch("app.storage.get_s3_client")
    def test_upload_to_s3_calls_put_object(self, mock_get_client):
        """upload_to_s3 should invoke boto3 put_object with correct parameters."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        res = upload_to_s3(_SAMPLE_BYTES, "thumbnails/test.jpg", "image/jpeg")

        mock_client.put_object.assert_called_once_with(
            Bucket="my-thumbnails-bucket",
            Key="thumbnails/test.jpg",
            Body=_SAMPLE_BYTES,
            ContentType="image/jpeg",
        )
        assert res["bucket"] == "my-thumbnails-bucket"
        assert res["key"] == "thumbnails/test.jpg"
        assert res["s3_uri"] == "s3://my-thumbnails-bucket/thumbnails/test.jpg"

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "S3_BUCKET_NAME": "my-thumbnails-bucket",
            "AWS_REGION": "us-east-1",
        },
        clear=True,
    )
    @patch("app.storage.get_s3_client")
    def test_generate_presigned_url_calls_boto3(self, mock_get_client):
        """generate_presigned_url should call boto3 client's generate_presigned_url."""
        mock_client = MagicMock()
        fake_url = "https://my-thumbnails-bucket.s3.amazonaws.com/thumbnails/test.jpg?AWSAccessKeyId=123"
        mock_client.generate_presigned_url.return_value = fake_url
        mock_get_client.return_value = mock_client

        url = generate_presigned_url("thumbnails/test.jpg", expiration=3600)

        assert url == fake_url
        mock_client.generate_presigned_url.assert_called_once_with(
            ClientMethod="get_object",
            Params={"Bucket": "my-thumbnails-bucket", "Key": "thumbnails/test.jpg"},
            ExpiresIn=3600,
        )

    @pytest.mark.asyncio
    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "S3_BUCKET_NAME": "my-thumbnails-bucket",
            "AWS_REGION": "us-east-1",
        },
        clear=True,
    )
    @patch("app.storage.generate_presigned_url")
    @patch("app.storage.upload_to_s3")
    async def test_save_image_uses_s3_when_configured(self, mock_upload, mock_presign):
        """save_image should upload to S3 and return presigned URL when S3 is configured."""
        fake_url = "https://s3.amazonaws.com/my-thumbnails-bucket/thumbnails/test.jpg?sig=xyz"
        mock_presign.return_value = fake_url

        result = await save_image(_SAMPLE_BYTES, _SAMPLE_FILENAME, content_type="image/jpeg")

        mock_upload.assert_called_once_with(
            _SAMPLE_BYTES,
            f"thumbnails/{_SAMPLE_FILENAME}",
            content_type="image/jpeg",
        )
        mock_presign.assert_called_once_with(f"thumbnails/{_SAMPLE_FILENAME}", expiration=86400)
        assert result["storage"] == "s3"
        assert result["url"] == fake_url
        assert result["saved_path"] == f"s3://my-thumbnails-bucket/thumbnails/{_SAMPLE_FILENAME}"
        assert result["s3_key"] == f"thumbnails/{_SAMPLE_FILENAME}"
