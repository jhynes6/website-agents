import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

# Handle imports for both package use and standalone script execution
try:
    from ..config import get_settings
except ImportError:
    # When run standalone, add parent directories to path
    script_dir = Path(__file__).resolve().parent
    backend_dir = script_dir.parent.parent
    if backend_dir not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from app.config import get_settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Minimal Supabase PostgREST client (read-only) for this project.
    We use it to map Email Bison webhook `workspace_name` to our `client_slug`
    via the `bison_client_db` table.
    """

    def __init__(
        self,
        *,
        project_url: Optional[str] = None,
        api_key: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> None:
        self.settings = get_settings()
        self._override_project_url = project_url
        self._override_api_key = api_key
        self._override_schema = schema

    def _rest_base(self) -> str:
        # Prefer Bison-specific Supabase vars (per context/supabase_client.py)
        base = self._override_project_url or self.settings.bison_supabase_project_url or self.settings.supabase_url
        if not base:
            raise ValueError("BISON_SUPABASE_PROJECT_URL (or SUPABASE_URL) not configured")
        # HttpUrl -> str
        return f"{str(base).rstrip('/')}/rest/v1"

    def _headers(self, *, profile: Optional[str] = None) -> Dict[str, str]:
        # Use anon key for read-only lookup; fall back to service role if provided.
        key = self._override_api_key or (self.settings.bison_supabase_anon_key or self.settings.supabase_service_role_key)
        if not key:
            raise ValueError("BISON_SUPABASE_ANON_KEY (or SUPABASE_SERVICE_ROLE_KEY) not configured")
        # PostgREST uses the same bearer token as apikey for auth (anon key works for public tables)
        headers: Dict[str, str] = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        }
        # Select schema/profile (Supabase PostgREST uses Accept-Profile for reads).
        # Some deployments 400 if you send Accept-Profile=public, so only send when non-public.
        if profile and profile != "public":
            headers["Accept-Profile"] = profile
        return headers

    async def get_client_slug_for_workspace(
        self,
        *,
        workspace_id: Optional[int] = None,
        workspace_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Resolve our internal client slug for an Email Bison workspace.

        We prefer workspace_id (stable, numeric, present in webhook payloads).
        We fall back to workspace_name only if needed.

        Expected table: bison_client_db
        Expected columns (at minimum):
          - workspace_id (preferred) OR workspace_name (fallback)
          - client_slug (preferred) OR another slug-like field
        """
        schema = (self._override_schema or self.settings.supabase_schema or "public").strip() or "public"
        table = "bison_client_db"

        # Helper to extract slug from a returned row with flexible column naming.
        def _extract_slug(row: Any) -> Optional[str]:
            if not isinstance(row, dict):
                return None
            for k in ["client_slug", "clientSlug", "slug", "client"]:
                v = row.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            return None

        async def _query(filter_expr: str) -> Optional[str]:
            url = f"{self._rest_base()}/{quote(table)}?select=*&{filter_expr}&limit=1"
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, headers=self._headers(profile=schema))
                if resp.status_code >= 400:
                    raise httpx.HTTPStatusError(
                        f"Supabase PostgREST error {resp.status_code}: {resp.text}",
                        request=resp.request,
                        response=resp,
                    )
                rows: Any = resp.json()
                if isinstance(rows, list) and rows:
                    return _extract_slug(rows[0])
                return None

        # 1) Prefer workspace_id lookup (most likely column exists)
        if workspace_id is not None:
            try:
                slug = await _query(f"workspace_id=eq.{int(workspace_id)}")
                if slug:
                    return slug
            except httpx.HTTPStatusError as e:
                # If workspace_id column doesn't exist, we'll fall back to name-based matching.
                logger.debug("workspace_id lookup failed: %s", str(e))

        # 2) Fallback to workspace_name lookup if available
        name = (workspace_name or "").strip()
        if name:
            # Try a few common column names to be resilient to schema drift.
            for col in ["workspace_name", "workspace", "client_name", "name"]:
                try:
                    # Only quote the value; column names are from a fixed allow-list above.
                    slug = await _query(f"{col}=eq.{quote(name)}")
                    if slug:
                        return slug
                except httpx.HTTPStatusError as e:
                    # If the column doesn't exist, try the next one.
                    logger.debug("workspace_name lookup failed for col=%s: %s", col, str(e))

        return None

    async def get_client_slug_for_workspace_name(self, workspace_name: str) -> Optional[str]:
        """
        Back-compat shim (older call sites). Prefer get_client_slug_for_workspace(workspace_id=...).
        """
        return await self.get_client_slug_for_workspace(workspace_name=workspace_name)


supabase_client = SupabaseClient()


