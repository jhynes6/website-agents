import json
import asyncio
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote
from collections import Counter

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

from ..config import get_settings
from ..logging import log
from ..clients.agent_templates.loader import load_agent_template
from ..clients.llm import llm_client
from ..clients.pinecone_client import pinecone_kb_client
from ..clients.supabase_storage_client import SupabaseStorageClient
from ..utils.retrieval_eval import build_trace_from_hits, write_trace

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

router = APIRouter()

_QUERY_REWRITE_SYSTEM_PROMPT = """You are a query rewriting assistant for vector retrieval (RAG).

Given a user's question, produce a rewritten query that maximizes retrieval recall/precision from a knowledge base.

Rules:
- Do NOT add facts not present in the user question.
- Preserve named entities (company names, product names, locations), numbers, and constraints.
- Expand acronyms where obvious; add common synonyms where helpful.
- Keep it short and "searchy" (keywords + key phrases), not conversational.

Return ONLY valid JSON with this exact shape:
{
  "rewritten_query": "string",
  "expansions": ["string", "..."]  // 0-2 items
}
"""

_CASE_STUDY_SUMMARY_FORMAT_INSTRUCTIONS = """When asked to summarize case studies, format the response as follows:

0. CLIENT: the name of the client in the case study.
1. INDUSTRY: the industry category of the CLIENT (rather than the subject of the case) in the case study.
2. SERVICES: the service(s) that were rendered (bullet point list). Be as specific as possible when defining the service (for example, use "paid ads" instead of "marketing services").
3. RESULTS: extract and list ALL quantitative results and ALL qualitative results found in the case study. Do not summarize into a smaller representative set. Only combine exact duplicates. Completeness takes priority over brevity.
   - If no quantitative results are provided, explicitly state: "No quantitative results provided".
   - If no qualitative results are provided, explicitly state: "No qualitative results provided".
4. MECHANISM: the specific mechanism(s) by which the results were achieved. This should answer: "How did [service] drive [result]?"
5. SOURCE: include the source URL from metadata as "Source: [URL]". If no URL is available, state "Source: Not available".

When summarizing a single case study, output the result as a clean bulleted list.
"""

_CASE_STUDY_SUMMARY_JSON_INSTRUCTIONS = """Return ONLY valid JSON with this exact shape:
{
  "client": "string",
  "industry": "string",
  "services": ["string", "..."],
  "results_quantitative": ["string", "..."],
  "results_qualitative": ["string", "..."],
  "mechanism": ["string", "..."],
  "source": "string"
}

Rules:
- Include all quantitative and qualitative results present in the document.
- If no quantitative results are provided, set results_quantitative to ["No quantitative results provided"].
- If no qualitative results are provided, set results_qualitative to ["No qualitative results provided"].
- If source URL is missing, set source to "Not available".
"""

_CLIENT_INTAKE_FORM_SUMMARIZER_INSTRUCTIONS = """When summarizing the client intake form, extract the client's answers from the following sections and return JSON with these fields:

1. TARGETING: the client's target market (industries, headcounts, company demographics).
2. PRODUCTS_SERVICES: the client's service offerings they provide.
3. CASE_STUDIES: the case studies provided by the client.
4. PAIN_POINTS: the pain points of the client's ideal client.
5. OFFERS: response to "For each service, what are your top offers (packages/examples) that you would be willing to pitch them?"
6. DIFFERENTIATORS: how the client is different.
7. PRICING: the client's typical pricing packages.

Return ONLY valid JSON object with those exact keys. Do not include markdown.
"""

_CLIENT_MATERIALS_SUMMARIZER_INSTRUCTIONS = """Analyze the content of each file and extract information useful for generating a go-to-market strategy for the client.

Return response as JSON with the following fields:
1. DOC_NAME: normalized document id from the knowledge base (use file_key if available).
2. URL: link to the drive file.
3. CONTENT_OVERVIEW: one-sentence explanation of the doc contents.
4. DETAILED_SUMMARY: a detailed extraction of the document content. This should be a complete and accurate summary of the document. Do not lose context here. 
5. SOURCE: "Source: [URL]" if URL exists; otherwise "Source: Not available".

Return ONLY valid JSON object with those exact keys. Do not include markdown.
"""

_CLIENT_WEBSITE_SUMMARIZER_INSTRUCTIONS = """Generate a high-level summary from core website pages.

Return ONLY valid JSON object with this exact shape:
{
  "executive_overview": "string",
  "services_products": {
    "a": "description_a",
    "b": "description_b"
  },
  "target_industries": ["industry 1", "industry 2", "industry 3"]
}

Guidelines:
- Use only the provided website documents.
- Keep executive_overview concise and strategic.
- services_products should capture distinct offerings/services as key-value pairs.
- target_industries should be a deduplicated list of industries/markets served.
"""

_UNIQUE_MECHANISM_RESEARCHER_INSTRUCTIONS = """Given a list of services our client is selling, search for "advanced strategies for [service] in 2025" and propose potential unique mechanisms that make the service sound cutting edge and compelling.

A "unique mechanism" should explain HOW a service could lead to strong outcomes (for example, 400% increase in conversion rate). Be specific enough to show expertise, but keep language clear and practical.

For example: paid social ads -> "using lookalike audiences and dynamic ad creative".

Return format for each service:
[service name] - Unique Mechanisms
1.
2.
3.
query: [query that was searched]
"""

_CASE_STUDY_CONTENT_TYPES = {"case_study", "case_studies"}
_CASE_STUDY_BUCKET = "client-data-sources"
_WEBSITE_SUMMARY_CONTENT_TYPES = [
    "homepage",
    "services_products",
    "industry_markets",
    "case_studies",
    "testimonials",
    "blogs_resources",
    "about",
]


def _safe_parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort parse of a JSON object from an LLM response.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        out = json.loads(raw)
        if isinstance(out, dict):
            return out
    except Exception:
        pass
    # Try to extract the first {...} block
    try:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return None
        out = json.loads(m.group(0))
        return out if isinstance(out, dict) else None
    except Exception:
        return None


async def _rewrite_queries_for_retrieval(
    *,
    query_text: str,
    max_expansions: int = 2,
) -> Dict[str, Any]:
    """
    Returns:
      {
        "rewritten_query": str,
        "expansions": list[str],
        "used": bool,
      }
    """
    q0 = (query_text or "").strip()
    if not q0:
        return {"rewritten_query": "", "expansions": [], "used": False}

    try:
        resp = await llm_client.chat(
            messages=[
                {"role": "system", "content": _QUERY_REWRITE_SYSTEM_PROMPT},
                {"role": "user", "content": q0},
            ],
            temperature=0.0,
            max_tokens=220,
            model="gpt-4o-mini",
        )
        content = str(((resp or {}).get("choices") or [{}])[0].get("message", {}).get("content") or "")
        parsed = _safe_parse_json_object(content) or {}

        rewritten = str(parsed.get("rewritten_query") or "").strip()
        expansions_in = parsed.get("expansions")
        expansions: List[str] = []
        if isinstance(expansions_in, list):
            for x in expansions_in:
                if not isinstance(x, str):
                    continue
                s = x.strip()
                if s:
                    expansions.append(s)
        expansions = expansions[: max(0, int(max_expansions or 0))]

        if not rewritten:
            return {"rewritten_query": q0, "expansions": expansions, "used": False}

        return {"rewritten_query": rewritten, "expansions": expansions, "used": True}
    except Exception as e:
        log("query.rewrite.error", {"error": str(e)})
        return {"rewritten_query": q0, "expansions": [], "used": False}


def _merge_hits_by_record_id(hit_lists: List[List[Any]]) -> List[Any]:
    """
    Dedupe Pinecone hits across multiple queries by record_id; keep the highest-scoring hit.
    """
    best: Dict[str, Any] = {}
    for hits in hit_lists:
        for h in hits or []:
            rid = str(getattr(h, "record_id", "") or "")
            if not rid:
                continue
            try:
                score = float(getattr(h, "score", 0.0) or 0.0)
            except Exception:
                score = 0.0
            prev = best.get(rid)
            if prev is None:
                best[rid] = h
                continue
            try:
                prev_score = float(getattr(prev, "score", 0.0) or 0.0)
            except Exception:
                prev_score = 0.0
            if score > prev_score:
                best[rid] = h
    out = list(best.values())
    out.sort(key=lambda x: float(getattr(x, "score", 0.0) or 0.0), reverse=True)
    return out


def _preview_text(value: str, max_len: int = 120) -> str:
    s = (value or "").strip()
    if len(s) <= max_len:
        return s
    return s[:max_len] + "…"


