from typing import Any, Dict, List, Optional

from upstash_search import Search

from ..config import get_settings
from ..logging import log


class UpstashSearchClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.default_index = self.settings.upstash_search_index

    def _client(self) -> Search:
        return Search(
            url=str(self.settings.upstash_search_rest_url),
            token=self.settings.upstash_search_rest_token,
        )

    def _index(self, index_name: Optional[str] = None):
        return self._client().index(index_name or self.default_index)

    def _normalize_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            doc_id = doc.get("id")
            if not doc_id:
                continue

            content_raw = doc.get("content")
            content_in = content_raw if isinstance(content_raw, dict) else {}
            metadata_raw = doc.get("metadata")
            metadata = metadata_raw.copy() if isinstance(metadata_raw, dict) else {}

            # Derive text
            text = ""
            if isinstance(doc.get("text"), str):
                text = doc.get("text") or ""
            if not text and isinstance(content_in.get("text"), str):
                text = content_in.get("text") or ""
            if not text and isinstance(metadata.get("fullContent"), str):
                text = metadata.get("fullContent", "")[:2000]

            # Build content payload expected by Upstash Search
            content_out = {
                "text": text,
                "url": content_in.get("url") or metadata.get("url"),
                "title": content_in.get("title") or metadata.get("title"),
                "description": content_in.get("description") or metadata.get("description"),
            }

            # Keep other metadata fields
            normalized.append(
                {
                    "id": doc_id,
                    "content": content_out,
                    "metadata": metadata,
                }
            )
        return normalized

    async def upsert_documents(self, documents: List[Dict[str, Any]], index_name: Optional[str] = None) -> None:
        index = index_name or self.default_index
        norm_docs = self._normalize_documents(documents)
        log("upstash.upsert.start", {"index": index, "docs": len(norm_docs), "sample": norm_docs[:1]})
        if not norm_docs:
            log("upstash.upsert.skip", {"index": index, "reason": "no valid documents"})
            return
        try:
            import os
            url = os.environ.get("UPSTASH_SEARCH_REST_URL", "https://assuring-stingray-92074-gcp-usc1-search.upstash.io")
            token = os.environ.get("UPSTASH_SEARCH_REST_TOKEN", "ACAFMGFzc3VyaW5nLXN0aW5ncmF5LTkyMDc0LWdjcC11c2MxYWRtaW5ZVGt5WXpCbU5qY3RNamRtT0MwME1XTTBMV0k1T1RrdFpUY3pNR05pTWpjM01qZzM=")
            test_client = Search(url=url, token=token)
            test_index = test_client.index(index)
            test_index.upsert(documents=norm_docs)
            log("upstash.upsert.success", {"docs": len(norm_docs), "index": index})
            # Optional lightweight verification: try a tiny search on namespace if present
            try:
                ns = norm_docs[0].get("metadata", {}).get("namespace") if norm_docs else None
                if ns:
                    res = self._index(index).search(query=ns, limit=1, filter=f"metadata.namespace = '{ns}'")
                    log("upstash.upsert.verify", {"index": index, "namespace": ns, "hits": len(res) if isinstance(res, list) else None})
            except Exception:
                # Ignore verification errors
                pass
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            log("upstash.upsert.error", {"index": index, "error": msg})
            # Tolerate empty-body JSON decode issues the SDK sometimes emits
            if "Expecting value" in msg or "JSONDecodeError" in msg:
                log("upstash.upsert", {"docs": len(norm_docs), "index": index, "note": "ignored empty body"})
                return
            # Swallow errors to avoid breaking the app; surface via logs
            return

    async def search(
        self,
        query: str,
        limit: int,
        filter_expr: Optional[str] = None,
        reranking: bool = True,
        index_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"query": query, "limit": limit, "reranking": reranking}
        if filter_expr:
            params["filter"] = filter_expr
        result = self._index(index_name).search(**params)
        return result if isinstance(result, list) else result.get("results", [])


upstash_search_client = UpstashSearchClient()

