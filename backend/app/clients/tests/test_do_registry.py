import sys
import tempfile
from pathlib import Path

# Ensure backend root is on path when running via pytest from repo root
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.clients.do_kb_registry import KnowledgeBaseRegistry  # noqa: E402


def test_registry_upsert_and_lookup():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = Path(tmpdir) / "registry.json"
        reg = KnowledgeBaseRegistry(reg_path)

        rec = reg.upsert(
            slug="client-a",
            kb_uuid="kb-123",
            region="sfo2",
            tags=["client-docs", "client-a"],
            data_sources=[{"spaces_data_source": {"bucket": "demo"}}],
            created_at="2024-01-01T00:00:00Z",
        )

        assert rec.kb_uuid == "kb-123"
        assert reg.get("client-a").kb_uuid == "kb-123"
        assert reg.find_by_uuid("kb-123").slug == "client-a"

if __name__ == "__main__":
    test_registry_upsert_and_lookup()