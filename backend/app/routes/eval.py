"""
Retrieval eval endpoints.

GET  /api/mintagent/eval/traces        - list traces with optional filters
GET  /api/mintagent/eval/stats         - aggregated stats grouped by a dimension
POST /api/mintagent/eval/traces/{id}/label  - label a trace (relevant/partial/irrelevant)
DELETE /api/mintagent/eval/traces      - clear all traces (dev use)
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ..utils.retrieval_eval import (
    clear_traces,
    compute_stats,
    patch_trace_label,
    read_traces,
)

router = APIRouter()

_VALID_GROUP_BY = {"chunker", "vector_model", "top_k", "reranker", "experiment_tag", "client_slug"}
_VALID_LABELS = {"relevant", "partial", "irrelevant"}


@router.get("/eval/traces")
async def list_traces(
    client_slug: Optional[str] = Query(None, description="Filter by client slug"),
    experiment_tag: Optional[str] = Query(None, description="Filter by experiment tag"),
    label: Optional[str] = Query(None, description="Filter by eval label"),
    limit: int = Query(100, ge=1, le=1000, description="Max traces to return"),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    traces = read_traces(
        client_slug=client_slug,
        experiment_tag=experiment_tag,
        label=label,
        limit=limit,
        offset=offset,
    )
    return JSONResponse({"traces": traces, "count": len(traces)})


@router.get("/eval/stats")
async def get_stats(
    client_slug: Optional[str] = Query(None),
    experiment_tag: Optional[str] = Query(None),
    group_by: str = Query("chunker", description=f"Group dimension: {_VALID_GROUP_BY}"),
    limit: int = Query(2000, ge=1, le=10000),
) -> JSONResponse:
    if group_by not in _VALID_GROUP_BY:
        raise HTTPException(
            status_code=400,
            detail=f"group_by must be one of: {sorted(_VALID_GROUP_BY)}",
        )
    traces = read_traces(
        client_slug=client_slug,
        experiment_tag=experiment_tag,
        limit=limit,
    )
    stats = compute_stats(traces, group_by=group_by)
    return JSONResponse(stats)


@router.post("/eval/traces/{trace_id}/label")
async def label_trace(trace_id: str, payload: Dict[str, Any]) -> JSONResponse:
    label = str(payload.get("label") or "").strip().lower()
    notes = payload.get("notes")

    if label not in _VALID_LABELS:
        raise HTTPException(
            status_code=400,
            detail=f"label must be one of: {sorted(_VALID_LABELS)}",
        )

    found = patch_trace_label(trace_id, label=label, notes=notes)
    if not found:
        raise HTTPException(status_code=404, detail=f"trace_id '{trace_id}' not found")

    return JSONResponse({"ok": True, "trace_id": trace_id, "label": label})


@router.delete("/eval/traces")
async def delete_traces() -> JSONResponse:
    count = clear_traces()
    return JSONResponse({"ok": True, "deleted": count})
