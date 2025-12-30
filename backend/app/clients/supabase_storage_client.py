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


@dataclass(frozen=True)
class UploadResult:
    key: str
    raw: Dict[str, Any]


class SupabaseStorageClient:
    """
    Minimal Supabase Storage API client (server-side, service-role).

    Uses the Storage API OpenAPI spec (see https://supabase.github.io/storage/api.json).
    Base URL is `${SUPABASE_URL}/storage/v1`.
    """

    def __init__(self, *, project_url: Optional[str] = None, service_role_key: Optional[str] = None) -> None:
        s = get_settings()
        self.project_url = (project_url or str(s.supabase_url or "")).rstrip("/")
        self.service_role_key = service_role_key or (s.supabase_service_role_key or "")
        if not self.project_url:
            raise ValueError("SUPABASE_URL not configured")
        if not self.service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY not configured (required for Storage admin operations)")
        self.base_url = f"{self.project_url}/storage/v1"

    def _headers(self) -> Dict[str, str]:
        key = self.service_role_key
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
        }

    def list_buckets(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/bucket"
        resp = httpx.get(url, headers=self._headers(), timeout=30)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase Storage list buckets error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data if isinstance(data, list) else []

    def bucket_exists(self, bucket_id: str) -> bool:
        bid = (bucket_id or "").strip()
        if not bid:
            return False
        url = f"{self.base_url}/bucket/{quote(bid)}"
        resp = httpx.get(url, headers=self._headers(), timeout=30)
        if resp.status_code == 200:
            return True
        if resp.status_code in (400, 404):
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

    def empty_bucket(self, bucket_id: str) -> Dict[str, Any]:
        """
        Remove all objects inside a bucket (Storage API).

        Supabase docs: a bucket cannot be deleted if it still has objects; empty it first.
        """
        bid = (bucket_id or "").strip()
        if not bid:
            raise ValueError("bucket_id required")
        url = f"{self.base_url}/bucket/{quote(bid)}/empty"
        resp = httpx.post(url, headers=self._headers(), timeout=120)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase Storage empty bucket error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data if isinstance(data, dict) else {"raw": data}

    def delete_bucket(self, bucket_id: str) -> Dict[str, Any]:
        """
        Delete a bucket (must be empty first).
        """
        bid = (bucket_id or "").strip()
        if not bid:
            raise ValueError("bucket_id required")
        url = f"{self.base_url}/bucket/{quote(bid)}"
        resp = httpx.delete(url, headers=self._headers(), timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase Storage delete bucket error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data if isinstance(data, dict) else {"raw": data}

    def ensure_bucket(self, bucket_id: str, *, public: bool = True) -> None:
        if self.bucket_exists(bucket_id):
            return
        self.create_bucket(bucket_id, public=public)

    def object_exists(self, bucket: str, path: str) -> bool:
        b = (bucket or "").strip()
        p = (path or "").lstrip("/")
        if not b or not p:
            return False
        # IMPORTANT: object paths are a wildcard and may contain '/', so do not encode slashes.
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
    ) -> UploadResult:
        """
        Upload a new object (POST /object/{bucketName}/{wildcard}).
        """
        b = (bucket or "").strip()
        p = (path or "").lstrip("/")
        if not b:
            raise ValueError("bucket required")
        if not p:
            raise ValueError("path required")

        # IMPORTANT: object paths are a wildcard and may contain '/', so do not encode slashes.
        url = f"{self.base_url}/object/{quote(b)}/{quote(p, safe='/')}"
        headers = {
            **self._headers(),
            "Content-Type": content_type,
        }
        resp = httpx.post(url, headers=headers, content=data, timeout=120)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase Storage upload error {resp.status_code}: {resp.text}")
        raw = resp.json()
        key = ""
        if isinstance(raw, dict):
            key = str(raw.get("Key") or raw.get("key") or "")
        return UploadResult(key=key or f"{b}/{p}", raw=raw if isinstance(raw, dict) else {"raw": raw})

    def upload_json(self, *, bucket: str, path: str, payload: Any) -> UploadResult:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        return self.upload_bytes(bucket=bucket, path=path, data=data, content_type="application/json; charset=utf-8")

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

        Note: This is paginated via limit/offset.
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

    def delete_objects(self, bucket: str, paths: List[str]) -> Dict[str, Any]:
        """
        Delete specific objects by path list.
        """
        b = (bucket or "").strip()
        if not b:
            raise ValueError("bucket required")
        if not paths:
            return {"status": "skipped", "message": "no paths provided"}
        url = f"{self.base_url}/object/{quote(b)}"
        resp = httpx.delete(
            url,
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"paths": paths},
            timeout=120,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase Storage delete objects error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data if isinstance(data, dict) else {"raw": data}

    def ensure_prefixes(self, bucket: str, prefixes: List[str]) -> None:
        """
        Supabase Storage "folders" are just prefixes. We materialize them by creating `.keep` objects.
        """
        for pref in prefixes:
            p = (pref or "").strip().strip("/")
            if not p:
                continue
            keep_path = f"{p}/.keep"
            if self.object_exists(bucket, keep_path):
                continue
            self.upload_bytes(bucket=bucket, path=keep_path, data=b"\n", content_type="text/plain; charset=utf-8")

    @staticmethod
    def safe_key_for_url(url: str, *, prefix: str = "pages", ext: str = "md") -> str:
        u = (url or "").strip()
        h = _sha1_hex(u)[:16]
        return f"{prefix}/{h}.{ext.lstrip('.')}"


