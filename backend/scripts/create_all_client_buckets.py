"""
Create all client buckets and RLS policies in Supabase.

This script reads the CSV file and creates a bucket for each client with appropriate
RLS policies to allow anon key access.
"""
import csv
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

def generate_bucket_creation_sql(csv_path: Path) -> str:
    """
    Generate SQL to create all client buckets and RLS policies.
    """
    clients = []
    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            client_slug = row.get("client-slug", "").strip()
            if client_slug:
                clients.append(client_slug)
    
    print(f"Found {len(clients)} clients")
    
    # Generate SQL
    sql_parts = []
    
    # Insert all buckets
    sql_parts.append("-- Create all client buckets")
    for client_slug in clients:
        sql_parts.append(f"""
INSERT INTO storage.buckets (id, name, public)
VALUES ('{client_slug}', '{client_slug}', false)
ON CONFLICT (id) DO NOTHING;""")
    
    # Create RLS policies for each bucket
    sql_parts.append("\n-- Create RLS policies for all buckets")
    for client_slug in clients:
        # Escape single quotes in client slug for SQL
        safe_slug = client_slug.replace("'", "''")
        sql_parts.append(f"""
-- Policies for {client_slug}
DROP POLICY IF EXISTS "Allow anon uploads to {safe_slug}" ON storage.objects;
DROP POLICY IF EXISTS "Allow anon reads from {safe_slug}" ON storage.objects;

CREATE POLICY "Allow anon uploads to {safe_slug}"
ON storage.objects FOR INSERT
TO anon
WITH CHECK (bucket_id = '{safe_slug}');

CREATE POLICY "Allow anon reads from {safe_slug}"
ON storage.objects FOR SELECT
TO anon
USING (bucket_id = '{safe_slug}');""")
    
    return "\n".join(sql_parts)


def main():
    """Generate SQL file for bucket creation."""
    csv_path = backend_dir / "scripts" / "io" / "bulk_onboarding_run_file.csv"
    
    if not csv_path.exists():
        print(f"CSV file not found at: {csv_path}")
        return
    
    print(f"Reading clients from: {csv_path}")
    sql = generate_bucket_creation_sql(csv_path)
    
    # Save to file
    output_path = backend_dir / "scripts" / "create_all_buckets.sql"
    with open(output_path, 'w') as f:
        f.write(sql)
    
    print(f"\n✅ SQL generated successfully!")
    print(f"📄 Saved to: {output_path}")
    print(f"\nYou can now execute this SQL in Supabase or use the MCP tool to apply it.")


if __name__ == "__main__":
    main()

