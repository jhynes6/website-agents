# KB Retrieval Test Tool

Test document retrieval from DigitalOcean Knowledge Bases using the Gradient API.

## Usage

### Interactive Mode (Default)
```bash
cd backend
source venv/bin/activate
python scripts/test_kb_retrieval.py
```

This will:
1. Show all available KBs from your registry
2. Let you test retrieval by client slug or KB UUID
3. Display results with scores and content

### Quick Test (Command Line)

**Test by client slug:**
```bash
python scripts/test_kb_retrieval.py --client pi-lit --query "What services do you offer?"
```

**Test by KB UUID:**
```bash
python scripts/test_kb_retrieval.py \
  --kb-uuid 7130339a-e343-11f0-b074-4e013e2ddde4 \
  --query "pricing information"
```

**Retrieve more results:**
```bash
python scripts/test_kb_retrieval.py \
  --client pi-lit \
  --query "contact information" \
  --num-results 10
```

### List All Available KBs
```bash
python scripts/test_kb_retrieval.py --list
```

## What It Shows

For each result:
- **Score**: Relevance score (higher = more relevant)
- **Document ID**: Unique identifier for the chunk
- **Metadata**: Source information, content type, etc.
- **Content/Text**: The actual text content retrieved

Plus a raw JSON dump for debugging.

## Use Cases

1. **Test KB quality**: See what documents are being retrieved for queries
2. **Debug retrieval issues**: Check if relevant info is in the KB
3. **Tune K parameter**: Experiment with different `num_results` values
4. **Verify indexing**: Make sure new documents are searchable
5. **Compare queries**: See how different phrasings affect results

## Example Session

```bash
$ python scripts/test_kb_retrieval.py

================================================================================
Available Knowledge Bases
================================================================================
  1. pi-lit                                   | 7130339a-e343-11f0-b074-4e013e2ddde4
  2. x-agency                                 | 1b5875a9-e342-11f0-b074-4e013e2ddde4
  ...

Options:
  1. Test retrieval by client slug
  2. Test retrieval by KB UUID
  3. List all KBs
  q. Quit

Choice: 1
Client slug: pi-lit
Query: What products do you sell?
Number of results [5]: 

================================================================================
Testing KB Retrieval
================================================================================
KB UUID: 7130339a-e343-11f0-b074-4e013e2ddde4
Query: What products do you sell?
Num Results: 5
================================================================================

✓ Successfully retrieved 5 results

================================================================================
Result 1
================================================================================
Score: 0.89
Document ID: doc_abc123
Content:
PI-LIT offers LED road flares and warning lights for traffic safety...
```

## Requirements

- `gradient` Python SDK installed (should be in requirements.txt)
- Valid DigitalOcean credentials in `.env`
- KB registry populated (`backend/app/clients/do_kb_registry.json`)

## Troubleshooting

**Error: "Client not found"**
- Run `--list` to see available clients
- Check that KB registry is up to date

**Error: "No results returned"**
- KB might be empty or not indexed
- Try a more general query
- Check KB indexing status with audit script

**Error: "Authentication failed"**
- Check `DIGITALOCEAN_TOKEN` in `.env`
- Verify token has GenAI API access

