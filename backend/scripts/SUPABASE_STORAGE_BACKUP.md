# Supabase Storage Backup System

## Overview

When uploading documents to Supabase Storage fails (e.g., bucket doesn't exist, RLS policy issues), the system automatically saves all files locally as a backup.

## Local Backup Location

```
data/supabase_backup/{client-slug}/
├── website/
│   └── {doc_id}.md
├── drive/
│   └── {doc_id}.md
└── intake_form/
    └── {doc_id}.md
```

## When Backups Are Created

1. **Bucket Creation Fails**: If the bucket cannot be created due to RLS policies
2. **Upload Errors**: Individual file upload failures
3. **Network Issues**: Connection problems with Supabase

## File Format

All files are saved with YAML frontmatter:

```yaml
---
doc_id: "galacticfed.com/case-studies/kayrros.md"
client_slug: "galactic-fed"
document_source: "website"
url: "https://www.galacticfed.com/case-studies/kayrros"
title: "Case Study: Kayrros"
content_type: "case_studies"
keywords:
  - "case study"
  - "kayrros"
ingested_at: "2025-12-29T20:30:00.000000+00:00"
---

[markdown content here]
```

## Logs

The system logs backup activity:

```
[INFO] create.local_backup.initialized {'client': 'evenbound', 'path': '/path/to/data/supabase_backup/evenbound'}
[INFO] create.local_backup.saved {'doc_id': 'evenbound.com/services.md', 'path': '/path/to/file.md'}
[INFO] create.local_backup.complete {'client': 'evenbound', 'path': '/path/to/backup', 'files_backed_up': 150}
```

## Success Reporting

The API now correctly reports upload status:

```json
{
  "storage": {
    "uploaded_to_supabase": 0,
    "failed": 150,
    "total": 150,
    "success": false,
    "local_backup_path": "/path/to/data/supabase_backup/evenbound"
  }
}
```

## Recovery

To upload backed-up files to Supabase:

1. Fix the RLS policies or bucket creation issue
2. Create a recovery script that reads from `data/supabase_backup/{client}/`
3. Upload each file using the `SupabaseAgentStorageClient`

## Gitignore

The backup directory is automatically excluded from git:

```gitignore
data/supabase_backup/
```