async def _test_standalone():
    """Test the SupabaseClient and list all storage objects."""
    import asyncio
    import os
    
    # Try to load environment variables from .env file
    try:
        from dotenv import load_dotenv
        # Look for .env files in project root
        project_root = Path(__file__).resolve().parent.parent.parent
        env_files = [
            project_root / '.env',
            project_root / '.env.local',
            project_root / 'backend' / '.env',
        ]
        for env_file in env_files:
            if env_file.exists():
                print(f"Loading environment from: {env_file}")
                load_dotenv(env_file)
                break
        else:
            print("⚠ No .env file found. Relying on existing environment variables.")
    except ImportError:
        print("⚠ python-dotenv not installed. Relying on existing environment variables.")
    
    print("Testing SupabaseClient...")
    client = SupabaseClient()
    
    try:
        # Test basic configuration
        print(f"✓ Client initialized successfully")
        
        # Try to get REST base URL
        try:
            base_url = client._rest_base()
            print(f"✓ REST base URL: {base_url}")
        except ValueError as e:
            print(f"⚠ REST base URL not configured: {e}")
            print("  Set BISON_SUPABASE_PROJECT_URL or SUPABASE_URL to test API calls")
            return 1
        
        # List all storage objects using Storage API
        print("\n=== Listeing All Storage Objects ===\n")
        try:
            # Import the storage client
            try:
                from .supabase_storage_client import SupabaseStorageClient
            except ImportError:
                from app.clients.supabase_storage_client import SupabaseStorageClient
            
            # Get credentials
            project_url = client._override_project_url or client.settings.bison_supabase_project_url or client.settings.supabase_url
            service_key = client.settings.supabase_service_role_key
            
            if not service_key:
                print("❌ Service role key required to list storage objects")
                print("\n📝 To fix this, add to your .env file:")
                print("   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here")
                print("\n💡 You can find your service role key in:")
                print("   Supabase Dashboard → Project Settings → API → service_role key")
                print("\n⚠️  This workaround is needed because the storage.objects table is")
                print("   owned by the system and cannot be queried directly via SQL without")
                print("   elevated permissions. The Storage API with service role key bypasses this.")
                return 1
            
            # Create storage client
            storage = SupabaseStorageClient(
                project_url=str(project_url),
                service_role_key=service_key
            )
            
            # Get all buckets
            buckets = storage.list_buckets()
            
            if not buckets:
                print("No storage buckets found.")
                return 0
            
            # Collect all objects from all buckets
            all_objects = []
            for bucket in buckets:
                bucket_id = bucket.get('id') or bucket.get('name', 'unknown')
                try:
                    objects = storage.list_objects(bucket_id, prefix="", limit=1000)
                    for obj in objects:
                        obj['bucket_id'] = bucket_id
                        all_objects.append(obj)
                except Exception as e:
                    print(f"⚠ Failed to list objects in bucket '{bucket_id}': {e}")
            
            objects = all_objects
            
            if not objects:
                print("No storage objects found.")
                return 0
            
            print(f"Found {len(objects)} storage object(s):\n")
            
            # Group by bucket
            from collections import defaultdict
            by_bucket = defaultdict(list)
            for obj in objects:
                bucket_id = obj.get('bucket_id', 'unknown')
                by_bucket[bucket_id].append(obj)
            
            for bucket_id, bucket_objects in sorted(by_bucket.items()):
                print(f"📦 Bucket: {bucket_id} ({len(bucket_objects)} objects)")
                for obj in bucket_objects:
                    name = obj.get('name', 'unknown')
                    
                    # Storage API returns metadata as a dict
                    metadata = obj.get('metadata', {})
                    if isinstance(metadata, dict):
                        size = metadata.get('size', 0)
                        mimetype = metadata.get('mimetype', 'unknown')
                    else:
                        size = 0
                        mimetype = 'unknown'
                    
                    updated_at = obj.get('updated_at') or obj.get('created_at', 'unknown')
                    obj_id = obj.get('id', 'unknown')
                    
                    # Format size
                    if isinstance(size, (int, float)) and size > 0:
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size / 1024:.1f} KB"
                        else:
                            size_str = f"{size / (1024 * 1024):.1f} MB"
                    else:
                        size_str = "unknown size"
                    
                    print(f"   • {name}")
                    print(f"     ID: {obj_id}")
                    print(f"     Size: {size_str}")
                    print(f"     Type: {mimetype}")
                    print(f"     Updated: {updated_at}")
                print()
                
                print("✅ Successfully listed all storage objects")
                
        except Exception as e:
            print(f"❌ Failed to list storage objects: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
    except Exception as e:
        print(f"\n❌ Test failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(_test_standalone()))
    
