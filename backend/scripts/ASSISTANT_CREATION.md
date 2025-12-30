# Pinecone Assistant Creation

## Overview

Pinecone Assistants provide a managed RAG chatbot with built-in file management, chunking, embedding, and chat interface. Each client gets their own assistant for isolation and customization.

---

## Architecture

### Two Chatbot Options

This system now supports **two parallel chatbot implementations**:

1. **Custom RAG System** (via `/api/mintagent/chat`)
   - Uses Pinecone Index with namespaces
   - Custom chunking & embedding logic
   - Full control over retrieval & generation
   - Requires manual management

2. **Pinecone Assistants** (managed service)
   - Built-in file upload & processing
   - Automatic chunking & embedding
   - Managed chat interface
   - Citations & source tracking
   - Access via Pinecone API or Console

---

## Automatic Creation (Integrated)

Assistants are automatically created during the main ingestion pipeline:

### When It Runs
- Triggers after successful Supabase Storage upload
- Triggers after successful Pinecone vectorization
- Only for **new clients** (checks if assistant exists first)

### What It Does
1. Creates assistant named `{client_slug}`
2. Sets custom instructions for the client
3. Uploads all markdown files from Supabase Storage
4. Waits for file processing to complete

### Flow Diagram
```
Ingest Client Data
        ↓
Upload to Supabase Storage
        ↓
Vectorize to Pinecone Index
        ↓
Create Pinecone Assistant ← YOU ARE HERE
        ↓
Upload Files to Assistant
        ↓
✅ Ready for Chat
```

### Code Location
- Function: `_create_assistant()` in `backend/app/routes/create.py`
- Called from: `create_chatbot()` endpoint

---

## Manual Creation (Standalone Script)

For existing clients or re-creation, use the standalone script:

### Usage

**Basic creation:**
```bash
python backend/scripts/create_assistant.py CLIENT_SLUG
```

**With custom instructions:**
```bash
python backend/scripts/create_assistant.py CLIENT_SLUG \
  --instructions "You are an expert in renewable energy..."
```

**Force recreation (deletes existing):**
```bash
python backend/scripts/create_assistant.py CLIENT_SLUG --force
```

### Examples

```bash
# Create assistant for a-perfect-promotion
python backend/scripts/create_assistant.py a-perfect-promotion

# Recreate assistant with new instructions
python backend/scripts/create_assistant.py galactic-fed \
  --force \
  --instructions "You are a marketing agency AI assistant..."
```

### Output Example
```
🤖 Creating Pinecone Assistant for: client-slug
================================================================================

1️⃣ Creating assistant...
  ✓ Assistant 'client-slug' created
  ✓ Status: Ready

2️⃣ Listing files from Supabase Storage...
  ✓ Found 47 markdown files

3️⃣ Uploading files to assistant...
  ✓ Uploaded: 404.md (3421 bytes)
  ✓ Uploaded: about.md (5234 bytes)
  ...
  ✓ Uploaded: contact.md (2891 bytes)

================================================================================
✅ Assistant creation complete!

📊 Summary:
   - Assistant Name: client-slug
   - Files Uploaded: 47
   - Failed: 0
   - Status: Ready

💬 Test your assistant:
   - Console: https://app.pinecone.io/organizations/-/projects/-/assistant
   - API: POST /assistant/chat/client-slug
```

---

## Prerequisites

### 1. Files Must Exist in Supabase Storage

The assistant creation reads files from:
```
client-data-sources/
  └── {client-slug}/
      ├── website/*.md
      ├── drive/*.md
      └── intake_form/*.md
```

**If files don't exist:**
- Run ingestion first: `python backend/scripts/ingest_to_supabase.py --client CLIENT_SLUG`
- Or call the API: `POST /api/mintagent/create`

### 2. Environment Variables

```bash
PINECONE_API_KEY=pcsk_...  # Required for assistant creation
SUPABASE_AGENT_URL=https://xxx.supabase.co  # Required for file download
SUPABASE_AGENT_KEY=eyJhbGc...  # Required for file download
```

---

## Chat with an Assistant

### Via Pinecone API

**Python SDK:**
```python
from pinecone import Pinecone
from pinecone_plugins.assistant.models.chat import Message

pc = Pinecone(api_key="YOUR_API_KEY")
assistant = pc.assistant.Assistant(assistant_name="client-slug")

msg = Message(role="user", content="What services do you offer?")
response = assistant.chat(messages=[msg])

print(response.message.content)
```

**REST API:**
```bash
curl -X POST \
  "https://prod-1-data.ke.pinecone.io/assistant/chat/client-slug" \
  -H "Api-Key: $PINECONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Tell me about your company"}
    ]
  }'
```

