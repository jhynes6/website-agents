# Agent Registry Migration to Spaces

## Overview
Migrated the agent registry from local JSON files to DigitalOcean Spaces (`mintleads-agents-store`) for centralized, cloud-based agent metadata management.

## What Was Done

### 1. Created `mintleads-agents-store` Space
- New Space bucket specifically for agent metadata
- Accessible from anywhere with DO credentials
- Separates agent data from client KB data

### 2. Created Sync Script (`backend/scripts/sync_agents_to_spaces.py`)
- Fetches all agents from DigitalOcean API
- Parses agent names into structured slugs
  - `inbox-manager-pi-lit` → `inbox_manager:pi-lit`
  - `copywriting` → `copywriting`
- Extracts comprehensive agent metadata:
  - UUID, name, region
  - Model information
  - Knowledge Base UUIDs
  - Retrieval method
  - Endpoint URL (if public)
  - API keys (if available)
- Uploads to Spaces:
  - `agent_registry.json` - Master registry file
  - `agents/{slug}.json` - Individual agent files

### 3. Rewrote `do_agent_registry.py`
- **Old**: Read from local `do_agent_registry.json` file
- **New**: Read from `mintleads-agents-store/agent_registry.json` in Spaces
- Features:
  - Automatic S3 client initialization
  - Caching with 5-minute TTL
  - Auto-refresh on cache expiry
  - Extended `AgentRecord` dataclass with new fields
  - Backward compatibility for legacy slugs

### 4. Registry Structure

#### Master Registry (`agent_registry.json`)
```json
{
  "inbox_manager:pi-lit": {
    "agent_uuid": "1582641c-e362-11f0-b074-4e013e2ddde4",
    "agent_name": "inbox-manager-pi-lit",
    "slug": "inbox_manager:pi-lit",
    "endpoint_url": "https://...",
    "api_key": "...",
    "region": "tor1",
    "model": "openai-gpt-5",
    "knowledge_base_uuids": ["..."],
    "retrieval_method": "RETRIEVAL_METHOD_REWRITE",
    "created_at": "2025-12-27T...",
    "updated_at": "2025-12-27T..."
  }
}
```

#### Individual Agent Files (`agents/inbox_manager_pi-lit.json`)
Same structure as above, one file per agent for granular access.

## Usage

### Syncing Agents
```bash
cd backend
source venv/bin/activate
python scripts/sync_agents_to_spaces.py
```

Run this script whenever:
- New agents are created in DigitalOcean
- Agent configuration changes
- Need to refresh the registry

### Using the Registry in Code
```python
from app.clients.do_agent_registry import AgentRegistry

registry = AgentRegistry()

# Get agent by composite slug
agent = registry.get('inbox_manager:pi-lit')

# Get agent by client + type
agent = registry.get_for('pi-lit', 'inbox_manager')

# List all agents
all_agents = registry.list_all()

# Upsert agent
registry.upsert_for(
    client_slug='pi-lit',
    agent_type='inbox_manager',
    agent_uuid='...',
    endpoint_url='...',
    api_key='...'
)
```

### Cache Behavior
- Registry loads from Spaces on first access
- Cached in memory for 5 minutes
- Automatically refreshes after TTL expires
- Call `_load()` manually to force refresh

## Migration Notes

### Removed Files
- `backend/app/clients/do_agent_registry.json` - Local registry (deleted)

### Slug Format
**Format**: `{agent_type}:{client_slug}`

**Examples**:
- `inbox_manager:pi-lit` - Inbox manager for pi-lit client
- `inbox_manager:x-agency` - Inbox manager for x-agency client  
- `copywriting` - Generic copywriting agent (no client)

**Parsing Rules**:
1. Agent name: `inbox-manager-pi-lit`
   - Template: First 2 dash-separated parts (`inbox-manager`)
   - Client: Everything after (`pi-lit`)
   - Slug: `inbox_manager:pi-lit` (underscores in template, colon separator)

2. Agent name: `copywriting`
   - No client suffix
   - Slug: `copywriting`

### API Keys
- Not automatically populated by sync script
- Must be generated separately and added via `upsert()`
- Consider adding API key generation to sync script in future

## Workflow Integration

### Creating a New Agent
1. Create agent via DO API or web console
2. Run `sync_agents_to_spaces.py` to add to registry
3. Generate API key if needed
4. Update registry entry with API key

### Updating Agent Configuration
1. Update agent via DO API or web console
2. Run `sync_agents_to_spaces.py` to refresh registry
3. Registry will automatically refresh in running applications after 5 minutes

### Agent Retrieval Troubleshooting
See `TROUBLESHOOTING_AGENT_RETRIEVAL.md` for debugging document retrieval issues.

## Benefits

### Before (Local JSON)
- ❌ File must be manually updated
- ❌ Changes not synced across deployments
- ❌ No version history
- ❌ Requires code changes for updates
- ❌ Not accessible to external tools

### After (Spaces)
- ✅ Centralized in cloud
- ✅ Accessible from any deployment
- ✅ Can be updated by scripts/automation
- ✅ Accessible to external tools with DO credentials
- ✅ Automatic caching for performance
- ✅ Easy to back up and version

## Future Enhancements

1. **Automatic API Key Generation**
   - Modify sync script to generate API keys for new agents
   - Store securely in registry

2. **Webhook Integration**
   - Trigger sync when agents are created/updated in DO
   - Real-time registry updates

3. **Registry Versioning**
   - Keep historical versions of registry
   - Track changes over time

4. **Access Control**
   - Implement read-only vs read-write access
   - Audit logging for registry updates

5. **Multi-Region Support**
   - Replicate registry across DO regions
   - Reduce latency for global deployments

