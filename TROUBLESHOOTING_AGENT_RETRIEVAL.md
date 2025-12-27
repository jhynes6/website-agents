# Troubleshooting Agent Document Retrieval

## Problem
Agent logs showed: `"Retrieved 0 results from Knowledge Base"` when trying to retrieve documents.

## Root Cause
The agent (`inbox-manager-pi-lit`) was **not connected to any Knowledge Base**. Even though the KB (`pi-lit`) existed and was properly indexed, the agent had 0 KBs attached.

## Solution Steps

### 1. Check if Agent has KB Connected
```python
from app.clients.digital_ocean_client import do_client
import asyncio

async def check_agent():
    agents = await do_client.list_agents()
    agent = next((a for a in agents if 'pi-lit' in a['name']), None)
    
    if agent:
        kb_uuids = agent.get('knowledge_base_uuids', [])
        print(f"Agent has {len(kb_uuids)} KB(s) connected")
        for kb_uuid in kb_uuids:
            print(f"  - {kb_uuid}")

asyncio.run(check_agent())
```

### 2. Attach KB to Agent
```python
from app.clients.digital_ocean_client import do_client
import asyncio

async def attach_kb():
    agent_uuid = "YOUR_AGENT_UUID"
    client_slug = "pi-lit"  # Or whatever client
    
    success = await do_client.attach_client_kb_to_agent(agent_uuid, client_slug)
    print(f"Attach KB: {'✓' if success else '✗'}")

asyncio.run(attach_kb())
```

### 3. Verify KB has Data Sources
```python
from app.clients.digital_ocean_client import do_client
import asyncio

async def check_kb():
    kb_uuid = "YOUR_KB_UUID"
    
    # Check data sources
    sources = await do_client.list_data_sources(kb_uuid)
    print(f"Data Sources: {len(sources)}")
    for s in sources:
        spaces = s.get('spaces_data_source', {})
        print(f"  Bucket: {spaces.get('bucket_name')}")
        print(f"  Path: {spaces.get('item_path')}")
    
    # Check indexing status
    kb = await do_client.get_knowledge_base(kb_uuid)
    last_job = kb.get('last_indexing_job', {})
    print(f"\nLast Index Status: {last_job.get('status')}")
    print(f"Finished: {last_job.get('finished_at')}")

asyncio.run(check_kb())
```

### 4. Trigger Reindex (if needed)
```python
from app.clients.digital_ocean_client import do_client
import asyncio

async def reindex():
    kb_uuid = "YOUR_KB_UUID"
    bucket = "mintleads-clients-kb"
    prefix = "client-slug/"
    
    success = await do_client.trigger_reindexing(kb_uuid, bucket, prefix)
    print(f"Reindex triggered: {'✓' if success else '✗'}")

asyncio.run(reindex())
```

## Checklist for "0 Results" Issues

- [ ] Agent is connected to a Knowledge Base
- [ ] KB has at least one data source configured
- [ ] Data source points to the correct Spaces bucket/prefix
- [ ] There are actually files in the Spaces folder
- [ ] KB has been indexed (check `last_indexing_job.status`)
- [ ] KB and Agent are in the same region
- [ ] Indexing job completed successfully (not failed/pending)

## What Was Done for pi-lit

1. **Identified**: Agent `inbox-manager-pi-lit` had 0 KBs connected
2. **Attached**: Connected KB `pi-lit` (`7130339a-e343-11f0-b074-4e013e2ddde4`) to the agent
3. **Verified**: KB has data source (`mintleads-clients-kb/pi-lit/`) with 100+ files
4. **Reindexed**: Triggered a fresh reindex to ensure documents are searchable

## Wait Time
After reindexing, wait **2-5 minutes** for the indexing job to complete before testing retrieval again.

## Monitoring Index Status
```bash
# Check index job status
cd backend && source venv/bin/activate
python -c "
from app.clients.digital_ocean_client import do_client
import asyncio

async def monitor():
    kb = await do_client.get_knowledge_base('7130339a-e343-11f0-b074-4e013e2ddde4')
    job = kb.get('last_indexing_job', {})
    print(f\"Status: {job.get('status')}\")
    print(f\"Phase: {job.get('phase')}\")
    print(f\"Finished: {job.get('finished_at')}\")

asyncio.run(monitor())
"
```

## Expected Agent Logs (When Working)
```
Retrieved X results from Knowledge Base.  # X should be > 0
Retrieved top X results from 1 KBs (<index/id> <filename> <score>):
  - file1.md (score: 0.85)
  - file2.md (score: 0.82)
  ...
```

