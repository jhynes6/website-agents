"""
Supabase Storage client for the Agents project (SUPABASE_AGENT_* env vars).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from ..config import get_settings


def _sha1_hex(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8"), usedforsecurity=False).hexdigest()

def _looks_like_jwt(token: str) -> bool:
    """
    Supabase "legacy" anon/service_role keys are JWTs (3 segments separated by '.').
    Newer publishable keys (e.g. sb_publishable_* / sbp_v0_*) are NOT JWTs and will
    fail against endpoints that expect a compact JWS.
    """
    t = (token or "").strip()
    parts = t.split(".")
    return len(parts) == 3 and all(p.strip() for p in parts)


@dataclass(frozen=True)
class UploadResult:
    key: str
    raw: Dict[str, Any]


class SupabaseAgentStorageClient:
    """
    Supabase Storage API client for the Agents project.
    
    Uses SUPABASE_AGENT_URL and SUPABASE_AGENT_KEY environment variables.
    Base URL is `${SUPABASE_AGENT_URL}/storage/v1`.
    """

    def __init__(self, *, project_url: Optional[str] = None, api_key: Optional[str] = None) -> None:
        s = get_settings()
        self.project_url = (project_url or str(s.supabase_agent_url or "")).rstrip("/")
        # Prefer service-role key for server-side Storage operations.
        # Fall back to SUPABASE_AGENT_KEY for backwards compatibility.
        self.api_key = (
            api_key
            or (s.supabase_agent_service_role_key or "")
            or (s.supabase_agent_key or "")
        )
        if not self.project_url:
            raise ValueError("SUPABASE_AGENT_URL not configured")
        if not self.api_key:
            raise ValueError(
                "Supabase key not configured. Set SUPABASE_AGENT_SERVICE_ROLE_KEY (preferred) "
                "or SUPABASE_AGENT_KEY (legacy JWT anon/service_role)."
            )
        # Fail fast with a clearer error if someone accidentally provides a non-JWT publishable key.
        if not _looks_like_jwt(self.api_key):
            raise ValueError(
                "Supabase Storage requires a JWT key (legacy anon/service_role). "
                "Your configured key does not look like a compact JWS. "
                "Set SUPABASE_AGENT_SERVICE_ROLE_KEY (preferred) or SUPABASE_AGENT_KEY to a JWT."
            )
        self.base_url = f"{self.project_url}/storage/v1"

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
        }

    def list_buckets(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/bucket"
        resp = httpx.get(url, headers=self._headers(), timeout=30)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase Storage list buckets error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data if isinstance(data, list) else []

    def bucket_exists(self, bucket_id: str) -> bool:
        """
        Check if a bucket exists.
        
        Note: This may return False due to RLS policies even if the bucket exists.
        Use ensure_bucket() which handles this gracefully.
        """
        bid = (bucket_id or "").strip()
        if not bid:
            return False
        url = f"{self.base_url}/bucket/{quote(bid)}"
        resp = httpx.get(url, headers=self._headers(), timeout=30)
        if resp.status_code == 200:
            return True
        if resp.status_code in (400, 404, 403):  # 403 = RLS policy blocks read
            return False
        raise RuntimeError(f"Supabase Storage get bucket error {resp.status_code}: {resp.text}")

    def create_bucket(self, bucket_id: str, *, public: bool = True) -> Dict[str, Any]:
        bid = (bucket_id or "").strip()
        if not bid:
            raise ValueError("bucket_id required")
        url = f"{self.base_url}/bucket"
        payload = {"id": bid, "name": bid, "public": bool(public)}
        resp = httpx.post(url, headers={**self._headers(), "Content-Type": "application/json"}, json=payload, timeout=30)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase Storage create bucket error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data if isinstance(data, dict) else {"raw": data}

    def ensure_bucket(self, bucket_id: str, *, public: bool = False) -> bool:
        """
        Ensure a bucket exists, creating it if necessary.
        
        Returns True if bucket was verified/created successfully, False if uncertain.
        
        Note: Due to RLS policies, we may not be able to verify bucket existence.
        This attempts to create the bucket and treats "already exists" errors as success.
        """
        # Try to check if bucket exists (may fail due to RLS)
        try:
            if self.bucket_exists(bucket_id):
                return True
        except Exception:
            pass  # RLS may block read access, continue to attempt creation
        
        # Try to create bucket
        try:
            self.create_bucket(bucket_id, public=public)
            return True
        except RuntimeError as e:
            error_text = str(e).lower()
            # If bucket already exists, that's fine
            if "already exists" in error_text or "duplicate" in error_text:
                return True
            # If RLS blocks creation, bucket might still exist - assume success
            if "row-level security" in error_text or "unauthorized" in error_text:
                # Bucket might exist but we can't verify. Uploads will tell us.
                return False
            raise

    def object_exists(self, bucket: str, path: str) -> bool:
        b = (bucket or "").strip()
        p = (path or "").lstrip("/")
        if not b or not p:
            return False
        url = f"{self.base_url}/object/info/authenticated/{quote(b)}/{quote(p, safe='/')}"
        resp = httpx.get(url, headers=self._headers(), timeout=30)
        if resp.status_code == 200:
            return True
        if resp.status_code in (400, 404):
            return False
        raise RuntimeError(f"Supabase Storage object info error {resp.status_code}: {resp.text}")

    def upload_bytes(
        self,
        *,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        upsert: bool = False,
    ) -> UploadResult:
        """
        Upload a new object (POST /object/{bucketName}/{wildcard}).
        Set upsert=True to overwrite existing files.
        """
        b = (bucket or "").strip()
        p = (path or "").lstrip("/")
        if not b:
            raise ValueError("bucket required")
        if not p:
            raise ValueError("path required")

        url = f"{self.base_url}/object/{quote(b)}/{quote(p, safe='/')}"
        headers = {
            **self._headers(),
            "Content-Type": content_type,
        }
        
        # Use upsert header if requested
        if upsert:
            headers["x-upsert"] = "true"
        
        resp = httpx.post(url, headers=headers, content=data, timeout=120)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase Storage upload error {resp.status_code}: {resp.text}")
        raw = resp.json()
        key = ""
        if isinstance(raw, dict):
            key = str(raw.get("Key") or raw.get("key") or "")
        return UploadResult(key=key or f"{b}/{p}", raw=raw if isinstance(raw, dict) else {"raw": raw})

    def upload_json(self, *, bucket: str, path: str, payload: Any, upsert: bool = False) -> UploadResult:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        return self.upload_bytes(bucket=bucket, path=path, data=data, content_type="application/json; charset=utf-8", upsert=upsert)

    def list_objects(
        self,
        bucket: str,
        *,
        prefix: str = "",
        limit: int = 1000,
        offset: int = 0,
        sort_by: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List objects in a bucket using the Storage API list endpoint.
        """
        b = (bucket or "").strip()
        if not b:
            raise ValueError("bucket required")

        url = f"{self.base_url}/object/list/{quote(b)}"
        body: Dict[str, Any] = {
            "prefix": prefix,
            "limit": limit,
            "offset": offset,
        }
        if sort_by:
            body["sortBy"] = sort_by
        resp = httpx.post(url, headers={**self._headers(), "Content-Type": "application/json"}, json=body, timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase Storage list objects error {resp.status_code}: {resp.text}")
        data = resp.json()
        items = data.get("items") if isinstance(data, dict) else None
        return items or []

