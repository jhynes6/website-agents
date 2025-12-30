"""
Delete all client buckets and their contents from Supabase Storage via SQL.

This script uses the Supabase MCP tool to delete buckets.
"""

# To delete all buckets, run this SQL via the Supabase MCP tool:

# 1. First, get a list of all buckets to delete:
SELECT id, name FROM storage.buckets ORDER BY name;

# 2. Delete all objects from all buckets (use this carefully!):
# This is a PostgreSQL function that will delete all objects in all buckets

DO $$
DECLARE
    bucket_record RECORD;
    object_record RECORD;
BEGIN
    -- Loop through all buckets
    FOR bucket_record IN 
        SELECT id FROM storage.buckets
    LOOP
        -- Delete all objects in this bucket
        DELETE FROM storage.objects 
        WHERE bucket_id = bucket_record.id;
        
        RAISE NOTICE 'Deleted objects from bucket: %', bucket_record.id;
    END LOOP;
END $$;

# 3. Then delete all buckets:
DELETE FROM storage.buckets;

# Or delete specific buckets:
DELETE FROM storage.buckets 
WHERE id IN (
    'a-perfect-promotion',
    'abundantly'
    -- add more as needed
);

