from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx  # type: ignore[import-not-found]

from ..config import get_settings


class SupabaseAgentsDbClient:
    """
    Minimal PostgREST client for the mintleads-agents Supabase project.

    Uses SUPABASE_AGENT_URL + SUPABASE_AGENT_SERVICE_ROLE_KEY (preferred) to bypass RLS.
    """

    def __init__(self, *, project_url: Optional[str] = None, service_role_key: Optional[str] = None) -> None:
        s = get_settings()
        self.project_url = str(project_url or s.supabase_agent_url or s.supabase_url or "").rstrip("/")
        self.key = (
            (service_role_key or "").strip()
            or str(s.supabase_agent_service_role_key or "").strip()
            or str(s.supabase_service_role_key or "").strip()
            or str(s.supabase_agent_key or "").strip()
        )
        if not self.project_url:
            raise ValueError("SUPABASE_AGENT_URL not configured")
        if not self.key:
            raise ValueError("SUPABASE_AGENT_SERVICE_ROLE_KEY not configured (required for RLS tables)")
        self.rest_base = f"{self.project_url}/rest/v1"

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def _count_from_content_range(content_range: Optional[str]) -> Optional[int]:
        """
        Parse total count from a PostgREST Content-Range header like:
          "0-0/12" or "*/0"
        """
        cr = (content_range or "").strip()
        if "/" not in cr:
            return None
        total = cr.split("/", 1)[-1].strip()
        try:
            return int(total)
        except Exception:
            return None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def upsert_client(
        self,
        *,
        client_slug: str,
        client_domain: str,
        client_name: Optional[str] = None,
        website: Optional[str] = None,
        drive_folder_url: Optional[str] = None,
        intake_form_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        slug = (client_slug or "").strip()
        domain = (client_domain or "").strip()
        if not slug:
            raise ValueError("client_slug required")
        if not domain:
            raise ValueError("client_domain required")

        url = f"{self.rest_base}/clients?on_conflict={quote('client_slug')}"
        payload: Dict[str, Any] = {
            "client_slug": slug,
            "client_domain": domain,
            "last_updated": self._now_iso(),
        }
        if client_name is not None:
            payload["client_name"] = (client_name or "").strip() or None
        if website is not None:
            payload["website"] = (website or "").strip() or None
        if drive_folder_url is not None:
            payload["drive_folder_url"] = (drive_folder_url or "").strip() or None
        if intake_form_url is not None:
            payload["intake_form_url"] = (intake_form_url or "").strip() or None

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                headers={**self._headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
                json=[payload],
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Supabase clients upsert error {resp.status_code}: {resp.text}")
            data = resp.json()
            return data[0] if isinstance(data, list) and data else {"ok": True}

    async def upsert_documents(self, *, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Upsert documents by doc_id.
        Expects each doc dict to contain at least: doc_id.
        """
        if not docs:
            return {"upserted": 0}
        url = f"{self.rest_base}/documents?on_conflict={quote('doc_id')}"

        # Ensure timestamps
        now = self._now_iso()
        payload = []
        for d in docs:
            if not isinstance(d, dict):
                continue
            doc_id = (d.get("doc_id") or "").strip()
            if not doc_id:
                continue
            row = {**d}
            row.setdefault("updated_at", now)
            payload.append(row)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                headers={**self._headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
                json=payload,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Supabase documents upsert error {resp.status_code}: {resp.text}")
            return {"upserted": len(payload)}

    async def set_documents_status(self, *, doc_ids: List[str], status: str) -> Dict[str, Any]:
        ids = [i.strip() for i in (doc_ids or []) if isinstance(i, str) and i.strip()]
        if not ids:
            return {"updated": 0}

        # PostgREST IN filter: doc_id=in.(a,b,c)
        in_list = ",".join(ids)
        url = f"{self.rest_base}/documents?doc_id=in.({quote(in_list, safe=',')})"
        body = {"ingestion_status": status, "updated_at": self._now_iso()}

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.patch(
                url,
                headers={**self._headers(), "Prefer": "return=minimal"},
                json=body,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Supabase documents update error {resp.status_code}: {resp.text}")
            return {"updated": len(ids)}

    async def delete_documents_for_client(self, *, client_slug: str) -> Dict[str, Any]:
        """
        Delete all rows in public.documents for a client.
        Returns best-effort count (from Content-Range when available).
        """
        slug = (client_slug or "").strip()
        if not slug:
            raise ValueError("client_slug required")
        url = f"{self.rest_base}/documents?client_slug=eq.{quote(slug)}"
        headers = {**self._headers(), "Prefer": "count=exact,return=minimal"}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.delete(url, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase documents delete error {resp.status_code}: {resp.text}")
        count = self._count_from_content_range(resp.headers.get("content-range"))
        return {"deleted": count if count is not None else True}

    async def delete_client(self, *, client_slug: str) -> Dict[str, Any]:
        """
        Delete a row in public.clients for a client_slug.
        Returns best-effort count (from Content-Range when available).
        """
        slug = (client_slug or "").strip()
        if not slug:
            raise ValueError("client_slug required")
        url = f"{self.rest_base}/clients?client_slug=eq.{quote(slug)}"
        headers = {**self._headers(), "Prefer": "count=exact,return=minimal"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(url, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase clients delete error {resp.status_code}: {resp.text}")
        count = self._count_from_content_range(resp.headers.get("content-range"))
        return {"deleted": count if count is not None else True}

    async def get_client_names_map(self, *, client_slugs: List[str]) -> Dict[str, str]:
        """
        Fetch client_name values for a set of slugs.
        Returns: {client_slug: client_name}
        """
        slugs = [s.strip() for s in (client_slugs or []) if isinstance(s, str) and s.strip()]
        slugs = sorted(set(slugs))
        if not slugs:
            return {}

        # PostgREST IN filter: client_slug=in.(a,b,c)
        in_list = ",".join(slugs)
        url = f"{self.rest_base}/clients?select=client_slug,client_name&client_slug=in.({quote(in_list, safe=',')})"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers={**self._headers(), "Prefer": "count=none"})
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase clients select error {resp.status_code}: {resp.text}")
        data = resp.json()
        out: Dict[str, str] = {}
        if isinstance(data, list):
            for row in data:
                if not isinstance(row, dict):
                    continue
                slug = str(row.get("client_slug") or "").strip()
                name = row.get("client_name")
                if slug and isinstance(name, str) and name.strip():
                    out[slug] = name.strip()
        return out


