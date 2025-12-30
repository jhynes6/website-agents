# 3-Agent Reply System with Pinecone Assistants

## Overview

This implements a **3-stage intelligent reply generation system** using Pinecone Assistants. Each stage specializes in a specific aspect of reply generation, ensuring high-quality, accurate, and professionally polished responses.

---

## Architecture

```
User Message
     ↓
┌────────────────────┐
│  1. DRAFT AGENT    │ ← Pinecone Assistant with RAG
│  Generate Reply    │ → Initial draft + citations
└────────────────────┘
     ↓
┌────────────────────┐
│  2. QA AGENT       │ ← Same Assistant, QA mode
│  Quality Check     │ → Accuracy assessment + suggestions
└────────────────────┘
     ↓
┌────────────────────┐
│  3. FINALIZE AGENT │ ← Same Assistant, Polish mode
│  Polish & Style    │ → Final polished reply
└────────────────────┘
     ↓
Final Professional Reply
```

---

## The Three Agents

### 1. Draft Agent (`/assistant-chat/draft`)

**Purpose**: Generate initial reply using RAG

**What it does**:
- Accesses full client knowledge base via Pinecone Assistant
- Uses built-in RAG to find relevant context
- Generates contextually appropriate draft reply
- Provides source citations

**Advantages over inbox_manager/draft**:
- ✅ Built-in file management (no manual upload needed)
- ✅ Automatic chunking and embedding
- ✅ Better citation tracking
- ✅ Managed infrastructure

**Example Request**:
```json
POST /api/mintagent/assistant-chat/draft
{
  "clientSlug": "a-perfect-promotion",
  "messages": [
    {
      "role": "user",
      "content": "I need promotional products for a trade show"
    }
  ],
  "model": "gpt-4o-mini"
}
```

**Example Response**:
```json
{
  "draft": "Thank you for your interest...",
  "citations": [
    {
      "file_name": "services.md",
      "pages": [1, 2],
      "metadata": {...}
    }
  ],
  "finish_reason": "stop",
  "usage": {
    "prompt_tokens": 1234,
    "completion_tokens": 567,
    "total_tokens": 1801
  }
}
```

---

### 2. QA Agent (`/assistant-chat/qa`)

**Purpose**: Quality check draft for accuracy and completeness

**What it does**:
- Verifies facts against knowledge base
- Identifies inaccuracies or hallucinations
- Detects missing important information
- Provides improvement suggestions
- Calculates confidence score

**Advantages over inbox_manager_qa**:
- ✅ Uses same assistant (consistent knowledge)
- ✅ Structured JSON output
- ✅ Detailed confidence scoring
- ✅ Specific actionable suggestions

**Example Request**:
```json
POST /api/mintagent/assistant-chat/qa
{
  "clientSlug": "a-perfect-promotion",
  "draft": "Thank you for your interest...",
  "originalMessage": "I need promotional products..."
}
```

**Example Response**:
```json
{
  "qa_result": {
    "is_accurate": true,
    "confidence": 0.92,
    "inaccuracies": [],
    "missing_info": ["Pricing information", "Timeline details"],
    "suggestions": [
      "Add estimated turnaround time",
      "Mention minimum order quantities"
    ],
    "overall_assessment": "Draft is accurate but could include more details"
  },
  "is_accurate": true,
  "suggestions": [...],
  "confidence": 0.92
}
```

---

### 3. Finalize Agent (`/assistant-chat/finalize`)

**Purpose**: Polish reply for tone, style, and professionalism

**What it does**:
- Incorporates QA feedback
- Adjusts tone and style
- Improves formatting and structure
- Enhances clarity and engagement
- Ensures professional email etiquette

**Tone Options**:
- `professional` (default) - Business professional
- `friendly` - Warm and approachable
- `formal` - Very formal and diplomatic

**Example Request**:
```json
POST /api/mintagent/assistant-chat/finalize
{
  "clientSlug": "a-perfect-promotion",
  "draft": "Thank you for your interest...",
  "qaFeedback": {
    "suggestions": ["Add pricing info", "Mention timeline"]
  },
  "tone": "professional"
}
```

