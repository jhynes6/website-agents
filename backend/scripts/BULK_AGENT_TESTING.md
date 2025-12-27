# Bulk Agent Testing

This script tests all inbox-manager agents with a standard set of queries to evaluate their performance and response quality.

## Features

- ✅ Tests all inbox-manager agents (or filtered subset)
- ✅ Sends 4 standard queries to each agent
- ✅ Records responses, timing, token usage, and errors
- ✅ Generates comprehensive JSON report
- ✅ Displays real-time progress and summaries
- ✅ Handles rate limiting with configurable delays

## Test Queries

1. **"what does your company do?"** - Tests basic company description
2. **"tell me what you sell"** - Tests product/service description
3. **"what do you sell and what industries have you worked with?"** - Tests combined product + industry knowledge
4. **"do you have any case studies?"** - Tests case study awareness

## Usage

### Test All Agents

```bash
cd /Users/hynes/dev/website-agents
python backend/scripts/bulk_test_agents.py
```

This will test all ~50 inbox-manager agents (takes ~10-15 minutes).

### Test Specific Client

```bash
python backend/scripts/bulk_test_agents.py --client pi-lit
```

### Test Limited Number of Agents

```bash
python backend/scripts/bulk_test_agents.py --limit 5
```

### Custom Output File

```bash
python backend/scripts/bulk_test_agents.py --output my_test_results.json
```

### Adjust Rate Limiting

```bash
# Wait 5 seconds between agents, 2 seconds between queries
python backend/scripts/bulk_test_agents.py --delay-agents 5.0 --delay-queries 2.0
```

### Combined Options

```bash
# Test first 10 agents, save to custom file
python backend/scripts/bulk_test_agents.py --limit 10 --output quick_test.json
```

## Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--client` | Only test this specific client slug | None (all clients) |
| `--limit` | Limit number of agents to test | None (all agents) |
| `--output` | Output JSON file path | `backend/scripts/io/bulk_agent_test_results.json` |
| `--delay-agents` | Seconds to wait between testing different agents | 2.0 |
| `--delay-queries` | Seconds to wait between queries to same agent | 1.0 |

## Output Format

### JSON Structure

```json
{
  "test_queries": [
    "what does your company do?",
    "tell me what you sell",
    "what do you sell and what industries have you worked with?",
    "do you have any case studies?"
  ],
  "results": [
    {
      "agent_name": "inbox-manager-pi-lit",
      "client_slug": "pi-lit",
      "endpoint_url": "https://xxx.agents.do-ai.run",
      "has_api_key": true,
      "tested_at": "2025-12-27T23:33:33.866288+00:00",
      "queries": [
        {
          "query": "what does your company do?",
          "response": "...",
          "error": null,
          "duration_ms": 4037.73,
          "status": "success",
          "tokens": {
            "prompt": 378,
            "completion": 41,
            "total": 419
          }
        }
      ],
      "summary": {
        "total_queries": 4,
        "successful": 4,
        "errors": 0,
        "timeouts": 0,
        "success_rate": 100.0,
        "avg_duration_ms": 2618.38
      }
    }
  ],
  "summary": {
    "total_agents_tested": 1,
    "agents_with_results": 1,
    "total_queries_sent": 4,
    "successful_queries": 4,
    "overall_success_rate": 100.0,
    "tested_at": "2025-12-27T23:33:38.075806+00:00"
  }
}
```

### Console Output

