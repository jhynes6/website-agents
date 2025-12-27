import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeBaseRecord:
    slug: str
    kb_uuid: str
    region: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    data_sources: list[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slug": self.slug,
            "kb_uuid": self.kb_uuid,
            "region": self.region,
            "tags": self.tags,
            "data_sources": self.data_sources,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class KnowledgeBaseRegistry:
    """
    Lightweight on-disk registry for client KB metadata so callers never guess IDs.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        default_path = Path(__file__).resolve().parent / "do_kb_registry.json"
        self.path = Path(path) if path else default_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, KnowledgeBaseRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text())
            for slug, payload in raw.items():
                self._data[slug] = KnowledgeBaseRecord(
                    slug=slug,
                    kb_uuid=payload.get("kb_uuid", ""),
                    region=payload.get("region"),
                    tags=payload.get("tags") or [],
                    data_sources=payload.get("data_sources") or [],
                    created_at=payload.get("created_at"),
                    updated_at=payload.get("updated_at"),
                )
        except Exception as exc:  # pragma: no cover - defensive logging only
            logger.warning("Failed to load KB registry: %s", exc)

    def _persist(self) -> None:
        serializable = {slug: rec.to_dict() for slug, rec in self._data.items()}
        self.path.write_text(json.dumps(serializable, indent=2, sort_keys=True))

    def upsert(
        self,
        slug: str,
        kb_uuid: str,
        region: Optional[str],
        tags: Optional[list[str]] = None,
        data_sources: Optional[list[Dict[str, Any]]] = None,
        created_at: Optional[str] = None,
    ) -> KnowledgeBaseRecord:
        now = datetime.now(timezone.utc).isoformat()
        record = self._data.get(slug)
        created_ts = created_at or (record.created_at if record else now)
        new_record = KnowledgeBaseRecord(
            slug=slug,
            kb_uuid=kb_uuid,
            region=region,
            tags=tags or [],
            data_sources=data_sources or [],
            created_at=created_ts,
            updated_at=now,
        )
        self._data[slug] = new_record
        self._persist()
        return new_record

    def get(self, slug: str) -> Optional[KnowledgeBaseRecord]:
        return self._data.get(slug)

    def find_by_uuid(self, kb_uuid: str) -> Optional[KnowledgeBaseRecord]:
        for rec in self._data.values():
            if rec.kb_uuid == kb_uuid:
                return rec
        return None

    def all(self) -> Dict[str, KnowledgeBaseRecord]:
        return self._data