def _summarize_hits(hits: List[Any], *, max_items: int = 5) -> Dict[str, Any]:
    distinct_files = set()
    by_content_type: Dict[str, int] = {}
    by_document_source: Dict[str, int] = {}
    samples: List[Dict[str, Any]] = []

    for h in hits:
        rid = str(getattr(h, "record_id", "") or "").strip()
        score = float(getattr(h, "score", 0.0) or 0.0)
        f = getattr(h, "fields", {}) or {}
        fk = str(f.get("file_key") or "").strip()
        ct = str(f.get("content_type") or "").strip() or "(none)"
        ds = str(f.get("document_source") or "").strip() or "(none)"
        if fk:
            distinct_files.add(fk)
        by_content_type[ct] = by_content_type.get(ct, 0) + 1
        by_document_source[ds] = by_document_source.get(ds, 0) + 1
        if len(samples) < max_items:
            samples.append(
                {
                    "record_id": rid,
                    "score": round(score, 6),
                    "content_type": ct,
                    "document_source": ds,
                    "file_key": fk,
                    "chunk_index": f.get("chunk_index"),
                    "title": _preview_text(str(f.get("title") or ""), 80),
                }
            )

    return {
        "hits_total": len(hits),
        "distinct_files": len(distinct_files),
        "by_content_type": by_content_type,
        "by_document_source": by_document_source,
        "top_hits": samples,
    }