```
================================================================================
BULK AGENT TESTING
================================================================================

Found 50 inbox-manager agents
Limited to first 5 agents

[1/5] Agent: inbox-manager-pi-lit

================================================================================
Testing: inbox-manager-pi-lit (pi-lit)
================================================================================

[1/4] Query: what does your company do?
  ✓ Status: success
  ⏱  Duration: 4038ms
  💬 Response: Could you please specify which aspect...
  🔢 Tokens: 419 total (378 prompt + 41 completion)

[2/4] Query: tell me what you sell
  ✓ Status: success
  ⏱  Duration: 2004ms
  💬 Response: Could you please specify which products...
  🔢 Tokens: 408 total (377 prompt + 31 completion)

────────────────────────────────────────────────────────────────────────────────
Summary: 4/4 successful (100.0%)
Average duration: 2618ms

================================================================================
FINAL SUMMARY
================================================================================
Agents tested: 5
Total queries: 20
Successful: 20/20 (100.0%)
Results saved: backend/scripts/io/bulk_agent_test_results.json
================================================================================
```

## Response Status Codes

- **success** ✓ - Query completed successfully
- **error** ✗ - Agent returned an error
- **timeout** ⏱ - Query exceeded timeout (default: 30s)
- **pending** ⋯ - Query not yet executed

## Analysis

### Quick Analysis with jq

```bash
# Count successful vs failed queries
jq '.summary' bulk_agent_test_results.json

# List agents with errors
jq '.results[] | select(.summary.errors > 0) | {agent_name, client_slug, errors: .summary.errors}' bulk_agent_test_results.json

# Get average response times per agent
jq '.results[] | {agent_name, avg_duration_ms: .summary.avg_duration_ms}' bulk_agent_test_results.json

# Find slowest responses
jq '.results[].queries[] | {client: .., duration: .duration_ms} | select(.duration > 5000)' bulk_agent_test_results.json

# Get all responses to a specific query
jq '.results[] | {client_slug, response: (.queries[] | select(.query == "what does your company do?") | .response)}' bulk_agent_test_results.json
```

### Python Analysis

```python
import json

with open('bulk_agent_test_results.json') as f:
    data = json.load(f)

# Calculate average response time across all agents
all_durations = [
    q['duration_ms'] 
    for result in data['results'] 
    for q in result['queries'] 
    if q['status'] == 'success'
]
print(f"Average response time: {sum(all_durations) / len(all_durations):.0f}ms")

# Find agents with low success rates
for result in data['results']:
    if result.get('summary', {}).get('success_rate', 100) < 100:
        print(f"{result['client_slug']}: {result['summary']['success_rate']}% success")

# Extract all responses to "what does your company do?"
for result in data['results']:
    for query in result['queries']:
        if query['query'] == 'what does your company do?':
            print(f"\n{result['client_slug']}:")
            print(query['response'][:200])
```

## Troubleshooting

### Missing API Keys

If agents are skipped due to missing API keys:

```bash
# Regenerate API keys for all agents
python backend/scripts/refresh_agent_tokens.py --all --yes
```

### Timeout Issues

If queries are timing out, increase the timeout in the script (default: 30s) or investigate slow agents:

```bash
# Test a single slow agent
python backend/scripts/test_inbox_manager.py --client slow-client
```

### Rate Limiting

If you encounter rate limiting:

```bash
# Increase delays between requests
python backend/scripts/bulk_test_agents.py --delay-agents 5.0 --delay-queries 2.0
```

## Best Practices

1. **Start Small**: Test with `--limit 5` first to verify everything works
2. **Monitor Progress**: The script shows real-time progress and summaries
3. **Save Results**: Always specify a meaningful `--output` filename for historical comparison
4. **Analyze Patterns**: Look for common failure modes or slow responses across agents
5. **Compare Over Time**: Run periodically and compare results to track improvements

## Related Scripts

- `refresh_agent_tokens.py` - Regenerate API keys
- `test_inbox_manager.py` - Test a single agent interactively
- `update_agent_params.py` - Update agent parameters (temperature, etc.)
- `audit_clients_and_kbs.py` - Generate KB statistics

## Timing Estimates

- **Single agent**: ~10-15 seconds (4 queries × 2-3s each + delays)
- **10 agents**: ~2-3 minutes
- **50 agents (all)**: ~10-15 minutes

Adjust `--delay-agents` and `--delay-queries` to speed up or slow down testing.

