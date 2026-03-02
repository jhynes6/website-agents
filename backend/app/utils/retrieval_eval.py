"""
Retrieval traceability & eval for Pinecone KB retrievals.

Each search call can emit a RetrievalTrace that captures:
- query config: original query, rewritten query, top_k, filters, index, chunker, vector_model, reranker
- timing: latency_ms
- result signals: score distribution, hit count, distinct files, content-type breakdown
- eval label: filled in later via the /eval endpoints

Traces are stored as newline-delimited JSON (JSONL) in backend/eval/retrieval_traces.jsonl.
Use GET /api/mintagent/eval/traces and GET /api/mintagent/eval/stats to inspect them.
"""

from __future__ import annotations

import json
import os
import statistics
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_EVAL_DIR = Path(__file__).parent.parent.parent / "eval"
_TRACES_FILE = _EVAL_DIR / "retrieval_traces.jsonl"

# Vector model used by the current index (Pinecone Integrated Embedding).
# Update this if you switch indexes / models.
_DEFAULT_VECTOR_MODEL = "multilingual-e5-large"


# ---------------------------------------------------------------------------
# Trace dataclass
# ---------------------------------------------------------------------------


@dataclass
class RetrievalTrace:
    # Identifiers
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Query config
    client_slug: str = ""
    query_original: str = ""
    query_rewritten: str = ""         # empty = no rewrite applied
    retrieval_queries: List[str] = field(default_factory=list)  # all queries sent to Pinecone
    top_k: int = 5
    index_name: str = ""
    filter: Dict[str, Any] = field(default_factory=dict)

    # Vector config
    vector_model: str = _DEFAULT_VECTOR_MODEL
    chunker: str = ""                 # e.g. "char:1200:200" or "md_semantic_v1:w350:m550:o80"
    reranker: str = "none"            # "none" | "cohere" | "bm25" | etc.

    # Timing
    latency_ms: float = 0.0           # wall-clock time for all Pinecone calls combined

    # Result quality signals
    hits_total: int = 0               # after merge+dedup
    hits_returned: int = 0
    score_mean: float = 0.0
    score_median: float = 0.0
    score_p90: float = 0.0
    score_min: float = 0.0
    score_max: float = 0.0
    distinct_files: int = 0
    by_content_type: Dict[str, int] = field(default_factory=dict)
    by_document_source: Dict[str, int] = field(default_factory=dict)
    top_hits: List[Dict[str, Any]] = field(default_factory=list)  # up to 5

    # Retrieval mode flags
    case_study_mode: bool = False
    pricing_mode: bool = False
    metadata_filter_mode: bool = False
    query_rewrite_used: bool = False

    # Experiment tagging for A/B comparisons
    experiment_tag: str = ""          # e.g. "char_vs_semantic" | "top_k_ablation"

    # Eval label (filled in later via POST /eval/traces/{trace_id}/label)
    label: Optional[str] = None       # "relevant" | "partial" | "irrelevant"
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Compute stats from raw hits
# ---------------------------------------------------------------------------


def build_trace_from_hits(
    *,
    hits: List[Any],
    client_slug: str,
    query_original: str,
    query_rewritten: str,
    retrieval_queries: List[str],
    top_k: int,
    index_name: str,
    filter: Dict[str, Any],
    latency_ms: float,
    case_study_mode: bool = False,
    pricing_mode: bool = False,
    metadata_filter_mode: bool = False,
    query_rewrite_used: bool = False,
    reranker: str = "none",
    experiment_tag: str = "",
    vector_model: str = _DEFAULT_VECTOR_MODEL,
) -> RetrievalTrace:
    """
    Build a RetrievalTrace from merged Pinecone hits and query context.
    Extracts chunker from the first hit's metadata if available.
    """
    scores: List[float] = []
    distinct_files: set[str] = set()
    by_content_type: Dict[str, int] = {}
    by_document_source: Dict[str, int] = {}
    top_hits: List[Dict[str, Any]] = []
    chunker_seen = ""

    for h in hits:
        try:
            score = float(getattr(h, "score", 0.0) or 0.0)
        except Exception:
            score = 0.0
        scores.append(score)

        f = getattr(h, "fields", {}) or {}
        fk = str(f.get("file_key") or "").strip()
        ct = str(f.get("content_type") or "").strip() or "(none)"
        ds = str(f.get("document_source") or "").strip() or "(none)"

        if fk:
            distinct_files.add(fk)
        by_content_type[ct] = by_content_type.get(ct, 0) + 1
        by_document_source[ds] = by_document_source.get(ds, 0) + 1

        if not chunker_seen:
            chunker_seen = str(f.get("chunker") or "").strip()

        if len(top_hits) < 5:
            top_hits.append(
                {
                    "record_id": str(getattr(h, "record_id", "") or ""),
                    "score": round(score, 6),
                    "file_key": fk,
                    "content_type": ct,
                    "document_source": ds,
                    "chunk_index": f.get("chunk_index"),
                    "title": str(f.get("title") or "")[:80],
                }
            )

    score_mean = statistics.mean(scores) if scores else 0.0
    score_median = statistics.median(scores) if scores else 0.0
    score_p90 = sorted(scores)[int(len(scores) * 0.9)] if len(scores) >= 10 else (max(scores) if scores else 0.0)
    score_min = min(scores) if scores else 0.0
    score_max = max(scores) if scores else 0.0

    return RetrievalTrace(
        client_slug=client_slug,
        query_original=query_original,
        query_rewritten=query_rewritten,
        retrieval_queries=retrieval_queries,
        top_k=top_k,
        index_name=index_name,
        filter=filter,
        vector_model=vector_model,
        chunker=chunker_seen,
        reranker=reranker,
        latency_ms=round(latency_ms, 2),
        hits_total=len(hits),
        hits_returned=len(hits),
        score_mean=round(score_mean, 6),
        score_median=round(score_median, 6),
        score_p90=round(score_p90, 6),
        score_min=round(score_min, 6),
        score_max=round(score_max, 6),
        distinct_files=len(distinct_files),
        by_content_type=by_content_type,
        by_document_source=by_document_source,
        top_hits=top_hits,
        case_study_mode=case_study_mode,
        pricing_mode=pricing_mode,
        metadata_filter_mode=metadata_filter_mode,
        query_rewrite_used=query_rewrite_used,
        experiment_tag=experiment_tag,
    )