**Example Response**:
```json
{
  "finalReply": "Thank you for reaching out...",
  "changes": [
    "Added pricing range information",
    "Included typical turnaround time",
    "Improved opening paragraph flow",
    "Added professional closing"
  ],
  "reasoning": "Incorporated QA suggestions and improved professional tone"
}
```

---

## Full Pipeline Endpoint

### `/assistant-chat/full-pipeline`

Orchestrates all three stages automatically.

**Advantages**:
- Single API call
- Automatic error handling
- Execution trace for debugging
- Optional stage skipping

**Example Request**:
```json
POST /api/mintagent/assistant-chat/full-pipeline
{
  "clientSlug": "a-perfect-promotion",
  "messages": [
    {"role": "user", "content": "What do you offer?"}
  ],
  "tone": "professional",
  "skipQA": false,
  "skipFinalize": false
}
```

**Example Response**:
```json
{
  "draft": {
    "draft": "...",
    "citations": [...]
  },
  "qa": {
    "is_accurate": true,
    "confidence": 0.92,
    ...
  },
  "final": {
    "finalReply": "...",
    "changes": [...],
    "reasoning": "..."
  },
  "pipeline_trace": [
    {"stage": "draft", "status": "success"},
    {"stage": "qa", "status": "success"},
    {"stage": "finalize", "status": "success"}
  ]
}
```

---

## Usage Examples

### Python SDK

```python
import httpx
import asyncio

async def generate_reply(client_slug: str, message: str):
    backend_url = "http://localhost:8000/api/mintagent"
    
    # Use full pipeline
    response = await httpx.post(
        f"{backend_url}/assistant-chat/full-pipeline",
        json={
            "clientSlug": client_slug,
            "messages": [{"role": "user", "content": message}],
            "tone": "professional"
        },
        timeout=120
    )
    
    result = response.json()
    final_reply = result["final"]["finalReply"]
    
    return final_reply

# Usage
reply = asyncio.run(generate_reply("a-perfect-promotion", "Tell me about your services"))
print(reply)
```

### Individual Stages

```python
# Stage 1: Draft
draft_response = await httpx.post(
    f"{backend_url}/assistant-chat/draft",
    json={"clientSlug": "client-slug", "messages": [...]},
    timeout=60
)
draft = draft_response.json()["draft"]

# Stage 2: QA
qa_response = await httpx.post(
    f"{backend_url}/assistant-chat/qa",
    json={
        "clientSlug": "client-slug",
        "draft": draft,
        "originalMessage": "..."
    },
    timeout=60
)
qa_result = qa_response.json()

# Stage 3: Finalize (only if QA passes)
if qa_result["is_accurate"]:
    finalize_response = await httpx.post(
        f"{backend_url}/assistant-chat/finalize",
        json={
            "clientSlug": "client-slug",
            "draft": draft,
            "qaFeedback": qa_result["qa_result"],
            "tone": "professional"
        },
        timeout=60
    )
    final_reply = finalize_response.json()["finalReply"]
```

---

## Testing

### Test Individual Stages
```bash
python backend/scripts/test_3_agent_system.py --client a-perfect-promotion
```

### Test Orchestrated Pipeline Only
```bash
python backend/scripts/test_3_agent_system.py --orchestrated --client a-perfect-promotion
```

### Expected Output
```
🤖 Testing 3-Agent Reply System
Client: a-perfect-promotion
================================================================================

1️⃣  STAGE 1: DRAFT AGENT
--------------------------------------------------------------------------------
Generating initial reply...
✅ Draft generated (1234 chars)
📚 Citations: 3
📝 Draft:
Thank you for your interest...

2️⃣  STAGE 2: QA AGENT
--------------------------------------------------------------------------------
Quality checking draft for accuracy...
✅ QA complete
📊 Accuracy: ✓ PASS
📊 Confidence: 92.0%
💡 Suggestions: 2
   1. Add pricing range information
   2. Include typical turnaround time

3️⃣  STAGE 3: FINALIZE AGENT
--------------------------------------------------------------------------------
Polishing reply for tone and style...
✅ Finalization complete
✏️  Changes made: 4
📝 Changes:
   1. Added pricing range information
   2. Improved opening paragraph flow
   3. Enhanced professional closing
   4. Included timeline expectations

================================================================================
✅ 3-AGENT PIPELINE COMPLETE
================================================================================
```

