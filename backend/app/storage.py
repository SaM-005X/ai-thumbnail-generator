"""
storage.py

Storage abstraction layer for AI Thumbnail Generator (Phase 6).

Supports dual-mode storage:
1. Amazon S3 (production / cloud):
   Uploads generated thumbnails to an S3 bucket and generates secure,
   time-limited Presigned URLs for client viewing and downloading.
2. Local file storage (development fallback):
   If AWS credentials are not configured in .env, saves images to
   `backend/outputs/` without disrupting local development or automated tests.
"""

import os
from typing import Optional
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv(override=True)

# Resolve local outputs directory: backend/app/storage.py -> backend/outputs/
_OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")

# Default presigned URL lifetime: 24 hours (86,400 seconds)
DEFAULT_PRESIGNED_EXPIRATION = 86400


# ---------------------------------------------------------------------------
# S3 Configuration & Client Factory
# ---------------------------------------------------------------------------

def is_s3_configured() -> bool:
    """
    Check whether valid AWS S3 configuration is available.

    Returns:
        True if S3_BUCKET_NAME is set and:
          - Running inside AWS Lambda (uses IAM Execution Role), OR
          - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are provided in .env.
    """
    bucket = os.getenv("S3_BUCKET_NAME", "").strip()
    if not bucket:
        return False

    placeholders = ("your_", "placeholder", "xxx")
    if any(bucket.lower().startswith(p) for p in placeholders):
        return False

    # Inside AWS Lambda, IAM execution role provides credentials automatically
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return True

    access_key = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()

    if not access_key or not secret_key:
        return False

    if any(access_key.lower().startswith(p) for p in placeholders):
        return False
    if any(secret_key.lower().startswith(p) for p in placeholders):
        return False

    return True


def get_s3_client():
    """
    Construct and return a boto3 S3 client.

    Uses IAM execution role credentials when running in AWS Lambda,
    or configured environment variables when running locally.

    Raises:
        RuntimeError: If S3 is not configured.
    """
    if not is_s3_configured():
        raise RuntimeError(
            "AWS S3 is not configured. Please set S3_BUCKET_NAME and "
            "AWS credentials in backend/.env"
        )

    region = os.getenv("AWS_REGION", "ap-south-1")
    config = Config(signature_version="s3v4")

    # If running in AWS Lambda, use IAM Execution Role credentials
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME") or not os.getenv("AWS_ACCESS_KEY_ID"):
        return boto3.client("s3", region_name=region, config=config)

    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=region,
        config=config,
    )



# ---------------------------------------------------------------------------
# S3 Operations
# ---------------------------------------------------------------------------

def upload_to_s3(
    image_bytes: bytes,
    key: str,
    content_type: str = "image/jpeg",
) -> dict:
    """
    Upload raw image bytes directly to the configured S3 bucket.

    Args:
        image_bytes:  Raw binary data of the image.
        key:          Destination object key in S3 (e.g. 'thumbnails/generated_123.jpg').
        content_type: MIME type of the image (e.g. 'image/jpeg', 'image/png').

    Returns:
        Dict with bucket, key, and s3_uri (e.g. 's3://my-bucket/thumbnails/generated_123.jpg').
    """
    client = get_s3_client()
    bucket = os.getenv("S3_BUCKET_NAME")

    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=image_bytes,
        ContentType=content_type,
    )

    return {
        "bucket": bucket,
        "key": key,
        "s3_uri": f"s3://{bucket}/{key}",
    }


def generate_presigned_url(
    key: str,
    expiration: int = DEFAULT_PRESIGNED_EXPIRATION,
) -> str:
    """
    Generate a presigned GET URL granting temporary read access to a private S3 object.

    Args:
        key:        Object key within the S3 bucket.
        expiration: Time in seconds before the presigned URL expires (default: 24h).

    Returns:
        HTTPS URL signed with AWS credentials.
    """
    client = get_s3_client()
    bucket = os.getenv("S3_BUCKET_NAME")

    url = client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiration,
    )
    return url


# ---------------------------------------------------------------------------
# Local Storage Fallback
# ---------------------------------------------------------------------------

async def save_image_locally(image_bytes: bytes, filename: str) -> str:
    """
    Save an image to the local `backend/outputs/` directory.

    Creates the outputs directory automatically if it does not exist.

    Args:
        image_bytes: Raw bytes of the image to save.
        filename:    The filename to save as (e.g. ``generated_20260916_120000.jpg``).

    Returns:
        Normalised absolute file path on the local disk.
    """
    os.makedirs(_OUTPUTS_DIR, exist_ok=True)
    filepath = os.path.normpath(os.path.join(_OUTPUTS_DIR, filename))
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    return filepath


# ---------------------------------------------------------------------------
# Unified Storage Entry Point
# ---------------------------------------------------------------------------

async def save_image(
    image_bytes: bytes,
    filename: str,
    content_type: str = "image/jpeg",
    expiration: int = DEFAULT_PRESIGNED_EXPIRATION,
) -> dict:
    """
    Unified entry point for saving images.

    If S3 is configured, uploads the object to Amazon S3 under `thumbnails/<filename>`
    and returns a presigned URL.
    Otherwise, gracefully falls back to local disk storage in `backend/outputs/`.

    Args:
        image_bytes:  Raw binary image data.
        filename:     Target filename (e.g. 'generated_20260916_183000.jpg').
        content_type: MIME type string.
        expiration:   Seconds until presigned URL expires (if S3 is used).

    Returns:
        Dict containing:
          - storage: 's3' or 'local'
          - saved_path: S3 URI or local filesystem path
          - url: Presigned HTTPS URL (or None if local)
          - s3_key: S3 object key (or None if local)
          - bucket: S3 bucket name (or None if local)
    """
    if is_s3_configured():
        key = f"thumbnails/{filename}"
        upload_to_s3(image_bytes, key, content_type=content_type)
        presigned_url = generate_presigned_url(key, expiration=expiration)
        bucket = os.getenv("S3_BUCKET_NAME")
        return {
            "storage": "s3",
            "saved_path": f"s3://{bucket}/{key}",
            "url": presigned_url,
            "s3_key": key,
            "bucket": bucket,
        }

    # Fallback to local disk storage
    local_path = await save_image_locally(image_bytes, filename)
    return {
        "storage": "local",
        "saved_path": local_path,
        "url": None,
        "s3_key": None,
        "bucket": None,
    }
