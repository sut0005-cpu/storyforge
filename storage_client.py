"""Supabase Storage helpers for Story Forge.

Uses Supabase Storage's HTTP API and the signed-in user's access token.
No service-role key or third-party S3 credentials are required.

Environment overrides:
    SUPABASE_URL       Supabase project URL
    SUPABASE_BUCKET    Storage bucket name (default: storyforge)
    SUPABASE_PUBLISHABLE_KEY  Public/publishable project key
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://cdkisxurtrmaruwnbfjw.supabase.co").rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.getenv(
    "SUPABASE_PUBLISHABLE_KEY", "sb_publishable_nrrtqoy7gIvmiYOZF0Ym3A_7TAWkj9K"
)
DEFAULT_BUCKET = os.getenv("SUPABASE_BUCKET", "storyforge")


def _request(path: str, *, token: str, method: str = "GET", data: bytes | None = None,
             content_type: str | None = None, extra_headers: dict[str, str] | None = None,
             timeout: int = 45) -> bytes:
    if not token:
        raise RuntimeError("Sign in to your Story Forge account before accessing cloud files.")
    headers = {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {token}",
}
    if content_type:
        headers["Content-Type"] = content_type
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(SUPABASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase Storage returned HTTP {exc.code}: {detail[:900]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not reach Supabase Storage: {exc}") from exc


def list_project_files(token: str, bucket: str = DEFAULT_BUCKET, prefix: str = "") -> list[dict[str, Any]]:
    """List objects at a bucket prefix. Returns Supabase object metadata rows."""
    bucket_q = urllib.parse.quote(bucket, safe="")
    payload = json.dumps({"prefix": prefix, "limit": 1000, "offset": 0,
                          "sortBy": {"column": "name", "order": "asc"}}).encode("utf-8")
    raw = _request(f"/storage/v1/object/list/{bucket_q}", token=token, method="POST",
                   data=payload, content_type="application/json")
    result = json.loads(raw.decode("utf-8")) if raw else []
    return result if isinstance(result, list) else []


def upload_project_file(local_path: str | os.PathLike[str], object_key: str,
                        token: str, bucket: str = DEFAULT_BUCKET, upsert: bool = True) -> None:
    path = Path(local_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    key = "/".join(urllib.parse.quote(part, safe="") for part in object_key.strip("/").split("/"))
    bucket_q = urllib.parse.quote(bucket, safe="")
    _request(f"/storage/v1/object/{bucket_q}/{key}", token=token, method="POST",
             data=path.read_bytes(), content_type="application/octet-stream",
             extra_headers={"x-upsert": "true" if upsert else "false"})


def download_project_file(object_key: str, local_path: str | os.PathLike[str],
                          token: str, bucket: str = DEFAULT_BUCKET) -> None:
    key = "/".join(urllib.parse.quote(part, safe="") for part in object_key.strip("/").split("/"))
    bucket_q = urllib.parse.quote(bucket, safe="")
    raw = _request(f"/storage/v1/object/{bucket_q}/{key}", token=token)
    target = Path(local_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)


def delete_project_file(object_key: str, token: str, bucket: str = DEFAULT_BUCKET) -> None:
    """Delete one object from the bucket (subject to Storage policies)."""
    bucket_q = urllib.parse.quote(bucket, safe="")
    payload = json.dumps({"prefixes": [object_key]}).encode("utf-8")
    _request(f"/storage/v1/object/{bucket_q}", token=token, method="DELETE",
             data=payload, content_type="application/json")
