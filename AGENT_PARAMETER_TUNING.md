# Agent Generation Parameter Tuning Guide

## Problem
Agents not responding to queries even when relevant information is available in the Knowledge Base.

## Recommended Parameters for Customer Support Agents

### Temperature: `0.3` (Low, Deterministic)
**What it does**: Controls randomness in responses
- `0.0` = Completely deterministic, same answer every time
- `1.0` = More creative/random
- `2.0` = Very random (not recommended)

**Why 0.3 for customer support**:
- ✅ Consistent, reliable answers
- ✅ Stays focused on KB content
- ✅ Less likely to hallucinate
- ✅ Professional, predictable tone

**When to adjust**:
- **Lower to 0.1-0.2**: If agents are being too creative or straying from facts
- **Raise to 0.5-0.7**: If responses feel too robotic or you want more varied phrasing

### Top-P: `0.8` (Moderate Nucleus Sampling)
**What it does**: Limits token selection to top probability mass
- `0.1` = Very focused, only highest probability words
- `0.9-1.0` = More diverse word choice

**Why 0.8 for customer support**:
- ✅ Good balance of precision and natural language
- ✅ Allows some variation in phrasing
- ✅ Prevents overly repetitive responses
- ✅ Still maintains accuracy

**When to adjust**:
- **Lower to 0.6-0.7**: If responses are too wordy or straying off-topic
- **Raise to 0.9**: If responses feel too constrained

### Max Tokens: `1024` (Medium Length)
**What it does**: Maximum length of response
- `256` = Short, concise answers
- `512` = Medium paragraphs
- `1024` = Longer, detailed responses
- `2048+` = Very long responses

**Why 1024 for customer support**:
- ✅ Enough room for complete, helpful answers
- ✅ Can include examples and details
- ✅ Not so long that customers lose interest
- ✅ Good for multi-part questions

**When to adjust**:
- **Lower to 512**: If responses are too verbose
- **Raise to 2048**: If you need very detailed technical explanations

### K (Retrieval): `10` (Already configured)
**What it does**: Number of KB chunks to retrieve
- Your current setting of `10` is good
- Consider raising to `15-20` if agents can't find relevant info

## Configuration

### Via Environment Variables (.env)
```bash
# Recommended for customer support
DIGITALOCEAN_AGENT_TEMPERATURE=0.3
DIGITALOCEAN_AGENT_TOP_P=0.8
DIGITALOCEAN_AGENT_MAX_TOKENS=1024

# Already configured
DIGITALOCEAN_AGENT_K=10
```

### For Different Use Cases

#### **Technical Support** (Very Precise)
```bash
DIGITALOCEAN_AGENT_TEMPERATURE=0.1
DIGITALOCEAN_AGENT_TOP_P=0.7
DIGITALOCEAN_AGENT_MAX_TOKENS=1024
DIGITALOCEAN_AGENT_K=15
```

#### **Sales/Marketing** (More Creative)
```bash
DIGITALOCEAN_AGENT_TEMPERATURE=0.7
DIGITALOCEAN_AGENT_TOP_P=0.9
DIGITALOCEAN_AGENT_MAX_TOKENS=512
DIGITALOCEAN_AGENT_K=8
```

#### **Concise FAQ Bot**
```bash
DIGITALOCEAN_AGENT_TEMPERATURE=0.2
DIGITALOCEAN_AGENT_TOP_P=0.7
DIGITALOCEAN_AGENT_MAX_TOKENS=256
DIGITALOCEAN_AGENT_K=5
```

## Troubleshooting Non-Responsive Agents

If agents still aren't responding after tuning parameters:

### 1. **Check KB Attachment**
```bash
cd backend && source venv/bin/activate
python -c "
from app.clients.digital_ocean_client import do_client
import asyncio

async def check():
    agents = await do_client.list_agents()
    for a in agents:
        kbs = a.get('knowledge_base_uuids', [])
        print(f\"{a['name']}: {len(kbs)} KB(s) attached\")

asyncio.run(check())
"
```

### 2. **Verify KB Indexing**
```bash
python -c "
from app.clients.digital_ocean_client import do_client
import asyncio

async def check():
    kb_uuid = 'YOUR_KB_UUID'
    kb = await do_client.get_knowledge_base(kb_uuid)
    job = kb.get('last_indexing_job', {})
    print(f\"Status: {job.get('status')}\")
    print(f\"Finished: {job.get('finished_at')}\")

asyncio.run(check())
"
```

### 3. **Increase K Value**
If information exists but isn't being retrieved:
```bash
DIGITALOCEAN_AGENT_K=20  # Retrieve more chunks
```

### 4. **Check Retrieval Method**
Current setting: `RETRIEVAL_METHOD_REWRITE` (query rewriting)

Alternative: `RETRIEVAL_METHOD_VANILLA` (direct search)
```bash
DIGITALOCEAN_AGENT_RETRIEVAL_METHOD=RETRIEVAL_METHOD_VANILLA
```

## Testing After Changes

1. **Recreate agents** with new parameters:
```bash
# Agents created before config changes won't have new parameters
cd backend && source venv/bin/activate
python scripts/create_inbox_manager_agents.py --client test-client
```

2. **Test queries**:
```bash
curl -X POST "https://AGENT_ENDPOINT/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "messages": [
      {"role": "user", "content": "What services do you offer?"}
    ]
  }'
```

3. **Check agent logs** in DigitalOcean console for:
   - Number of KB chunks retrieved
   - Retrieval scores
   - Any errors

## Interaction Between Parameters

### Temperature + Top-P
- Both control randomness, but differently
- **Best practice**: Use one OR the other as primary control
- **Recommended**: Keep temperature low (0.3) and adjust top_p for fine-tuning

### Max Tokens + Response Quality
- Too low: Incomplete answers, truncated mid-sentence
- Too high: Rambling, off-topic content
- **Sweet spot**: 512-1024 for most use cases

### K + Performance
- Higher K = More context but slower responses
- Lower K = Faster but might miss relevant info
- **Balance**: 10-15 for most use cases

## Monitoring and Iteration

1. **Track metrics**:
   - Response rate (% of queries that get answers)
   - User satisfaction
   - Response length
   - Time to respond

2. **A/B test parameters**:
   - Create test agents with different settings
   - Compare performance
   - Iterate based on results

3. **Client-specific tuning**:
   - Some clients may need different parameters
   - Consider per-client configuration in future

