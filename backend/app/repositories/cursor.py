"""
summary:
    Opaque cursor encoding/decoding for keyset pagination.

    Why keyset over offset:
    - Offset pagination on a table with N rows costs O(offset). At deep
      pages this becomes the dominant query cost on hot endpoints.
    - Keyset uses (created_at, id) as the cursor and a strict
      WHERE (created_at, id) < (last_created_at, last_id) clause, which
      is index-only on the (tenant_id, created_at, id) index.

    The cursor is base64(JSON) so the client treats it as opaque.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Optional


def encode(created_at: datetime, row_id: str) -> str:
    """
    summary:
        Encode (created_at, id) into a base64 cursor string.
    args:
        created_at: timezone-aware datetime of the last row in the page.
        row_id: id of the last row in the page.
    return:
        URL-safe base64 string.
    """
    raw = json.dumps({"c": created_at.isoformat(), "i": row_id}).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode(cursor: Optional[str]) -> Optional[tuple[datetime, str]]:
    """
    summary:
        Decode a cursor into (created_at, id). Returns None for empty or
        invalid cursors so the caller can fall back to "first page".
    args:
        cursor: opaque cursor string, possibly None.
    return:
        Tuple (created_at, id) or None.
    """
    if not cursor:
        return None
    try:
        pad = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(cursor + pad).decode()
        data = json.loads(raw)
        return datetime.fromisoformat(data["c"]), data["i"]
    except Exception:  # noqa: BLE001
        return None