---

## Comparison: inbox_manager vs Assistant Chat

| Feature | inbox_manager | assistant_chat |
|---------|---------------|----------------|
| **Draft Generation** | Custom RAG | Pinecone Assistant RAG |
| **File Management** | Manual (Pinecone Index) | Automatic (Assistant) |
| **Citations** | Manual extraction | Built-in |
| **QA Agent** | Separate DO agent | Same assistant |
| **Finalize Agent** | ❌ Not implemented | ✅ Implemented |
| **Setup Complexity** | High | Low |
| **Infrastructure** | Self-managed | Managed by Pinecone |
| **Cost** | Index + OpenAI | Assistant pricing |
| **Flexibility** | Full control | Managed service |

---

## When to Use Each System

### Use `inbox_manager` when:
- Need custom chunking/embedding logic
- Want granular control over retrieval
- Building custom UI/UX
- Already have existing infrastructure

### Use `assistant_chat` when:
- Want quick setup and deployment
- Need built-in file management
- Prefer managed infrastructure
- Building MVP or prototype
- Want automatic citation handling

---

## Prerequisites

### 1. Assistant Must Exist

Before using the system, ensure an assistant exists for the client:

```bash
# Check if assistant exists
curl "https://api.pinecone.io/assistant/assistants" \
  -H "Api-Key: $PINECONE_API_KEY"

# Create if missing
python backend/scripts/create_assistant.py a-perfect-promotion
```

### 2. Files Must Be Uploaded

The assistant needs documents:
```bash
# Upload files during ingestion
POST /api/mintagent/create
{
  "clientSlug": "a-perfect-promotion",
  "url": "https://aperfectpromotion.com"
}

# Or manually
python backend/scripts/create_assistant.py a-perfect-promotion --force
```

### 3. Environment Variables

```bash
PINECONE_API_KEY=pcsk_...  # Required
```

---

## Error Handling

### Assistant Not Found
```json
{
  "detail": "Failed to generate draft: Assistant 'client-slug' not found"
}
```
**Solution**: Create assistant first

### Rate Limiting
```json
{
  "detail": "Failed to generate draft: Rate limit exceeded"
}
```
**Solution**: Implement exponential backoff

### QA Parse Error
- System gracefully falls back to draft
- Continues to finalization stage
- Check `qa_raw` for debugging

### Finalization Failure
- Returns original draft as fallback
- Logs error for investigation
- Pipeline still succeeds

---

## Performance Considerations

### Latency
- Draft: ~3-5 seconds
- QA: ~2-4 seconds
- Finalize: ~2-4 seconds
- **Total**: ~7-13 seconds

### Optimization Strategies
1. **Skip QA** for simple queries (`skipQA: true`)
2. **Skip Finalize** for internal use (`skipFinalize: true`)
3. **Use caching** for common queries
4. **Parallel execution** (future enhancement)

### Cost
- Each stage = 1 assistant chat call
- Full pipeline = 3 calls
- Token usage scales with context size

---

## Future Enhancements

- [ ] Parallel QA and initial finalize
- [ ] Streaming responses for better UX
- [ ] Multi-language support
- [ ] Custom agent instructions per stage
- [ ] A/B testing different approaches
- [ ] Feedback loop for continuous improvement
- [ ] Integration with email clients
- [ ] Bulk processing for multiple messages

---

## Related Documentation

- **Pipeline**: `PIPELINE_DOCUMENTATION.md` - Full ingestion flow
- **Assistants**: `ASSISTANT_CREATION.md` - Creating assistants
- **Testing**: `test_3_agent_system.py` - Test script

---

**Last Updated**: 2025-12-30
**Version**: 1.0.0

