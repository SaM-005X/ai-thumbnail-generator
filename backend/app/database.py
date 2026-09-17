"""
database.py

Supabase PostgreSQL integration for persisting and retrieving
generation history.

This module uses the `service_role` key for writes (trusted server-side
operations) and the `anon` key for reads (row-level security compatible).

Table: generation_history
  id          - auto-incrementing PK
  created_at  - UTC timestamp of generation
  prompt      - the original user prompt
  mode        - 'generate' | 'edit'
  image_b64   - base64-encoded image data
  mime_type   - e.g. 'image/jpeg'
  model       - model name string
  saved_path  - local file path (None in cloud deployments)
"""

import os
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_TABLE = "generation_history"

# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def _get_client(use_service_role: bool = False) -> Client:
    """
    Return a Supabase client.

    Args:
        use_service_role: If True, uses the SUPABASE_SERVICE_KEY (for writes).
                          If False, uses the SUPABASE_KEY (anon, for reads).

    Raises:
        RuntimeError: If required environment variables are missing.
    """
    url = os.getenv("SUPABASE_URL")
    if not url:
        raise RuntimeError("SUPABASE_URL is not set in backend/.env")

    if use_service_role:
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not key:
            raise RuntimeError("SUPABASE_SERVICE_KEY is not set in backend/.env")
    else:
        key = os.getenv("SUPABASE_KEY")
        if not key:
            raise RuntimeError("SUPABASE_KEY is not set in backend/.env")

    return create_client(url, key)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def save_generation(
    *,
    prompt: str,
    mode: str,
    image_b64: str,
    mime_type: str,
    model: str,
    saved_path: Optional[str] = None,
) -> dict:
    """
    Insert a new generation record into the ``generation_history`` table.

    Uses the service_role key so it can bypass Row-Level Security policies
    on server-side writes.

    Args:
        prompt:     The original user prompt.
        mode:       'generate' or 'edit'.
        image_b64:  Base64-encoded image string.
        mime_type:  MIME type of the image (e.g. 'image/jpeg').
        model:      The model identifier string.
        saved_path: Optional local file path where the image was saved.

    Returns:
        The inserted row as a dict.

    Raises:
        RuntimeError: If Supabase credentials are missing.
        Exception:    On any database error.
    """
    client = _get_client(use_service_role=True)
    row = {
        "prompt": prompt,
        "mode": mode,
        "image_b64": image_b64,
        "mime_type": mime_type,
        "model": model,
        "saved_path": saved_path,
    }
    response = client.table(_TABLE).insert(row).execute()
    data = response.data
    return data[0] if data else {}


async def get_history(limit: int = 20) -> list[dict]:
    """
    Retrieve the most recent generation records.

    Args:
        limit: Maximum number of records to return (default 20).

    Returns:
        A list of dicts, each representing a generation_history row.
        Ordered by ``created_at`` descending (newest first).

    Raises:
        RuntimeError: If Supabase credentials are missing.
        Exception:    On any database error.
    """
    client = _get_client(use_service_role=False)
    response = (
        client.table(_TABLE)
        .select("id, created_at, prompt, mode, image_b64, mime_type, model")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


async def delete_generation(item_id: int) -> bool:
    """
    Delete a single generation record by its primary key ID.

    Args:
        item_id: The ID of the record to delete.

    Returns:
        True if the record was deleted, False otherwise.
    """
    client = _get_client(use_service_role=True)
    response = client.table(_TABLE).delete().eq("id", item_id).execute()
    return bool(response.data)


async def clear_all_history() -> int:
    """
    Delete all generation history records from Supabase.

    Returns:
        The count of records deleted.
    """
    client = _get_client(use_service_role=True)
    response = client.table(_TABLE).delete().gt("id", 0).execute()
    return len(response.data) if response.data else 0
