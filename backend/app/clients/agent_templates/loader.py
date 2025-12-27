from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=32)
def load_agent_template(template_name: str) -> str:
    """
    Load an agent instruction template from backend/app/clients/agent_templates/<name>.md
    Cached per-process; restart the backend to pick up template edits.
    """
    name = (template_name or "").strip()
    if not name:
        raise ValueError("template_name is required")
    if "/" in name or "\\" in name:
        raise ValueError("invalid template_name")

    path = Path(__file__).resolve().parent / f"{name}.md"
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"template '{name}' is empty: {path}")
    return content