def _summarize_first_hit_per_query(hit_lists: List[List[Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, hits in enumerate(hit_lists, start=1):
        if not hits:
            out.append({"query_idx": i, "hits": 0})
            continue
        h = hits[0]
        f = getattr(h, "fields", {}) or {}
        out.append(
            {
                "query_idx": i,
                "hits": len(hits),
                "record_id": str(getattr(h, "record_id", "") or ""),
                "score": round(float(getattr(h, "score", 0.0) or 0.0), 6),
                "content_type": str(f.get("content_type") or ""),
                "document_source": str(f.get("document_source") or ""),
                "file_key": str(f.get("file_key") or ""),
                "title": _preview_text(str(f.get("title") or ""), 80),
            }
        )
    return out


def _normalize_agent_type(agent_type: str) -> str:
    t = (agent_type or "").strip().lower()
    if not t:
        return "kb_chat"
    return t.replace("-", "_")


def _build_conversation_history_block(
    messages: Any,
    *,
    max_messages: int = 8,
    max_chars: int = 4000,
) -> str:
    """
    Build a compact conversation-history block from chat messages.

    This gives the model session continuity without using prior turns as factual evidence.
    """
    if not isinstance(messages, list):
        return ""

    cleaned: List[str] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "").strip().lower()
        if role not in {"user", "assistant"}:
            continue
        content = str(m.get("content") or "").strip()
        if not content:
            continue
        cleaned.append(f"{role}: {content}")

    if not cleaned:
        return ""

    # Keep recent turns first.
    cleaned = cleaned[-max(1, int(max_messages)) :]

    # Enforce character budget from the end (most recent messages).
    kept_rev: List[str] = []
    used = 0
    for msg in reversed(cleaned):
        add = len(msg) + (1 if kept_rev else 0)
        if used + add > max(200, int(max_chars)):
            break
        kept_rev.append(msg)
        used += add
    kept = list(reversed(kept_rev))
    return "\n".join(kept).strip()

def _parse_requested_case_study_count(q: str) -> int:
    """
    Best-effort parse of requests like:
      - "summarize 5 case studies"
      - "summarise 3 case studies"
      - "summarize a few case studies"
    """
    text = (q or "").strip().lower()
    # Explicit number
    m = re.search(r"\b(?:summarize|summarise)\s+(\d+)\s+case\s+stud", text)
    if m:
        try:
            n = int(m.group(1))
            return max(1, min(10, n))
        except Exception:
            pass
    # Vague counts
    if re.search(r"\b(?:a\s+few|few|some|several)\s+case\s+stud", text):
        return 3
    return 0

def _looks_like_case_study_summary_request(q: str) -> bool:
    text = (q or "").strip().lower()
    return "case stud" in text


def _looks_like_all_case_studies_request(q: str) -> bool:
    text = (q or "").strip().lower()
    if "case stud" not in text:
        return False
    # "all case studies", "every case study", "summarize all case studies", etc.
    return bool(re.search(r"\b(all|every|each|entire|full)\b", text))


def _looks_like_pricing_summary_request(q: str) -> bool:
    text = (q or "").strip().lower()
    if not text:
        return False
    pricing_terms = [
        "pricing",
        "price",
        "prices",
        "cost",
        "costs",
        "rate",
        "rates",
        "package",
        "packages",
        "starting at",
        "average order value",
    ]
    return any(t in text for t in pricing_terms)


def _intent_seed_queries(
    *,
    query_text: str,
    pricing_mode: bool,
    case_study_mode: bool,
) -> List[str]:
    """
    Safe retrieval seeds for strongly-typed intents.

    Prevents generic query-rewrite drift (for example, "share pricing"
    becoming stock/equity related rewrites).
    """
    out: List[str] = [(query_text or "").strip()]
    if pricing_mode:
        out.extend(
            [
                "service pricing starting at costs average order value package tiers",
                "intake form pricing starting at costs",
            ]
        )
    elif case_study_mode:
        out.extend(
            [
                "case studies client results outcomes success stories",
                "customer success examples measurable outcomes",
            ]
        )

    seen: set[str] = set()
    deduped: List[str] = []
    for q in out:
        s = (q or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        deduped.append(s)
    return deduped


def _build_case_study_summaries_context(
    *,
    hits: List[Any],
    max_docs: int,
    chunks_per_doc: int = 3,
) -> tuple[List[Dict[str, Any]], List[str]]:
    """
    Convert chunk-level hits into doc-level sources and numbered context blocks.

    We dedupe by `file_key` and then take up to `chunks_per_doc` chunks per doc (ordered by chunk_index).
    """
    # file_key -> list of hits
    by_fk: Dict[str, List[Any]] = {}
    for h in hits:
        f = getattr(h, "fields", {}) or {}
        fk = str(f.get("file_key") or "").strip()
        if not fk:
            continue
        by_fk.setdefault(fk, []).append(h)

    # Rank docs by best score
    ranked: List[tuple[str, float]] = []
    for fk, hs in by_fk.items():
        best = 0.0
        for h in hs:
            try:
                best = max(best, float(getattr(h, "score", 0.0) or 0.0))
            except Exception:
                continue
        ranked.append((fk, best))
    ranked.sort(key=lambda x: x[1], reverse=True)
    top_fks = [fk for fk, _ in ranked[: max_docs]]

    sources: List[Dict[str, Any]] = []
    context_blocks: List[str] = []
    for i, fk in enumerate(top_fks, start=1):
        hs = by_fk.get(fk, [])
        # Order chunks by chunk_index to preserve narrative flow
        def _chunk_idx(h: Any) -> int:
            try:
                return int((getattr(h, "fields", {}) or {}).get("chunk_index") or 0)
            except Exception:
                return 0
        use_all_chunks = int(chunks_per_doc or 0) <= 0
        hs_sorted = sorted(hs, key=_chunk_idx) if use_all_chunks else sorted(hs, key=_chunk_idx)[: max(1, chunks_per_doc)]
        # Pick representative metadata
        first_fields = (getattr(hs_sorted[0], "fields", {}) or {}) if hs_sorted else {}
        title = str(first_fields.get("title") or first_fields.get("file_key") or f"Case study {i}").strip()
        url_out = str(first_fields.get("url") or first_fields.get("file_key") or "").strip()
        combined = "\n\n".join([str((getattr(h, "fields", {}) or {}).get("text") or "").strip() for h in hs_sorted]).strip()
        snippet = (combined[:250] + "…") if len(combined) > 250 else combined
        sources.append({"title": title, "url": url_out, "snippet": snippet})
        context_blocks.append(f"[{i}] Title: {title}\nURL: {url_out}\nContent:\n{combined}")

    return sources, context_blocks


def _build_doc_summaries_context(
    *,
    hits: List[Any],
    max_docs: int,
    chunks_per_doc: int = 4,
    prioritize_scored_chunks: bool = False,
) -> tuple[List[Dict[str, Any]], List[str]]:
    """
    Generic doc-level context builder for summary-style answers.
    """
    by_fk: Dict[str, List[Any]] = {}
    for h in hits:
        f = getattr(h, "fields", {}) or {}
        fk = str(f.get("file_key") or "").strip()
        if not fk:
            continue
        by_fk.setdefault(fk, []).append(h)

    ranked: List[tuple[str, float]] = []
    for fk, hs in by_fk.items():
        best = 0.0
        for h in hs:
            try:
                best = max(best, float(getattr(h, "score", 0.0) or 0.0))
            except Exception:
                continue
        ranked.append((fk, best))
    ranked.sort(key=lambda x: x[1], reverse=True)

    # max_docs <= 0 means "all"
    if max_docs and max_docs > 0:
        top_fks = [fk for fk, _ in ranked[:max_docs]]
    else:
        top_fks = [fk for fk, _ in ranked]

    sources: List[Dict[str, Any]] = []
    context_blocks: List[str] = []
    pricing_keywords = (
        "pricing",
        "price",
        "cost",
        "starting at",
        "average order value",
        "package",
        "tier",
    )

    for i, fk in enumerate(top_fks, start=1):
        hs = by_fk.get(fk, [])

        def _chunk_idx(h: Any) -> int:
            try:
                return int((getattr(h, "fields", {}) or {}).get("chunk_index") or 0)
            except Exception:
                return 0

        use_all_chunks = int(chunks_per_doc or 0) <= 0
        if prioritize_scored_chunks and not use_all_chunks:
            # For intent-heavy summaries (e.g., pricing), include chunks most likely
            # to contain the answer instead of only the earliest chunks in the file.
            def _score_key(h: Any) -> tuple[int, float, int]:
                f = getattr(h, "fields", {}) or {}
                text = str(f.get("text") or "").lower()
                has_kw = 1 if any(k in text for k in pricing_keywords) else 0
                try:
                    score = float(getattr(h, "score", 0.0) or 0.0)
                except Exception:
                    score = 0.0
                return (has_kw, score, -_chunk_idx(h))

            selected = sorted(hs, key=_score_key, reverse=True)[: max(1, chunks_per_doc)]
            hs_sorted = sorted(selected, key=_chunk_idx)
        else:
            hs_sorted = sorted(hs, key=_chunk_idx) if use_all_chunks else sorted(hs, key=_chunk_idx)[: max(1, chunks_per_doc)]
        first_fields = (getattr(hs_sorted[0], "fields", {}) or {}) if hs_sorted else {}
        title = str(first_fields.get("title") or first_fields.get("file_key") or f"Source {i}").strip()
        url_out = str(first_fields.get("url") or first_fields.get("file_key") or "").strip()
        combined = "\n\n".join([str((getattr(h, "fields", {}) or {}).get("text") or "").strip() for h in hs_sorted]).strip()
        snippet = (combined[:250] + "…") if len(combined) > 250 else combined
        sources.append({"title": title, "url": url_out, "snippet": snippet})
        context_blocks.append(f"[{i}] Title: {title}\nURL: {url_out}\nContent:\n{combined}")

    return sources, context_blocks


def _system_prompt_for(agent_type: str) -> str:
    """
    Prefer the agent template (if present) so behavior matches our intended "agentic" roles.
    Fallback to a generic QA-safe assistant prompt.
    """
    normalized = _normalize_agent_type(agent_type)
    try:
        base = load_agent_template(normalized)
    except Exception:
        base = (
            "You are a helpful assistant. Answer the user's question using the provided context.\n"
            "If the context is insufficient, say so and ask a clarifying question.\n"
            "Be concise and specific."
        )

    # Common guardrails: keep output clean, don't cite raw filenames unless asked
    normalized = _normalize_agent_type(agent_type)
    guardrails = (
        "You will be given a small set of retrieved context snippets.\n"
        "- Use ONLY that context for factual claims.\n"
        "- Do not mention internal tool names, record IDs, or retrieval mechanics.\n"
    )
    if normalized == "kb_chat":
        guardrails += (
            "- For broad/open-ended questions like “what do you do?” or “what services do you offer?”, "
            "start by giving a useful, sales-oriented overview framed around goods/services sold.\n"
            "- Do NOT lead with “the context does not provide…”. If specifics are missing, give the best safe overview you can, "
            "clearly label any generalized content as examples, then ask ONE light clarifying question.\n"
        )
    else:
        guardrails += (
            "- If context is insufficient, say what is missing and ask ONE clarifying question.\n"
        )
    return f"{base}\n\n{guardrails}"


def _is_open_ended_services_question(q: str) -> bool:
    text = (q or "").strip().lower()
    if not text:
        return False
    patterns = [
        r"\bwhat\s+do\s+you\s+do\b",
        r"\bwhat\s+does\s+your\s+company\s+do\b",
        r"\btell\s+me\s+about\s+what\s+you\s+do\b",
        r"\bwhat\s+services\s+do\s+you\s+offer\b",
        r"\bwhat\s+do\s+you\s+offer\b",
        r"\bwhat\s+can\s+you\s+help\s+with\b",
        r"\bour\s+services\b",
        r"\bservices\b",
    ]
    return any(re.search(p, text) for p in patterns)


def _parse_markdown_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    raw = text or ""
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    fm_raw = parts[1]
    body = parts[2].lstrip("\n")
    if yaml is None:
        return {}, body
    try:
        meta = yaml.safe_load(fm_raw) or {}
        if not isinstance(meta, dict):
            meta = {}
        return meta, body
    except Exception:
        return {}, body


def _list_objects_all_pages(storage: SupabaseStorageClient, *, bucket: str, prefix: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    limit = 500
    offset = 0
    while True:
        batch = storage.list_objects(
            bucket,
            prefix=prefix,
            limit=limit,
            offset=offset,
            sort_by={"column": "name", "order": "asc"},
        )
        if not batch:
            break
        out.extend([b for b in batch if isinstance(b, dict)])
        if len(batch) < limit:
            break
        offset += limit
    return out


def _collect_case_study_docs_sync(*, client_slug: str) -> List[Dict[str, Any]]:
    slug = (client_slug or "").strip()
    storage = SupabaseStorageClient()
    docs: List[Dict[str, Any]] = []
    seen_keys: set[str] = set()

    for subfolder in ("website", "drive", "intake_form"):
        prefix = f"{slug}/{subfolder}"
        items = _list_objects_all_pages(storage, bucket=_CASE_STUDY_BUCKET, prefix=prefix)
        for item in items:
            if item.get("metadata") is None:
                continue
            name = str(item.get("name") or "").strip().lstrip("/")
            if not name.endswith(".md"):
                continue

            # list_objects may return names relative to prefix or absolute-ish.
            if name.startswith(f"{slug}/"):
                object_path = name
            elif name.startswith(("website/", "drive/", "intake_form/")):
                object_path = f"{slug}/{name}"
            else:
                object_path = f"{prefix}/{name}"

            if object_path in seen_keys:
                continue

            try:
                raw = storage.download_bytes(_CASE_STUDY_BUCKET, object_path).decode("utf-8", errors="ignore")
            except Exception:
                continue

            meta, body = _parse_markdown_frontmatter(raw)
            ct = str(meta.get("content_type") or "").strip().lower()
            if ct not in _CASE_STUDY_CONTENT_TYPES:
                continue

            title = str(meta.get("title") or name.rsplit("/", 1)[-1]).strip()
            url = str(meta.get("url") or meta.get("storage_preview_url") or "").strip()
            file_key = str(meta.get("storage_path") or object_path).strip()
            source = str(meta.get("document_source") or subfolder).strip()
            text = (body or "").strip()
            if not text:
                continue

            seen_keys.add(object_path)
            docs.append(
                {
                    "title": title,
                    "url": url,
                    "file_key": file_key,
                    "document_source": source,
                    "content_type": ct,
                    "text": text,
                }
            )

    docs.sort(key=lambda d: (str(d.get("title") or "").lower(), str(d.get("file_key") or "").lower()))
    return docs


def _normalize_document_type(source: str) -> str:
    s = (source or "").strip().lower()
    if s == "website":
        return "website"
    if s in {"intake_form", "intake-form"}:
        return "intake_form"
    if s in {"drive", "client_materials"}:
        return "drive"
    return s or "unknown"


def _persist_case_studies_summary_json_sync(*, client_slug: str, payload: Dict[str, Any]) -> str:
    storage = SupabaseStorageClient()
    path = f"{(client_slug or '').strip()}/client_brief/case_studies_all.json"
    storage.upload_json(bucket=_CASE_STUDY_BUCKET, path=path, payload=payload, upsert=True)
    return path


def _to_str_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_case_study_summary(summary: Dict[str, Any], *, fallback_title: str, fallback_url: str) -> Dict[str, Any]:
    client = str(summary.get("client") or "").strip() or fallback_title
    industry = str(summary.get("industry") or "").strip()
    services = _to_str_list(summary.get("services"))
    results_quantitative = _to_str_list(summary.get("results_quantitative"))
    results_qualitative = _to_str_list(summary.get("results_qualitative"))
    mechanism = _to_str_list(summary.get("mechanism"))
    source = str(summary.get("source") or "").strip() or (fallback_url or "Not available")

    if not results_quantitative:
        results_quantitative = ["No quantitative results provided"]
    if not results_qualitative:
        results_qualitative = ["No qualitative results provided"]

    return {
        "client": client,
        "industry": industry,
        "services": services,
        "results_quantitative": results_quantitative,
        "results_qualitative": results_qualitative,
        "mechanism": mechanism,
        "source": source,
    }


def _format_case_study_summary_markdown(summary: Dict[str, Any]) -> str:
    services = _to_str_list(summary.get("services"))
    rq = _to_str_list(summary.get("results_quantitative"))
    rl = _to_str_list(summary.get("results_qualitative"))
    mech = _to_str_list(summary.get("mechanism"))
    source = str(summary.get("source") or "Not available")

    out: List[str] = []
    out.append(f"- **CLIENT:** {str(summary.get('client') or '')}")
    out.append(f"- **INDUSTRY:** {str(summary.get('industry') or '')}")
    out.append("- **SERVICES:**")
    out.extend([f"  - {x}" for x in (services or ["No services provided"])])
    out.append("- **RESULTS_QUANTITATIVE:**")
    out.extend([f"  - {x}" for x in (rq or ["No quantitative results provided"])])
    out.append("- **RESULTS_QUALITATIVE:**")
    out.extend([f"  - {x}" for x in (rl or ["No qualitative results provided"])])
    out.append("- **MECHANISM:**")
    out.extend([f"  - {x}" for x in (mech or ["No mechanism provided"])])
    out.append(f"- **SOURCE:** {source}")
    return "\n".join(out)


def _persist_client_brief_json_sync(*, client_slug: str, filename: str, payload: Dict[str, Any]) -> str:
    storage = SupabaseStorageClient()
    path = f"{(client_slug or '').strip()}/client_brief/{filename}"
    storage.upload_json(bucket=_CASE_STUDY_BUCKET, path=path, payload=payload, upsert=True)
    return path


def _load_client_brief_json_sync(*, client_slug: str, filename: str) -> Dict[str, Any]:
    storage = SupabaseStorageClient()
    path = f"{(client_slug or '').strip()}/client_brief/{filename}"
    try:
        data = storage.download_json(_CASE_STUDY_BUCKET, path)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _normalize_service_name(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    low = re.sub(r"\s+", " ", s.lower())

    if any(k in low for k in ["branding", "rebrand", "brand identity"]):
        return "Brand Strategy & Identity"
    if any(k in low for k in ["website", "web design", "web development", "site design"]):
        return "Website Design & Development"
    if any(k in low for k in ["marketing campaign", "campaign strategy", "campaigns"]):
        return "Marketing Campaign Strategy"
    if any(k in low for k in ["ppc", "paid ads", "google ads", "paid media", "search ads"]):
        return "Paid Media (PPC)"
    if "seo" in low:
        return "SEO"
    if "email marketing" in low:
        return "Email Marketing"
    if any(k in low for k in ["social media", "social content", "ugc"]):
        return "Social Media Marketing"
    if any(k in low for k in ["cro", "conversion rate"]):
        return "Conversion Rate Optimization (CRO)"
    if any(k in low for k in ["print design", "stationery", "collateral", "environmental graphics"]):
        return "Brand Collateral Design"
    if "product identity" in low:
        return "Product Identity Design"

    # Default to title-cased normalized label.
    return re.sub(r"\s+", " ", s).strip().title()


def _extract_candidate_services_from_briefs(
    *,
    intake_summary: Dict[str, Any],
    website_summary: Dict[str, Any],
    case_studies_all: Dict[str, Any],
) -> List[str]:
    candidates: List[str] = []

    # intake_form_summary.json
    i_summary = intake_summary.get("summary") if isinstance(intake_summary.get("summary"), dict) else {}
    ps = i_summary.get("PRODUCTS_SERVICES") if isinstance(i_summary, dict) else None
    ps_desc = ""
    if isinstance(ps, dict):
        ps_desc = str(ps.get("description") or "")
    if ps_desc.strip():
        for part in re.split(r"[,;/\n]+", ps_desc):
            p = part.strip()
            if p:
                candidates.append(p)

    # website_summary.json
    w_summary = website_summary.get("summary") if isinstance(website_summary.get("summary"), dict) else {}
    w_services = w_summary.get("services_products") if isinstance(w_summary, dict) else None
    if isinstance(w_services, dict):
        for k in w_services.keys():
            candidates.append(str(k))
        for v in w_services.values():
            txt = str(v or "").strip()
            if txt:
                # heuristic: split simple compound listings in values
                for part in re.split(r"[,;/\n]+", txt):
                    if len(part.strip().split()) <= 6:
                        candidates.append(part.strip())

    # case_studies_all.json
    summaries = case_studies_all.get("summaries")
    if isinstance(summaries, list):
        for rec in summaries:
            if not isinstance(rec, dict):
                continue
            s = rec.get("summary")
            if not isinstance(s, dict):
                continue
            services = s.get("services")
            if isinstance(services, list):
                for svc in services:
                    sv = str(svc or "").strip()
                    if sv:
                        candidates.append(sv)

    return candidates


def _build_top_services_list(*, candidates: List[str], max_services: int = 10) -> List[str]:
    normalized = [_normalize_service_name(c) for c in candidates if str(c or "").strip()]
    normalized = [n for n in normalized if n]
    counts = Counter(normalized)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [name for name, _ in ranked[: max(1, int(max_services))]]


def _web_search_snippets(query: str, *, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Lightweight web search via DuckDuckGo HTML results.
    Best-effort and dependency-free.
    """
    q = (query or "").strip()
    if not q:
        return []
    url = f"https://duckduckgo.com/html/?q={quote(q)}"
    try:
        resp = httpx.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code >= 400:
            return []
        text = resp.text or ""
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', text, flags=re.IGNORECASE | re.DOTALL)
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"', text, flags=re.IGNORECASE | re.DOTALL)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>|class="result__snippet"[^>]*>(.*?)</div>', text, flags=re.IGNORECASE | re.DOTALL)
        out: List[Dict[str, str]] = []
        for i in range(min(max_results, len(titles), len(links))):
            raw_snip = ""
            if i < len(snippets):
                raw_snip = snippets[i][0] or snippets[i][1] or ""
            clean = re.sub(r"<[^>]+>", "", raw_snip)
            clean = re.sub(r"\s+", " ", clean).strip()
            title = re.sub(r"<[^>]+>", "", titles[i]).strip()
            out.append({"title": title, "url": links[i], "snippet": clean})
        return out
    except Exception:
        return []


async def _generate_unique_mechanism_research(*, client_slug: str) -> Dict[str, Any]:
    intake = await asyncio.to_thread(_load_client_brief_json_sync, client_slug=client_slug, filename="intake_form_summary.json")
    website = await asyncio.to_thread(_load_client_brief_json_sync, client_slug=client_slug, filename="website_summary.json")
    case_all = await asyncio.to_thread(_load_client_brief_json_sync, client_slug=client_slug, filename="case_studies_all.json")

    candidates = _extract_candidate_services_from_briefs(
        intake_summary=intake,
        website_summary=website,
        case_studies_all=case_all,
    )
    services = _build_top_services_list(candidates=candidates, max_services=10)

    entries: List[Dict[str, Any]] = []
    for svc in services:
        query = f"advanced strategies for {svc} in 2025"
        snippets = await asyncio.to_thread(_web_search_snippets, query, max_results=5)
        resp = await llm_client.chat(
            messages=[
                {"role": "system", "content": "You are a growth strategist. Be specific, practical, and concise."},
                {
                    "role": "user",
                    "content": (
                        f"{_UNIQUE_MECHANISM_RESEARCHER_INSTRUCTIONS}\n\n"
                        f"Service: {svc}\n"
                        f"Query: {query}\n"
                        f"Web snippets:\n{json.dumps(snippets, ensure_ascii=False)}\n\n"
                        "Return ONLY valid JSON with shape:\n"
                        '{"service":"", "query":"", "unique_mechanisms":["", "", ""]}'
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=700,
            model="gpt-4o-mini",
        )
        content = str(((resp or {}).get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
        parsed = _safe_parse_json_object(content) or {}
        mechs = _to_str_list(parsed.get("unique_mechanisms"))[:3]
        while len(mechs) < 3:
            mechs.append("")
        entries.append(
            {
                "service": str(parsed.get("service") or svc).strip() or svc,
                "query": str(parsed.get("query") or query).strip() or query,
                "unique_mechanisms": mechs,
                "web_snippets": snippets,
            }
        )

    payload = {
        "client_slug": client_slug,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "source": "unique_mechanism_research",
        "services_input_candidates_count": len(candidates),
        "services_selected": services,
        "results": entries,
    }
    path = await asyncio.to_thread(
        _persist_client_brief_json_sync,
        client_slug=client_slug,
        filename="unique_mechanism_research.json",
        payload=payload,
    )
    return {
        "saved_path": path,
        "services_selected_count": len(services),
        "results_count": len(entries),
    }


def _collect_intake_form_docs_sync(*, client_slug: str) -> List[Dict[str, Any]]:
    slug = (client_slug or "").strip()
    storage = SupabaseStorageClient()
    docs: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for subfolder in ("intake_form", "drive"):
        prefix = f"{slug}/{subfolder}"
        items = _list_objects_all_pages(storage, bucket=_CASE_STUDY_BUCKET, prefix=prefix)
        for item in items:
            if item.get("metadata") is None:
                continue
            name = str(item.get("name") or "").strip().lstrip("/")
            if not name.endswith(".md"):
                continue
            if name.startswith(f"{slug}/"):
                object_path = name
            elif name.startswith(("website/", "drive/", "intake_form/")):
                object_path = f"{slug}/{name}"
            else:
                object_path = f"{prefix}/{name}"
            if object_path in seen:
                continue
            try:
                raw = storage.download_bytes(_CASE_STUDY_BUCKET, object_path).decode("utf-8", errors="ignore")
            except Exception:
                continue
            meta, body = _parse_markdown_frontmatter(raw)
            src = str(meta.get("document_source") or "").strip().lower()
            ct = str(meta.get("content_type") or "").strip().lower()
            if src not in {"intake_form", "intake-form"} and ct not in {"intake_form", "intake-form"}:
                continue
            seen.add(object_path)
            docs.append(
                {
                    "title": str(meta.get("title") or name.rsplit("/", 1)[-1]),
                    "url": str(meta.get("url") or meta.get("storage_preview_url") or ""),
                    "file_key": str(meta.get("storage_path") or object_path),
                    "document_source": src or "intake_form",
                    "content_type": ct or "intake_form",
                    "text": (body or "").strip(),
                }
            )
    return docs


def _collect_client_materials_docs_sync(*, client_slug: str) -> List[Dict[str, Any]]:
    slug = (client_slug or "").strip()
    storage = SupabaseStorageClient()
    docs: List[Dict[str, Any]] = []
    seen: set[str] = set()
    prefix = f"{slug}/drive"
    items = _list_objects_all_pages(storage, bucket=_CASE_STUDY_BUCKET, prefix=prefix)
    for item in items:
        if item.get("metadata") is None:
            continue
        name = str(item.get("name") or "").strip().lstrip("/")
        if not name.endswith(".md"):
            continue
        if name.startswith(f"{slug}/"):
            object_path = name
        elif name.startswith(("website/", "drive/", "intake_form/")):
            object_path = f"{slug}/{name}"
        else:
            object_path = f"{prefix}/{name}"
        if object_path in seen:
            continue
        try:
            raw = storage.download_bytes(_CASE_STUDY_BUCKET, object_path).decode("utf-8", errors="ignore")
        except Exception:
            continue
        meta, body = _parse_markdown_frontmatter(raw)
        src = str(meta.get("document_source") or "").strip().lower()
        ct = str(meta.get("content_type") or "").strip().lower()
        if src in {"intake_form", "intake-form"} or ct in {"intake_form", "intake-form"}:
            continue
        seen.add(object_path)
        docs.append(
            {
                "title": str(meta.get("title") or name.rsplit("/", 1)[-1]),
                "url": str(meta.get("url") or meta.get("storage_preview_url") or ""),
                "file_key": str(meta.get("storage_path") or object_path),
                "document_source": src or "drive",
                "content_type": ct or "other",
                "text": (body or "").strip(),
            }
        )
    return docs


def _collect_website_core_docs_sync(*, client_slug: str, max_per_type: int = 20) -> List[Dict[str, Any]]:
    slug = (client_slug or "").strip()
    storage = SupabaseStorageClient()
    docs: List[Dict[str, Any]] = []
    seen: set[str] = set()
    by_type: Dict[str, int] = {t: 0 for t in _WEBSITE_SUMMARY_CONTENT_TYPES}

    prefix = f"{slug}/website"
    items = _list_objects_all_pages(storage, bucket=_CASE_STUDY_BUCKET, prefix=prefix)
    for item in items:
        if item.get("metadata") is None:
            continue
        name = str(item.get("name") or "").strip().lstrip("/")
        if not name.endswith(".md"):
            continue
        if name.startswith(f"{slug}/"):
            object_path = name
        elif name.startswith(("website/", "drive/", "intake_form/")):
            object_path = f"{slug}/{name}"
        else:
            object_path = f"{prefix}/{name}"
        if object_path in seen:
            continue
        try:
            raw = storage.download_bytes(_CASE_STUDY_BUCKET, object_path).decode("utf-8", errors="ignore")
        except Exception:
            continue
        meta, body = _parse_markdown_frontmatter(raw)
        ct = str(meta.get("content_type") or "").strip().lower()
        if ct not in by_type:
            continue
        if by_type[ct] >= max(1, int(max_per_type)):
            continue

        seen.add(object_path)
        by_type[ct] += 1
        docs.append(
            {
                "title": str(meta.get("title") or name.rsplit("/", 1)[-1]),
                "url": str(meta.get("url") or meta.get("storage_preview_url") or ""),
                "file_key": str(meta.get("storage_path") or object_path),
                "document_source": "website",
                "content_type": ct,
                "text": (body or "").strip(),
            }
        )

    return docs


async def _summarize_intake_form_docs(*, client_slug: str) -> Dict[str, Any]:
    docs = await asyncio.to_thread(_collect_intake_form_docs_sync, client_slug=client_slug)
    combined = "\n\n---\n\n".join([str(d.get("text") or "").strip() for d in docs if str(d.get("text") or "").strip()])
    if not combined.strip():
        payload = {
            "client_slug": client_slug,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "source": "intake_form_summary",
            "documents_count": 0,
            "summary": {},
            "sources": [],
        }
        path = await asyncio.to_thread(_persist_client_brief_json_sync, client_slug=client_slug, filename="intake_form_summary.json", payload=payload)
        return {"saved_path": path, "documents_count": 0}

    resp = await llm_client.chat(
        messages=[
            {"role": "system", "content": "You are a structured summarizer. Return strict JSON only."},
            {
                "role": "user",
                "content": (
                    f"{_CLIENT_INTAKE_FORM_SUMMARIZER_INSTRUCTIONS}\n\n"
                    "Intake form content:\n"
                    f"{combined[:45000]}"
                ),
            },
        ],
        temperature=0.1,
        max_tokens=1600,
        model="gpt-4o-mini",
    )
    content = str(((resp or {}).get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
    parsed = _safe_parse_json_object(content) or {}
    payload = {
        "client_slug": client_slug,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "source": "intake_form_summary",
        "documents_count": len(docs),
        "summary": parsed,
        "raw_response": content if not parsed else None,
        "sources": [
            {
                "title": str(d.get("title") or ""),
                "url": str(d.get("url") or ""),
                "file_key": str(d.get("file_key") or ""),
                "document_type": _normalize_document_type(str(d.get("document_source") or "")),
            }
            for d in docs
        ],
    }
    path = await asyncio.to_thread(_persist_client_brief_json_sync, client_slug=client_slug, filename="intake_form_summary.json", payload=payload)
    return {"saved_path": path, "documents_count": len(docs)}


async def _summarize_client_materials_docs(*, client_slug: str) -> Dict[str, Any]:
    docs = await asyncio.to_thread(_collect_client_materials_docs_sync, client_slug=client_slug)
    items: List[Dict[str, Any]] = []
    for d in docs:
        text = str(d.get("text") or "").strip()
        if not text:
            continue
        resp = await llm_client.chat(
            messages=[
                {"role": "system", "content": "You are a structured summarizer. Return strict JSON only."},
                {
                    "role": "user",
                    "content": (
                        f"{_CLIENT_MATERIALS_SUMMARIZER_INSTRUCTIONS}\n\n"
                        f"Document metadata:\n"
                        f"- title: {d.get('title')}\n"
                        f"- file_key: {d.get('file_key')}\n"
                        f"- url: {d.get('url')}\n\n"
                        f"Document content:\n{text[:22000]}"
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=1400,
            model="gpt-4o-mini",
        )
        content = str(((resp or {}).get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
        parsed = _safe_parse_json_object(content) or {}
        if not parsed:
            parsed = {
                "DOC_NAME": str(d.get("file_key") or d.get("title") or ""),
                "URL": str(d.get("url") or ""),
                "CONTENT_OVERVIEW": "",
                "DETAILED_SUMMARY": content,
                "SOURCE": f"Source: {str(d.get('url') or 'Not available')}",
            }
        parsed["document_type"] = _normalize_document_type(str(d.get("document_source") or "drive"))
        parsed["document_source"] = str(d.get("document_source") or "drive")
        items.append(parsed)

    payload = {
        "client_slug": client_slug,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "source": "client_materials_summary",
        "documents_count": len(docs),
        "items": items,
    }
    path = await asyncio.to_thread(_persist_client_brief_json_sync, client_slug=client_slug, filename="client_materials_summary.json", payload=payload)
    return {"saved_path": path, "documents_count": len(docs), "items_count": len(items)}


async def _summarize_client_website_docs(*, client_slug: str) -> Dict[str, Any]:
    docs = await asyncio.to_thread(_collect_website_core_docs_sync, client_slug=client_slug, max_per_type=20)
    grouped: Dict[str, List[Dict[str, Any]]] = {t: [] for t in _WEBSITE_SUMMARY_CONTENT_TYPES}
    for d in docs:
        ct = str(d.get("content_type") or "")
        if ct in grouped:
            grouped[ct].append(d)

    # Compact digest for LLM context size control.
    digest_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for ct in _WEBSITE_SUMMARY_CONTENT_TYPES:
        digest_by_type[ct] = [
            {
                "title": str(d.get("title") or ""),
                "url": str(d.get("url") or ""),
                "file_key": str(d.get("file_key") or ""),
                "excerpt": _preview_text(str(d.get("text") or ""), 600),
            }
            for d in grouped.get(ct, [])
        ]

    llm_resp = await llm_client.chat(
        messages=[
            {"role": "system", "content": "You are a structured website summarizer. Return strict JSON only."},
            {
                "role": "user",
                "content": (
                    f"{_CLIENT_WEBSITE_SUMMARIZER_INSTRUCTIONS}\n\n"
                    f"Included content types: {', '.join(_WEBSITE_SUMMARY_CONTENT_TYPES)}\n"
                    "Each content type is capped at 20 files.\n\n"
                    "Website content digest:\n"
                    f"{json.dumps(digest_by_type, ensure_ascii=False)[:80000]}"
                ),
            },
        ],
        temperature=0.1,
        max_tokens=1500,
        model="gpt-4o-mini",
    )
    content = str(((llm_resp or {}).get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
    parsed = _safe_parse_json_object(content) or {}

    summary_obj = {
        "executive_overview": str(parsed.get("executive_overview") or "").strip(),
        "services_products": parsed.get("services_products") if isinstance(parsed.get("services_products"), dict) else {},
        "target_industries": _to_str_list(parsed.get("target_industries")),
    }

    payload = {
        "client_slug": client_slug,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "source": "website_summary",
        "considered_content_types": list(_WEBSITE_SUMMARY_CONTENT_TYPES),
        "max_files_per_content_type": 20,
        "documents_count": len(docs),
        "counts_by_content_type": {ct: len(grouped.get(ct, [])) for ct in _WEBSITE_SUMMARY_CONTENT_TYPES},
        "summary": summary_obj,
        "raw_response": content if not parsed else None,
    }
    path = await asyncio.to_thread(_persist_client_brief_json_sync, client_slug=client_slug, filename="website_summary.json", payload=payload)
    return {"saved_path": path, "documents_count": len(docs)}
async def _summarize_case_study_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    title = str(doc.get("title") or "Case Study").strip()
    url = str(doc.get("url") or "").strip()
    text = str(doc.get("text") or "").strip()
    text = text[:18000]

    system_prompt = (
        "You are a case-study analyst. Use ONLY the provided document content and metadata. "
        "Do not invent missing details."
    )
    user_prompt = (
        "Summarize this case study document in structured JSON.\n\n"
        f"{_CASE_STUDY_SUMMARY_JSON_INSTRUCTIONS}\n\n"
        f"Document title: {title}\n"
        f"Document URL: {url or 'Not available'}\n\n"
        "Document content:\n"
        f"{text}"
    )
    resp = await llm_client.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=1200,
        model="gpt-4o-mini",
    )
    content = str(((resp or {}).get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
    parsed = _safe_parse_json_object(content) or {}
    normalized = _normalize_case_study_summary(parsed, fallback_title=title, fallback_url=url)
    normalized["_raw_response"] = content if not parsed else None
    return normalized


async def _run_summarize_all_case_studies(
    *,
    client_slug: str,
    stream: bool,
) -> StreamingResponse:
    docs = await asyncio.to_thread(_collect_case_study_docs_sync, client_slug=client_slug)
    log("query.case_studies_all.docs_loaded", {"client_slug": client_slug, "docs": len(docs)})

    if not docs:
        empty_answer = "No case study documents were found for this client."
        if stream:
            async def empty_streamer():
                yield f"8:{json.dumps({'sources': []})}\n"
                yield f"0:{json.dumps(empty_answer)}\n"
            return StreamingResponse(empty_streamer(), media_type="text/plain; charset=utf-8")
        return JSONResponse({"answer": empty_answer, "sources": []})

    summaries: List[str] = []
    summary_records: List[Dict[str, Any]] = []
    for i, d in enumerate(docs, start=1):
        try:
            summary_obj = await _summarize_case_study_doc(d)
        except Exception as e:
            summary_obj = _normalize_case_study_summary(
                {},
                fallback_title=str(d.get("title") or "Case Study"),
                fallback_url=str(d.get("url") or ""),
            )
            summary_obj["_error"] = str(e)
        s = _format_case_study_summary_markdown(summary_obj)
        header = f"## CASE STUDY {i}: {d.get('title')}"
        summaries.append(f"{header}\n{s}".strip())
        summary_records.append(
            {
                "index": i,
                "title": str(d.get("title") or ""),
                "url": str(d.get("url") or ""),
                "file_key": str(d.get("file_key") or ""),
                "document_source": str(d.get("document_source") or ""),
                "document_type": _normalize_document_type(str(d.get("document_source") or "")),
                "content_type": str(d.get("content_type") or ""),
                "summary": {
                    "client": summary_obj.get("client"),
                    "industry": summary_obj.get("industry"),
                    "services": summary_obj.get("services") or [],
                    "results_quantitative": summary_obj.get("results_quantitative") or [],
                    "results_qualitative": summary_obj.get("results_qualitative") or [],
                    "mechanism": summary_obj.get("mechanism") or [],
                    "source": summary_obj.get("source") or "Not available",
                },
                "summary_markdown": s,
            }
        )

    answer = "\n\n".join(summaries).strip()
    sources = [
        {
            "title": str(d.get("title") or "Case Study"),
            "url": str(d.get("url") or ""),
            "snippet": _preview_text(str(d.get("text") or ""), 250),
            "document_type": _normalize_document_type(str(d.get("document_source") or "")),
            "document_source": str(d.get("document_source") or ""),
        }
        for d in docs
    ]

    grouped: Dict[str, List[Dict[str, Any]]] = {"website": [], "intake_form": [], "drive": [], "other": []}
    for rec in summary_records:
        dt = str(rec.get("document_type") or "other")
        if dt not in grouped:
            grouped["other"].append(rec)
        else:
            grouped[dt].append(rec)

    json_payload: Dict[str, Any] = {
        "client_slug": client_slug,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "source": "case_studies_all_summary",
        "total_case_studies": len(summary_records),
        "counts_by_document_type": {k: len(v) for k, v in grouped.items()},
        "summaries_by_document_type": grouped,
        "summaries": summary_records,
    }
    try:
        saved_path = await asyncio.to_thread(
            _persist_case_studies_summary_json_sync,
            client_slug=client_slug,
            payload=json_payload,
        )
        log("query.case_studies_all.saved", {"client_slug": client_slug, "path": saved_path, "count": len(summary_records)})
    except Exception as e:
        log("query.case_studies_all.save_error", {"client_slug": client_slug, "error": str(e)})

    if stream:
        async def streamer():
            yield f"8:{json.dumps({'sources': sources})}\n"
            yield f"0:{json.dumps(answer)}\n"
        return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")

    return JSONResponse({"answer": answer, "sources": sources})


@router.post("/summarize-all-case-studies")
async def summarize_all_case_studies(payload: Dict[str, Any]) -> StreamingResponse:
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("namespace")
    stream: bool = bool(payload.get("stream", False))
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    log("query.case_studies_all.start", {"client_slug": client_slug, "stream": stream})
    return await _run_summarize_all_case_studies(client_slug=client_slug, stream=stream)


@router.post("/generate-brief-files")
async def generate_brief_files(payload: Dict[str, Any]) -> JSONResponse:
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("namespace")
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    slug = str(client_slug).strip()
    log("query.briefs.generate.start", {"client_slug": slug})

    # 1) Case studies
    case_resp = await _run_summarize_all_case_studies(client_slug=slug, stream=False)
    case_body = json.loads(case_resp.body.decode("utf-8")) if hasattr(case_resp, "body") else {}

    # 2) Intake form summary
    intake_result = await _summarize_intake_form_docs(client_slug=slug)

    # 3) Client materials summary
    materials_result = await _summarize_client_materials_docs(client_slug=slug)
    
    # 4) Website summary
    website_result = await _summarize_client_website_docs(client_slug=slug)

    # 5) Unique mechanism research
    unique_mechanism_result = await _generate_unique_mechanism_research(client_slug=slug)

    out = {
        "ok": True,
        "client_slug": slug,
        "generated": {
            "case_studies_all": {
                "saved_path": f"{slug}/client_brief/case_studies_all.json",
                "sources_count": len((case_body or {}).get("sources") or []),
            },
            "intake_form_summary": intake_result,
            "client_materials_summary": materials_result,
            "website_summary": website_result,
            "unique_mechanism_research": unique_mechanism_result,
        },
    }
    log("query.briefs.generate.done", {"client_slug": slug, "out": out.get("generated")})
    return JSONResponse(out)


@router.post("/summarize-website")
async def summarize_website(payload: Dict[str, Any]) -> JSONResponse:
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("namespace")
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    slug = str(client_slug).strip()
    log("query.website_summary.start", {"client_slug": slug})
    result = await _summarize_client_website_docs(client_slug=slug)
    out = {"ok": True, "client_slug": slug, "website_summary": result}
    log("query.website_summary.done", {"client_slug": slug, "result": result})
    return JSONResponse(out)


@router.post("/summarize-client-intake")
async def summarize_client_intake(payload: Dict[str, Any]) -> JSONResponse:
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("namespace")
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    slug = str(client_slug).strip()
    log("query.intake_summary.start", {"client_slug": slug})
    result = await _summarize_intake_form_docs(client_slug=slug)
    out = {"ok": True, "client_slug": slug, "intake_form_summary": result}
    log("query.intake_summary.done", {"client_slug": slug, "result": result})
    return JSONResponse(out)


@router.post("/summarize-client-materials")
async def summarize_client_materials(payload: Dict[str, Any]) -> JSONResponse:
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("namespace")
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    slug = str(client_slug).strip()
    log("query.materials_summary.start", {"client_slug": slug})
    result = await _summarize_client_materials_docs(client_slug=slug)
    out = {"ok": True, "client_slug": slug, "client_materials_summary": result}
    log("query.materials_summary.done", {"client_slug": slug, "result": result})
    return JSONResponse(out)


@router.post("/research-unique-mechanisms")
async def research_unique_mechanisms(payload: Dict[str, Any]) -> JSONResponse:
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("namespace")
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    slug = str(client_slug).strip()
    log("query.unique_mechanism_research.start", {"client_slug": slug})
    result = await _generate_unique_mechanism_research(client_slug=slug)
    out = {"ok": True, "client_slug": slug, "unique_mechanism_research": result}
    log("query.unique_mechanism_research.done", {"client_slug": slug, "result": result})
    return JSONResponse(out)


@router.post("/query")
async def query(payload: Dict[str, Any]) -> StreamingResponse:
    settings = get_settings()

    query_text: Optional[str] = payload.get("query")
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("namespace")
    index_name: Optional[str] = payload.get("index")
    agent_type: str = str(payload.get("agentType") or payload.get("agent_type") or "inbox_manager")
    stream: bool = bool(payload.get("stream", False))
    enable_rewrite: bool = bool(payload.get("queryRewrite", payload.get("query_rewrite", True)))
    # Optional filters
    content_type: Optional[str] = payload.get("contentType") or payload.get("content_type")
    document_source: Optional[str] = payload.get("documentSource") or payload.get("document_source")
    keywords_in: Any = payload.get("keywords") or payload.get("keyword") or payload.get("keywordsAny")

    # Support chat-style payloads
    if not query_text:
        messages = payload.get("messages")
        if isinstance(messages, list):
            user_messages = [m for m in messages if isinstance(m, dict) and m.get("role") == "user"]
            if user_messages:
                query_text = user_messages[-1].get("content")

    if not query_text or not client_slug:
        raise HTTPException(status_code=400, detail="Query and clientSlug/index are required")

    conversation_history = _build_conversation_history_block(payload.get("messages"))

    log("query.start", {"client_slug": client_slug, "query_len": len(query_text), "agent_type": agent_type})

    # Build Pinecone filter (metadata filtering)
    pc_filter: Dict[str, Any] = {}
    if content_type:
        pc_filter["content_type"] = {"$eq": str(content_type)}
    if document_source:
        pc_filter["document_source"] = {"$eq": str(document_source)}
    # keywords is stored as a string list; support filtering where ANY keyword matches
    keywords_list: List[str] = []
    if isinstance(keywords_in, str) and keywords_in.strip():
        # allow "a,b,c" or single
        keywords_list = [k.strip().lower() for k in keywords_in.split(",") if k.strip()]
    elif isinstance(keywords_in, list):
        keywords_list = [str(k).strip().lower() for k in keywords_in if str(k).strip()]
    if keywords_list:
        pc_filter["keywords"] = {"$in": keywords_list}

    # Special handling: "summarize N case studies" needs doc-level retrieval, not just 5 random chunks.
    case_study_mode = _looks_like_case_study_summary_request(query_text)
    pricing_mode = _looks_like_pricing_summary_request(query_text)
    all_case_studies_mode = _looks_like_all_case_studies_request(query_text)
    if case_study_mode and all_case_studies_mode:
        log("query.case_studies_all.redirect", {"client_slug": client_slug, "query": _preview_text(query_text, 200)})
        return await _run_summarize_all_case_studies(client_slug=client_slug, stream=stream)
    requested_n = _parse_requested_case_study_count(query_text) if case_study_mode else 0
    if case_study_mode:
        # Case-study intent always narrows retrieval to case-study content.
        pc_filter["content_type"] = {"$in": ["case_study", "case_studies"]}
    if pricing_mode:
        # Pricing intent should include dedicated pricing docs + intake form pricing sections.
        pc_filter["content_type"] = {"$in": ["pricing", "intake_form"]}

    log(
        "query.classification",
        {
            "client_slug": client_slug,
            "case_study_mode": case_study_mode,
            "pricing_mode": pricing_mode,
            "requested_case_studies": requested_n,
            "incoming_content_type": content_type,
            "incoming_document_source": document_source,
            "keywords_count": len(keywords_list),
            "effective_filter": pc_filter or None,
        },
    )

    # --- Query rewrite / expansion (retrieval only) ---
    # Keep the original user question for response generation and for case-study detection,
    # but use rewritten/expanded queries to improve retrieval.
    retrieval_queries: List[str] = [query_text]
    rewrite_meta: Dict[str, Any] = {"used": False}
    if pricing_mode or case_study_mode:
        retrieval_queries = _intent_seed_queries(
            query_text=query_text,
            pricing_mode=pricing_mode,
            case_study_mode=case_study_mode,
        )
        log(
            "query.rewrite.skipped_for_intent",
            {
                "client_slug": client_slug,
                "pricing_mode": pricing_mode,
                "case_study_mode": case_study_mode,
                "n_queries": len(retrieval_queries),
                "retrieval_queries": [_preview_text(q) for q in retrieval_queries],
            },
        )
    elif enable_rewrite:
        rewrite_meta = await _rewrite_queries_for_retrieval(query_text=query_text, max_expansions=2)
        rq = str(rewrite_meta.get("rewritten_query") or "").strip()
        exps = rewrite_meta.get("expansions") or []
        expanded: List[str] = []
        if isinstance(exps, list):
            expanded = [str(x).strip() for x in exps if isinstance(x, str) and str(x).strip()]
        # Order matters: rewritten first, then expansions, then original as fallback.
        ordered = [rq, *expanded, query_text]
        # De-dupe while preserving order
        seen: set[str] = set()
        retrieval_queries = []
        for q in ordered:
            qq = (q or "").strip()
            if not qq or qq in seen:
                continue
            seen.add(qq)
            retrieval_queries.append(qq)
        # Log only lengths to avoid leaking user content in logs
        try:
            log(
                "query.rewrite",
                {
                    "client_slug": client_slug,
                    "used": bool(rewrite_meta.get("used")),
                    "n_queries": len(retrieval_queries),
                    "orig_len": len(query_text),
                    "rw_len": len(rq),
                    "orig_preview": _preview_text(query_text),
                    "rewritten_preview": _preview_text(rq),
                    "expansion_previews": [_preview_text(x) for x in expanded[:2]],
                },
            )
        except Exception:
            pass

    # --- Retrieve context from Pinecone ---
    top_k_in = int(payload.get("topK") or 5)
    # For case study summaries we need enough chunks to cover multiple distinct docs.
    top_k = top_k_in
    if case_study_mode:
        top_k = max(top_k_in, min(120, max(30, requested_n * 10 if requested_n > 0 else 80)))
    elif pricing_mode:
        top_k = max(top_k_in, 100)
    metadata_filter_mode = bool(pc_filter)
    if metadata_filter_mode:
        # When metadata is explicitly filtered, expand recall to pull all chunks
        # from matching docs so context assembly can include complete doc text.
        top_k = max(top_k, 400)
    log(
        "query.retrieval.plan",
        {
            "client_slug": client_slug,
            "top_k_in": top_k_in,
            "top_k_effective": top_k,
            "n_retrieval_queries": len(retrieval_queries),
            "retrieval_queries": [_preview_text(q) for q in retrieval_queries[:5]],
            "pricing_mode": pricing_mode,
            "case_study_mode": case_study_mode,
            "metadata_filter_mode": metadata_filter_mode,
        },
    )

    _retrieval_t0 = time.monotonic()

    async def _search_one(q: str):
        return await asyncio.to_thread(
            pinecone_kb_client.search,
            client_slug=client_slug,
            query=q,
            top_k=top_k,
            filter=pc_filter or None,
            fields=["text", "title", "url", "file_key", "content_type", "document_source", "chunk_index"],
            # Pinecone eventual consistency: if user queries right after ingestion, retry once after 10s
            wait_after_upsert_s=0.0,
        )

    if pricing_mode:
        intake_filter = dict(pc_filter or {})
        intake_filter["document_source"] = {"$eq": "intake_form"}
        log(
            "query.retrieval.requests.pricing",
            {
                "client_slug": client_slug,
                "top_k": top_k,
                "general_requests": [
                    {"query": _preview_text(q, 180), "filter": pc_filter or None}
                    for q in retrieval_queries
                ],
                "intake_requests": [
                    {"query": _preview_text(q, 180), "filter": intake_filter or None}
                    for q in retrieval_queries
                ],
            },
        )

        async def _search_pricing_intake(q: str):
            return await asyncio.to_thread(
                pinecone_kb_client.search,
                client_slug=client_slug,
                query=q,
                top_k=top_k,
                filter=intake_filter or None,
                fields=["text", "title", "url", "file_key", "content_type", "document_source", "chunk_index"],
                wait_after_upsert_s=0.0,
            )

        intake_lists, general_lists = await asyncio.gather(
            asyncio.gather(*[_search_pricing_intake(q) for q in retrieval_queries]),
            asyncio.gather(*[_search_one(q) for q in retrieval_queries]),
        )
        log(
            "query.retrieval.raw_counts.pricing",
            {
                "client_slug": client_slug,
                "per_query_intake_hits": [len(x or []) for x in intake_lists],
                "per_query_general_hits": [len(x or []) for x in general_lists],
                "first_hits_intake": _summarize_first_hit_per_query(list(intake_lists)),
                "first_hits_general": _summarize_first_hit_per_query(list(general_lists)),
            },
        )
        intake_hits = _merge_hits_by_record_id(list(intake_lists))
        general_hits = _merge_hits_by_record_id(list(general_lists))
        hits = _merge_hits_by_record_id([intake_hits, general_hits])
        # Prioritize intake_form chunks in final ranking while preserving score ordering.
        hits.sort(
            key=lambda h: (
                1 if str((getattr(h, "fields", {}) or {}).get("document_source") or "").strip() == "intake_form" else 0,
                float(getattr(h, "score", 0.0) or 0.0),
            ),
            reverse=True,
        )
    else:
        log(
            "query.retrieval.requests",
            {
                "client_slug": client_slug,
                "top_k": top_k,
                "requests": [
                    {"query": _preview_text(q, 180), "filter": pc_filter or None}
                    for q in retrieval_queries
                ],
            },
        )
        hit_lists = await asyncio.gather(*[_search_one(q) for q in retrieval_queries])
        log(
            "query.retrieval.raw_counts",
            {
                "client_slug": client_slug,
                "per_query_hits": [len(x or []) for x in hit_lists],
                "first_hits": _summarize_first_hit_per_query(list(hit_lists)),
            },
        )
        hits = _merge_hits_by_record_id(list(hit_lists))

    # If the user asks a very open-ended “what do you do / services” question,
    # bias retrieval toward likely overview pages (services/about/homepage) if initial retrieval is weak.
    if _is_open_ended_services_question(query_text) and not case_study_mode and not pricing_mode and not content_type:
        try:
            boosted_filter = dict(pc_filter or {})
            boosted_filter["content_type"] = {"$in": ["homepage", "services_products", "about"]}
            # Add a couple “overview” flavored queries to help the retriever land on service pages.
            boosted_queries = []
            for q in retrieval_queries:
                boosted_queries.append(q)
            boosted_queries.extend(
                [
                    "services overview what we do",
                    "products services offerings",
                ]
            )
            # De-dupe boosted queries
            seen_b: set[str] = set()
            deduped_boosted: List[str] = []
            for raw in boosted_queries:
                qq = (raw or "").strip()
                if not qq:
                    continue
                if qq in seen_b:
                    continue
                seen_b.add(qq)
                deduped_boosted.append(qq)
            boosted_queries = deduped_boosted
            boosted_lists = await asyncio.gather(
                *[
                    asyncio.to_thread(
                        pinecone_kb_client.search,
                        client_slug=client_slug,
                        query=q,
                        top_k=top_k,
                        filter=boosted_filter,
                        fields=["text", "title", "url", "file_key", "content_type", "document_source", "chunk_index"],
                        wait_after_upsert_s=0.0,
                    )
                    for q in boosted_queries[:4]
                ]
            )
            if hits:
                hits = _merge_hits_by_record_id([hits, *list(boosted_lists)])
            else:
                hits = _merge_hits_by_record_id(list(boosted_lists))
        except Exception as e:
            log("query.retrieval.boost.error", {"error": str(e)})

    if not hits:
        log("query.retrieval.empty_first_pass", {"client_slug": client_slug, "retrying_after_s": 10})
        await asyncio.sleep(10)
        if pricing_mode:
            intake_filter = dict(pc_filter or {})
            intake_filter["document_source"] = {"$eq": "intake_form"}
            intake_retry, general_retry = await asyncio.gather(
                asyncio.gather(
                    *[
                        asyncio.to_thread(
                            pinecone_kb_client.search,
                            client_slug=client_slug,
                            query=q,
                            top_k=top_k,
                            filter=intake_filter or None,
                            fields=["text", "title", "url", "file_key", "content_type", "document_source", "chunk_index"],
                            wait_after_upsert_s=0.0,
                        )
                        for q in retrieval_queries
                    ]
                ),
                asyncio.gather(*[_search_one(q) for q in retrieval_queries]),
            )
            log(
                "query.retrieval.retry_counts.pricing",
                {
                    "client_slug": client_slug,
                    "per_query_intake_hits": [len(x or []) for x in intake_retry],
                    "per_query_general_hits": [len(x or []) for x in general_retry],
                },
            )
            hits = _merge_hits_by_record_id([_merge_hits_by_record_id(list(intake_retry)), _merge_hits_by_record_id(list(general_retry))])
            hits.sort(
                key=lambda h: (
                    1 if str((getattr(h, "fields", {}) or {}).get("document_source") or "").strip() == "intake_form" else 0,
                    float(getattr(h, "score", 0.0) or 0.0),
                ),
                reverse=True,
            )
        else:
            hit_lists = await asyncio.gather(*[_search_one(q) for q in retrieval_queries])
            log(
                "query.retrieval.retry_counts",
                {
                    "client_slug": client_slug,
                    "per_query_hits": [len(x or []) for x in hit_lists],
                },
            )
            hits = _merge_hits_by_record_id(list(hit_lists))

    _retrieval_latency_ms = (time.monotonic() - _retrieval_t0) * 1000.0
    log("query.retrieval.summary", {"client_slug": client_slug, **_summarize_hits(hits, max_items=8)})

    # Emit retrieval trace for eval / A-B testing
    try:
        _trace = build_trace_from_hits(
            hits=hits,
            client_slug=client_slug,
            query_original=str(payload.get("query") or ""),
            query_rewritten=str(rewrite_meta.get("rewritten_query") or ""),
            retrieval_queries=retrieval_queries,
            top_k=top_k,
            index_name=str(index_name or settings.pinecone_kb_index_name or ""),
            filter=pc_filter,
            latency_ms=_retrieval_latency_ms,
            case_study_mode=case_study_mode,
            pricing_mode=pricing_mode,
            metadata_filter_mode=metadata_filter_mode,
            query_rewrite_used=bool(rewrite_meta.get("used")),
            experiment_tag=str(payload.get("experimentTag") or payload.get("experiment_tag") or ""),
        )
        await asyncio.to_thread(write_trace, _trace)
    except Exception as _eval_err:
        log("query.eval.trace_error", {"error": str(_eval_err)})

    # Build sources + context string
    sources: List[Dict[str, Any]] = []
    context_blocks: List[str] = []
    if case_study_mode:
        # Prefer doc-level, numbered context so the model can actually summarize multiple distinct case studies.
        if requested_n > 0:
            sources, context_blocks = _build_case_study_summaries_context(
                hits=hits,
                max_docs=requested_n,
                chunks_per_doc=0 if metadata_filter_mode else 3,
            )
        else:
            sources, context_blocks = _build_doc_summaries_context(
                hits=hits,
                max_docs=0,
                chunks_per_doc=0 if metadata_filter_mode else 3,
            )
        if sources:
            # Strong instruction: produce N summaries, cite using [n]
            if len(sources) == 1:
                query_text = (
                    f"{query_text}\n\n"
                    "IMPORTANT: Summarize the single case study in the context below.\n"
                    f"{_CASE_STUDY_SUMMARY_FORMAT_INSTRUCTIONS}\n"
                    "Use only grounded details from the context and keep output concise but complete.\n"
                )
            else:
                query_text = (
                    f"{query_text}\n\n"
                    f"IMPORTANT: Summarize {len(sources)} distinct case studies from the context below.\n"
                    f"{_CASE_STUDY_SUMMARY_FORMAT_INSTRUCTIONS}\n"
                    "For multiple case studies, present one clearly separated block per case study and cite with [1], [2], etc.\n"
                )
    elif pricing_mode:
        # Summarize all pricing documents, with intake_form chunks already prioritized.
        sources, context_blocks = _build_doc_summaries_context(
            hits=hits,
            max_docs=0,
            chunks_per_doc=0 if metadata_filter_mode else 8,
            prioritize_scored_chunks=True,
        )
        if sources:
            query_text = (
                f"{query_text}\n\n"
                "IMPORTANT: Summarize all pricing information from the provided sources. "
                "Prioritize intake form pricing details when there are conflicts. "
                "For each source, include: pricing model, starting costs, average order value, package tiers, and caveats if present. "
                "Cite sources as [1], [2], etc.\n"
            )
    else:
        for h in hits:
            f = h.fields
            title = f.get("title") or f.get("file_key") or "Source"
            url_out = f.get("url") or f.get("file_key") or ""
            snippet = (f.get("text") or "")[:250]
            sources.append({"title": title, "url": url_out, "snippet": snippet})
            context_blocks.append(f"[{title}] {snippet}")

    system_prompt = _system_prompt_for(agent_type)
    history_prefix = ""
    if conversation_history:
        history_prefix = (
            "Conversation so far (for continuity/reference resolution only):\n"
            f"{conversation_history}\n\n"
            "Use retrieved context as the source of truth for factual claims.\n\n"
        )
    user_prompt = f"{history_prefix}User question:\n{query_text}\n\nContext:\n" + "\n\n".join(context_blocks)

    if stream:
        async def streamer():
            # Send sources up-front in the format the frontend expects.
            yield f"8:{json.dumps({'sources': sources})}\n"
            try:
                async for delta in llm_client.stream_answer(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=settings.ai_temperature,
                    max_tokens=settings.ai_max_tokens,
                ):
                    yield f"0:{json.dumps(delta)}\n"
            except Exception as e:
                log("query.stream.error", {"error": str(e)})
                yield '0:"[error generating response]"\n'

        return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")

    resp = await llm_client.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=settings.ai_temperature,
        max_tokens=settings.ai_max_tokens,
        model="gpt-4o-mini",
    )
    answer = resp["choices"][0]["message"]["content"]
    return JSONResponse({"answer": answer, "sources": sources})