# ---------------------------------------------------------------------------
# JSONL persistence
# ---------------------------------------------------------------------------


def _ensure_eval_dir() -> None:
    _EVAL_DIR.mkdir(parents=True, exist_ok=True)


def write_trace(trace: RetrievalTrace) -> None:
    """Append a single trace to the JSONL file. Thread-safe via O_APPEND."""
    _ensure_eval_dir()
    line = json.dumps(trace.to_dict(), ensure_ascii=False)
    with open(_TRACES_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_traces(
    *,
    client_slug: Optional[str] = None,
    experiment_tag: Optional[str] = None,
    label: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Read traces from JSONL, optionally filtering by client/experiment/label."""
    if not _TRACES_FILE.exists():
        return []

    rows: List[Dict[str, Any]] = []
    with open(_TRACES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if client_slug and row.get("client_slug") != client_slug:
                continue
            if experiment_tag and row.get("experiment_tag") != experiment_tag:
                continue
            if label and row.get("label") != label:
                continue
            rows.append(row)

    # Most recent first
    rows.sort(key=lambda r: str(r.get("timestamp") or ""), reverse=True)
    return rows[offset : offset + limit]


def patch_trace_label(
    trace_id: str,
    *,
    label: str,
    notes: Optional[str] = None,
) -> bool:
    """Rewrite the JSONL file with an updated label on the given trace_id."""
    if not _TRACES_FILE.exists():
        return False

    lines: List[str] = []
    found = False
    with open(_TRACES_FILE, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
                if row.get("trace_id") == trace_id:
                    row["label"] = label
                    if notes is not None:
                        row["notes"] = notes
                    raw = json.dumps(row, ensure_ascii=False)
                    found = True
            except Exception:
                pass
            lines.append(raw)

    if found:
        with open(_TRACES_FILE, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
    return found


def clear_traces() -> int:
    """Delete all stored traces. Returns count of deleted records."""
    if not _TRACES_FILE.exists():
        return 0
    with open(_TRACES_FILE, "r", encoding="utf-8") as f:
        count = sum(1 for line in f if line.strip())
    _TRACES_FILE.unlink()
    return count


# ---------------------------------------------------------------------------
# Stats aggregation (group-by any dimension)
# ---------------------------------------------------------------------------

_NUMERIC_FIELDS = (
    "latency_ms",
    "hits_total",
    "score_mean",
    "score_median",
    "score_p90",
    "score_max",
    "distinct_files",
)


def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None


def compute_stats(
    traces: List[Dict[str, Any]],
    *,
    group_by: str = "chunker",
) -> Dict[str, Any]:
    """
    Aggregate traces by a grouping dimension (chunker | vector_model | top_k | reranker | experiment_tag).

    Returns per-group mean/median for latency, hit count, score signals plus label breakdown.
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for t in traces:
        key = str(t.get(group_by) or "(unset)").strip() or "(unset)"
        groups.setdefault(key, []).append(t)

    out: Dict[str, Any] = {"group_by": group_by, "total_traces": len(traces), "groups": {}}

    for key, rows in groups.items():
        n = len(rows)
        numeric: Dict[str, List[float]] = {f: [] for f in _NUMERIC_FIELDS}
        labels: Dict[str, int] = {}

        for r in rows:
            for f in _NUMERIC_FIELDS:
                v = _safe_float(r.get(f))
                if v is not None:
                    numeric[f].append(v)
            lbl = str(r.get("label") or "unlabeled")
            labels[lbl] = labels.get(lbl, 0) + 1

        agg: Dict[str, Any] = {"n": n, "labels": labels}
        for f, vals in numeric.items():
            if not vals:
                continue
            agg[f] = {
                "mean": round(statistics.mean(vals), 3),
                "median": round(statistics.median(vals), 3),
                "min": round(min(vals), 3),
                "max": round(max(vals), 3),
            }

        out["groups"][key] = agg

    return out
