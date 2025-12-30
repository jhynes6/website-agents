# Supabase Client Upload

This script uploads client onboarding data to Supabase Agent Storage for processing by agent workflows.

## Setup

### 1. Add Environment Variables

Add these to your `backend/.env` file:

```bash
# Supabase Agents Project Configuration
SUPABASE_AGENT_URL=https://<your-project-ref>.supabase.co
SUPABASE_AGENT_KEY=<your-supabase-agent-key>

# Optional: Modern publishable key
SUPABASE_AGENT_PUBLISHABLE_KEY=<your-supabase-publishable-key>
```

### 2. Ensure Dependencies

Make sure you have the required packages:

```bash
cd backend
pip install python-dotenv httpx pydantic pydantic-settings
```

### 3. Prepare CSV File

The script reads from `backend/scripts/io/bulk_onboarding_run_file.csv` with columns:
- `client-slug`: Unique identifier for the client
- `drive-folder`: Google Drive folder URL or ID
- `client-website`: Client's website URL

## Usage

### Test with First Client Only

```bash
cd backend
python scripts/upload_client_to_supabase.py
```

This will:
1. Load environment variables from `backend/.env`
2. Connect to Supabase Agent Storage
3. Upload the FIRST client from the CSV file
4. Create a bucket named `client-onboarding` (if it doesn't exist)
5. Upload data to: `client-onboarding/{client-slug}/data.json`

## Output

The script logs to:
- Console (stdout)
- `supabase_upload.log` file

### Uploaded Data Structure

Each client gets a JSON file with this structure:

```json
{
  "client_slug": "a-perfect-promotion",
  "website": "https://aperfectpromotion.com",
  "drive_folder_id": "1vKv7hXOxc2-Z9lOhQrqhNKCRqzPNrEED",
  "drive_folder_url": "https://drive.google.com/drive/folders/1vKv7hXOxc2-Z9lOhQrqhNKCRqzPNrEED",
  "status": "pending",
  "uploaded_at": "2025-12-30T12:34:56.789Z",
  "source": "bulk_onboarding_csv",
  "metadata": {
    "csv_row": {
      "client-slug": "a-perfect-promotion",
      "drive-folder": "https://drive.google.com/drive/folders/1vKv7hXOxc2-Z9lOhQrqhNKCRqzPNrEED",
      "client-website": "aperfectpromotion.com"
    }
  }
}
```

## Storage Structure

```
client-onboarding/
├── a-perfect-promotion/
│   └── data.json
├── archway-learning-solutions/
│   └── data.json
└── ... (more clients)
```

## Next Steps

After testing with the first client:

1. Review the uploaded data in Supabase Storage console
2. Modify the script to process all clients (remove the test limit)
3. Build agent workflows to consume this data
4. Add status tracking (pending → processing → complete)

## Troubleshooting

### Connection Issues

If you see "SUPABASE_AGENT_URL is not configured":
- Check that `backend/.env` exists
- Verify the environment variables are set correctly
- Try loading the `.env` file manually with `python-dotenv`

### Bucket Permissions

If uploads fail with 403/unauthorized:
- Verify your `SUPABASE_AGENT_KEY` has storage permissions
- Check bucket policies in Supabase dashboard
- You may need a service role key instead of the anon key

### Drive Folder ID Extraction

The script automatically extracts folder IDs from URLs like:
- `https://drive.google.com/drive/folders/1vKv7hXOxc2-Z9lOhQrqhNKCRqzPNrEED`
- Or raw IDs: `1vKv7hXOxc2-Z9lOhQrqhNKCRqzPNrEED`

