"""
3-Agent Reply System using Pinecone Index RAG

This implements a 3-stage reply generation system:
1. Draft Agent - Creates initial reply using Pinecone Index RAG
2. QA Agent - Quality checks the draft for accuracy
3. Finalize Agent - Polishes the reply for tone and style
"""
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..config import get_settings
from ..logging import log
from ..clients.pinecone_client import pinecone_kb_client
from ..clients.llm import llm_client

router = APIRouter()


@router.post("/assistant-chat/draft")
async def assistant_draft(payload: Dict[str, Any]) -> JSONResponse:
    """
    Stage 1: Create initial draft reply using Pinecone Index RAG.
    
    Retrieves relevant context from the client's Pinecone namespace and
    uses an LLM to generate a contextually relevant response with citations.
    
    Expected payload:
      - clientSlug: The client identifier (namespace in Pinecone)
      - messages: List of chat messages [{"role": "user", "content": "..."}]
      - model: Optional model override (default: gpt-4o-mini)
      - top_k: Number of context chunks to retrieve (default: 5)
      
    Returns:
      - draft: Generated reply text
      - citations: List of sources used
    """
    settings = get_settings()
    
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("client_slug")
    messages_raw = payload.get("messages", [])
    model = payload.get("model", "gpt-4o-mini")
    top_k = payload.get("top_k", 5)
    
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    if not messages_raw:
        raise HTTPException(status_code=400, detail="messages array is required")
    
    # Extract the latest user message for RAG query
    user_query = ""
    for msg in reversed(messages_raw):
        if isinstance(msg, dict) and msg.get("role") == "user":
            user_query = msg.get("content", "")
            break
    
    if not user_query:
        raise HTTPException(status_code=400, detail="No user message found")
    
    log("assistant.draft.start", {
        "client_slug": client_slug,
        "message_count": len(messages_raw),
        "query_length": len(user_query)
    })
    
    try:
        # Retrieve context from Pinecone
        hits = pinecone_kb_client.search(
            client_slug=client_slug,
            query=user_query,
            top_k=top_k,
            filter=None,
            fields=["text", "title", "url", "doc_id", "content_type", "document_source", "chunk_index"],
            wait_after_upsert_s=0.0,
        )
        
        # Build citations and context
        citations = []
        context_blocks = []
        for h in hits:
            f = h.fields
            title = f.get("title") or f.get("doc_id") or "Source"
            url = f.get("url") or f.get("doc_id") or ""
            text_snippet = (f.get("text") or "")[:500]
            
            citations.append({
                "title": title,
                "url": url,
                "snippet": text_snippet,
                "score": h.score,
                "doc_id": f.get("doc_id"),
                "content_type": f.get("content_type")
            })
            
            context_blocks.append(f"Title: {title}\nURL: {url}\nContent: {f.get('text')}")
        
        # Build system prompt for draft generation
        system_prompt = (
            "You are a helpful customer service assistant. "
            "Generate a professional, friendly draft reply to the customer's question. "
            "Use ONLY the provided knowledge base context for factual claims. "
            "If the context doesn't contain enough information, acknowledge what you can help with "
            "and politely ask for clarification or offer to connect them with someone who can help. "
            "Be concise but thorough. Cite sources when making specific claims."
        )
        
        # Build conversation for LLM
        llm_messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in messages_raw:
            if isinstance(msg, dict):
                llm_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # Append context to the last user message
        if context_blocks:
            context_str = "\n\nKnowledge base context:\n" + "\n\n".join(context_blocks)
            llm_messages[-1]["content"] += context_str
        else:
            llm_messages[-1]["content"] += "\n\nKnowledge base context: (No relevant information found)"
        
        # Generate draft with LLM
        resp = await llm_client.chat(
            messages=llm_messages,
            temperature=settings.ai_temperature,
            max_tokens=min(settings.ai_max_tokens, 1000),
            model=model,
        )
        
        draft = (resp["choices"][0]["message"]["content"] or "").strip()
        
        log("assistant.draft.success", {
            "client_slug": client_slug,
            "draft_length": len(draft),
            "citations": len(citations)
        })
        
        return JSONResponse({
            "draft": draft,
            "citations": citations,
            "usage": resp.get("usage", {})
        })
        
    except Exception as e:
        log("assistant.draft.error", {"client_slug": client_slug, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to generate draft: {str(e)}")


@router.post("/assistant-chat/qa")
async def assistant_qa(payload: Dict[str, Any]) -> JSONResponse:
    """
    Stage 2: Quality check the draft reply for accuracy and completeness.
    
    Uses an LLM to verify the draft against best practices and identify
    any inaccuracies or missing information.
    
    Expected payload:
      - clientSlug: The client identifier
      - draft: The draft reply to check
      - originalMessage: The original user message
      - model: Optional model override (default: gpt-4o-mini)
      
    Returns:
      - qa_result: Structured QA assessment
      - is_accurate: Boolean indicating if draft is accurate
      - suggestions: List of improvement suggestions
      - confidence: Confidence score (0-1)
    """
    settings = get_settings()
    
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("client_slug")
    draft: Optional[str] = payload.get("draft") or payload.get("proposedReply")
    original_message: Optional[str] = payload.get("originalMessage") or payload.get("original_message")
    model = payload.get("model", "gpt-4o-mini")
    
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    if not draft:
        raise HTTPException(status_code=400, detail="draft is required")
    if not original_message:
        raise HTTPException(status_code=400, detail="originalMessage is required")
    
    # Create QA system prompt
    system_prompt = """You are a quality assurance agent for customer service responses. 
Your job is to review draft replies and provide structured feedback.

Evaluate the draft for:
1. Accuracy - Are claims reasonable and verifiable?
2. Completeness - Does it fully address the customer's question?
3. Tone - Is it professional and helpful?
4. Clarity - Is it easy to understand?
5. Actionability - Does it provide clear next steps?

Return your assessment as a JSON object with this exact structure:
{
  "is_accurate": boolean,
  "confidence": float between 0 and 1,
  "inaccuracies": ["list any questionable claims or errors"],
  "missing_info": ["list any important information that should be included"],
  "suggestions": ["list specific improvement suggestions"],
  "overall_assessment": "brief summary of your evaluation"
}

Return ONLY valid JSON, no other text or markdown formatting."""
    
    user_prompt = f"""Original Customer Message:
{original_message}

Draft Reply to Review:
{draft}

Please evaluate this draft reply and provide your assessment."""
    
    log("assistant.qa.start", {"client_slug": client_slug, "draft_length": len(draft)})
    
    try:
        # Call LLM for QA evaluation
        resp = await llm_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent evaluation
            max_tokens=min(settings.ai_max_tokens, 800),
            model=model
        )
        
        qa_raw = (resp["choices"][0]["message"]["content"] or "").strip()
        
        # Try to parse as JSON
        qa_result = None
        try:
            qa_result = json.loads(qa_raw)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', qa_raw, re.DOTALL)
            if json_match:
                qa_result = json.loads(json_match.group(1))
            else:
                # Fallback: return raw text
                qa_result = {
                    "is_accurate": True,
                    "confidence": 0.5,
                    "raw_response": qa_raw,
                    "suggestions": [],
                    "inaccuracies": [],
                    "missing_info": [],
                    "overall_assessment": "Unable to parse QA response"
                }
        
        log("assistant.qa.success", {
            "client_slug": client_slug,
            "is_accurate": qa_result.get("is_accurate", False),
            "confidence": qa_result.get("confidence", 0.5)
        })
        
        return JSONResponse({
            "qa_result": qa_result,
            "is_accurate": qa_result.get("is_accurate", False),
            "suggestions": qa_result.get("suggestions", []),
            "confidence": qa_result.get("confidence", 0.5),
            "qa_raw": qa_raw
        })
        
    except Exception as e:
        log("assistant.qa.error", {"client_slug": client_slug, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"QA check failed: {str(e)}")


@router.post("/assistant-chat/finalize")
async def assistant_finalize(payload: Dict[str, Any]) -> JSONResponse:
    """
    Stage 3: Finalize and polish the reply for tone, style, and professionalism.
    
    Takes the QA-approved draft and polishes it for:
    - Appropriate tone and style
    - Professional formatting
    - Clear and engaging language
    - Proper email etiquette
    
    Expected payload:
      - clientSlug: The client identifier
      - draft: The QA-approved draft
      - qaFeedback: Optional QA feedback to incorporate
      - tone: Optional tone guidance (professional/friendly/formal)
      - model: Optional model override (default: gpt-4o-mini)
      
    Returns:
      - finalReply: Polished final reply
      - changes: List of changes made
      - reasoning: Explanation of finalization decisions
    """
    settings = get_settings()
    
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("client_slug")
    draft: Optional[str] = payload.get("draft")
    qa_feedback = payload.get("qaFeedback") or payload.get("qa_feedback") or {}
    tone = payload.get("tone", "professional")
    model = payload.get("model", "gpt-4o-mini")
    
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    if not draft:
        raise HTTPException(status_code=400, detail="draft is required")
    
    # Create finalization system prompt
    system_prompt = f"""You are a professional communication editor specializing in customer service.
Your job is to polish draft replies to be clear, professional, and engaging.

Target tone: {tone}

Polish the draft for:
1. Appropriate tone and style
2. Professional but warm language
3. Clear and concise communication
4. Proper formatting and structure
5. Engaging and helpful presentation

Return your polished version as a JSON object with this exact structure:
{{
  "final_reply": "the polished reply text",
  "changes": ["list specific changes you made, e.g., 'Made tone more friendly', 'Fixed grammar in paragraph 2'"],
  "reasoning": "brief explanation of your key finalization decisions"
}}

Return ONLY valid JSON, no other text or markdown formatting."""
    
    user_prompt = f"""Draft to finalize:
{draft}"""
    
    if qa_feedback:
        suggestions = qa_feedback.get("suggestions", [])
        inaccuracies = qa_feedback.get("inaccuracies", [])
        missing_info = qa_feedback.get("missing_info", [])
        
        if suggestions or inaccuracies or missing_info:
            user_prompt += "\n\nQA Feedback to incorporate:"
            if inaccuracies:
                user_prompt += "\n- Fix these inaccuracies: " + ", ".join(inaccuracies)
            if missing_info:
                user_prompt += "\n- Add this missing information: " + ", ".join(missing_info)
            if suggestions:
                user_prompt += "\n- Improvements: " + ", ".join(suggestions)
    
    user_prompt += "\n\nPlease polish this draft and provide your finalized version."
    
    log("assistant.finalize.start", {
        "client_slug": client_slug,
        "draft_length": len(draft),
        "has_qa_feedback": bool(qa_feedback),
        "tone": tone
    })
    
    try:
        # Call LLM for finalization
        resp = await llm_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,  # Balanced temperature for creative polishing
            max_tokens=min(settings.ai_max_tokens, 1000),
            model=model
        )
        
        finalize_raw = (resp["choices"][0]["message"]["content"] or "").strip()
        
        # Try to parse as JSON
        finalize_result = None
        try:
            finalize_result = json.loads(finalize_raw)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', finalize_raw, re.DOTALL)
            if json_match:
                finalize_result = json.loads(json_match.group(1))
            else:
                # Fallback: use draft as final
                finalize_result = {
                    "final_reply": draft,
                    "changes": [],
                    "reasoning": "Could not parse finalization response, using draft as-is"
                }
        
        log("assistant.finalize.success", {
            "client_slug": client_slug,
            "changes_made": len(finalize_result.get("changes", []))
        })
        
        return JSONResponse({
            "finalReply": finalize_result.get("final_reply", draft),
            "changes": finalize_result.get("changes", []),
            "reasoning": finalize_result.get("reasoning", ""),
            "raw_response": finalize_raw
        })
        
    except Exception as e:
        log("assistant.finalize.error", {"client_slug": client_slug, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Finalization failed: {str(e)}")


@router.post("/assistant-chat/full-pipeline")
async def assistant_full_pipeline(payload: Dict[str, Any]) -> JSONResponse:
    """
    Execute the complete 3-agent pipeline: Draft → QA → Finalize.
    
    This orchestrates all three stages automatically and returns the final result.
    
    Expected payload:
      - clientSlug: The client identifier
      - messages: Chat messages for drafting
      - tone: Optional tone for finalization
      - skipQA: Optional flag to skip QA stage
      - skipFinalize: Optional flag to skip finalization
      
    Returns:
      - draft: Initial draft
      - qa: QA results (if not skipped)
      - final: Final polished reply
      - pipeline_trace: Execution trace
    """
    client_slug = payload.get("clientSlug") or payload.get("client_slug")
    messages = payload.get("messages", [])
    skip_qa = payload.get("skipQA", False)
    skip_finalize = payload.get("skipFinalize", False)
    
    if not client_slug or not messages:
        raise HTTPException(status_code=400, detail="clientSlug and messages are required")
    
    pipeline_trace = []
    
    # Stage 1: Draft
    log("assistant.pipeline.start", {"client_slug": client_slug, "stages": "draft-qa-finalize"})
    
    try:
        draft_result = await assistant_draft(payload)
        draft_data = json.loads(draft_result.body.decode())
        draft_text = draft_data.get("draft", "")
        pipeline_trace.append({"stage": "draft", "status": "success"})
    except Exception as e:
        pipeline_trace.append({"stage": "draft", "status": "error", "error": str(e)})
        raise
    
    # Stage 2: QA (optional)
    qa_data = None
    if not skip_qa:
        try:
            # Extract original message from conversation
            original_message = ""
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    original_message = msg.get("content", "")
                    break
            
            if not original_message:
                raise ValueError("No user message found in conversation")
            
            qa_payload = {
                "clientSlug": client_slug,
                "draft": draft_text,
                "originalMessage": original_message,
                "model": payload.get("model", "gpt-4o-mini")
            }
            qa_result = await assistant_qa(qa_payload)
            qa_data = json.loads(qa_result.body.decode())
            pipeline_trace.append({"stage": "qa", "status": "success"})
        except Exception as e:
            log("assistant.pipeline.qa_error", {"error": str(e)})
            pipeline_trace.append({"stage": "qa", "status": "error", "error": str(e)})
            # Continue even if QA fails
            pass
    
    # Stage 3: Finalize (optional)
    final_data = None
    if not skip_finalize:
        try:
            finalize_payload = {
                "clientSlug": client_slug,
                "draft": draft_text,
                "qaFeedback": qa_data.get("qa_result") if qa_data else None,
                "tone": payload.get("tone", "professional"),
                "model": payload.get("model", "gpt-4o-mini")
            }
            finalize_result = await assistant_finalize(finalize_payload)
            final_data = json.loads(finalize_result.body.decode())
            pipeline_trace.append({"stage": "finalize", "status": "success"})
        except Exception as e:
            log("assistant.pipeline.finalize_error", {"error": str(e)})
            pipeline_trace.append({"stage": "finalize", "status": "error", "error": str(e)})
            # Use draft if finalization fails
            final_data = {"finalReply": draft_text, "changes": [], "reasoning": "Finalization failed"}
    
    log("assistant.pipeline.complete", {
        "client_slug": client_slug,
        "stages_completed": len([t for t in pipeline_trace if t["status"] == "success"])
    })
    
    return JSONResponse({
        "draft": draft_data,
        "qa": qa_data,
        "final": final_data or {"finalReply": draft_text},
        "pipeline_trace": pipeline_trace
    })

