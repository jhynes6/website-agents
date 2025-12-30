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

### Top-K: `40` (Moderate Token Limiting)
**What it does**: Limits model to only consider the top K most likely tokens at each generation step
- `1` = Always pick the most likely token (deterministic)
- `10-20` = Very focused, limited vocabulary
- `40-50` = Balanced, good for customer support
- `100+` = Very diverse vocabulary

**Why 40 for customer support**:
- ✅ Provides good vocabulary diversity
- ✅ Prevents overly repetitive phrasing
- ✅ Still maintains professional tone
- ✅ Works well with temperature 0.3

**When to adjust**:
- **Lower to 20-30**: If responses are too creative or inconsistent
- **Raise to 60-80**: If responses feel too constrained or robotic

**⚠️ Note**: Top-P and Top-K work together. The model applies **both** filters:
1. First filters to top K tokens
2. Then applies top-P within those K tokens
3. Use **one as primary** and the other for fine-tuning

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
**What it does**: Number of KB chunks to retrieve for context
- **This is different from Top-K** (generation parameter above)
- Controls how much information from the Knowledge Base is given to the model

**Why 10 for customer support**:
- Your current setting of `10` is good for most queries
- Provides enough context without overwhelming the model

**When to adjust**:
- **Raise to 15-20**: If agents can't find relevant info or responses lack detail
- **Lower to 5-8**: If responses are too long or pulling irrelevant information

## Important: K vs Top-K

| Parameter | What It Controls | Range | Current Setting |
|-----------|-----------------|-------|-----------------|
| **K** (Retrieval) | Number of KB chunks retrieved | 1-50+ | **10** |
| **Top-K** (Generation) | Token selection during generation | 1-100+ | **40** |

**Don't confuse them!** They serve completely different purposes.

## Configuration

### Via Environment Variables (.env)
```bash
# Recommended for customer support
DIGITALOCEAN_AGENT_TEMPERATURE=0.3
DIGITALOCEAN_AGENT_TOP_P=0.8
DIGITALOCEAN_AGENT_TOP_K=40
DIGITALOCEAN_AGENT_MAX_TOKENS=1024

# Already configured (KB retrieval)
DIGITALOCEAN_AGENT_K=10
```

### For Different Use Cases

#### **Technical Support** (Very Precise)
```bash
DIGITALOCEAN_AGENT_TEMPERATURE=0.1
DIGITALOCEAN_AGENT_TOP_P=0.7
DIGITALOCEAN_AGENT_TOP_K=30
DIGITALOCEAN_AGENT_MAX_TOKENS=1024
DIGITALOCEAN_AGENT_K=15
```

#### **Sales/Marketing** (More Creative)
```bash
DIGITALOCEAN_AGENT_TEMPERATURE=0.7
DIGITALOCEAN_AGENT_TOP_P=0.9
DIGITALOCEAN_AGENT_TOP_K=60
DIGITALOCEAN_AGENT_MAX_TOKENS=512
DIGITALOCEAN_AGENT_K=8
```

#### **Concise FAQ Bot**
```bash
DIGITALOCEAN_AGENT_TEMPERATURE=0.2
DIGITALOCEAN_AGENT_TOP_P=0.7
DIGITALOCEAN_AGENT_TOP_K=30
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

### Temperature + Top-P + Top-K
- All three control randomness/diversity, but at different stages
- **Best practice**: Set temperature as primary control, use top-p and top-k for fine-tuning
- **Recommended**: Keep temperature low (0.3), top-p moderate (0.8), top-k moderate (40)

**How they work together**:
1. Model calculates probabilities for all possible next tokens
2. **Top-K filter**: Keeps only the top K most likely tokens
3. **Top-P filter**: Within those K tokens, keeps tokens until cumulative probability reaches P
4. **Temperature**: Adjusts the final probabilities before sampling

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