### Via Pinecone Console

1. Navigate to: https://app.pinecone.io/organizations/-/projects/-/assistant
2. Select your assistant from the list
3. Use the playground to test chat

---

## Assistant Features

### ✅ Automatic Features
- **File Management**: Upload, list, delete files
- **Chunking**: Intelligent text segmentation
- **Embedding**: Automatic vector generation
- **RAG**: Context retrieval + generation
- **Citations**: Source references in responses
- **Streaming**: Real-time response streaming
- **Multi-turn**: Conversation history support

### 🎛️ Customizable
- **Instructions**: System prompt for behavior
- **Model**: Choose GPT-4o, GPT-4.1, Claude, etc.
- **Metadata**: Filter files by metadata
- **Context Size**: Control top_k and snippet_size
- **Temperature**: Adjust response randomness

---

## Comparison: Custom RAG vs Assistant

| Feature | Custom RAG | Pinecone Assistant |
|---------|-----------|-------------------|
| **Setup** | Manual | Automatic |
| **Chunking** | Custom logic | Built-in |
| **Embedding** | OpenAI API | Built-in |
| **File Management** | Supabase Storage | Pinecone Storage |
| **Chat API** | Custom endpoint | Pinecone API |
| **Citations** | Manual | Automatic |
| **Console UI** | No | Yes |
| **Cost** | OpenAI + Pinecone Index | Pinecone Assistant pricing |
| **Flexibility** | Full control | Managed service |

### When to Use Each

**Use Custom RAG when:**
- Need custom chunking strategy
- Want full control over retrieval
- Building custom UI/UX
- Integrating with other systems

**Use Pinecone Assistant when:**
- Want quick setup
- Need built-in chat interface
- Want automatic file management
- Prefer managed service
- Building prototype/MVP

---

## Troubleshooting

### Issue: Assistant already exists
```
⚠️  Assistant 'client-slug' already exists
    Use --force to recreate
```
**Solution**: Use `--force` flag to delete and recreate

### Issue: No files found
```
⚠️  No files found for client-slug
```
**Solution**: 
1. Check files exist in Supabase Storage
2. Run ingestion first: `python backend/scripts/ingest_to_supabase.py --client client-slug`

### Issue: Upload fails
```
❌ Failed to upload file.md: timeout
```
**Solution**:
- Check network connection
- Verify Pinecone API key
- Try smaller batch of files
- Increase timeout in script

### Issue: Assistant not responding
**Solution**:
1. Check assistant status in console
2. Verify files were uploaded successfully
3. Wait for file processing (can take 1-2 minutes)
4. Check logs for errors

---

## Monitoring

### Check Assistant Status
```python
from pinecone import Pinecone

pc = Pinecone(api_key="YOUR_API_KEY")
assistant = pc.assistant.Assistant(assistant_name="client-slug")
status = pc.assistant.describe_assistant("client-slug")
print(f"Status: {status.status}")
```

### List Files in Assistant
```python
assistant = pc.assistant.Assistant(assistant_name="client-slug")
files = assistant.list_files()
print(f"Total files: {len(files)}")
```

### Delete Assistant
```python
pc.assistant.delete_assistant(assistant_name="client-slug")
```
⚠️ **Warning**: Deleting an assistant also deletes all uploaded files

---

## API Response Example

### Successful Creation
```json
{
  "success": true,
  "assistant_name": "client-slug",
  "files_uploaded": 47,
  "files_failed": 0,
  "created": true
}
```

### Already Exists
```json
{
  "success": true,
  "assistant_name": "client-slug",
  "created": false,
  "reason": "Assistant already exists"
}
```

### Error
```json
{
  "success": false,
  "error": "Failed to create assistant: API key invalid"
}
```

---

## Cost Considerations

Pinecone Assistants have separate pricing:
- **Hourly rate**: Per assistant, regardless of activity
- **Chat tokens**: Input + output tokens
- **Storage**: File storage

See: https://docs.pinecone.io/guides/assistant/pricing-and-limits

---

## Future Enhancements

- [ ] Batch assistant creation for multiple clients
- [ ] Custom metadata per uploaded file
- [ ] Automatic file updates on content changes
- [ ] Assistant usage analytics
- [ ] Custom model selection per client
- [ ] Multi-language support
- [ ] File version management
- [ ] Backup/restore assistants

---

## Related Documentation

- **Pipeline**: `PIPELINE_DOCUMENTATION.md` - Full ingestion flow
- **Bucket Creation**: `BUCKET_CREATION.md` - Supabase Storage setup
- **Pinecone Docs**: https://docs.pinecone.io/guides/assistant/

---

**Last Updated**: 2025-12-30
**Version**: 1.0.0

