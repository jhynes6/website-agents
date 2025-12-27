import asyncio
import logging
import sys
import re
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

# Add backend directory to path so we can import app modules
# Assumes script is in backend/scripts/
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.clients.digital_ocean_client import DigitalOceanClient, do_client
from app.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("audit_script")

async def get_file_frontmatter(bucket: str, key: str, s3_client) -> Dict[str, str]:
    """
    Reads the first 1KB of a file from S3 and extracts YAML frontmatter.
    Returns a dict of found metadata keys.
    """
    try:
        # Get first 1KB
        response = s3_client.get_object(Bucket=bucket, Key=key, Range="bytes=0-1024")
        content = response['Body'].read().decode('utf-8', errors='ignore')
        
        # Parse frontmatter
        # Look for content between first two ---
        match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return {}
            
        frontmatter_text = match.group(1)
        metadata = {}
        for line in frontmatter_text.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                metadata[key.strip()] = val.strip()
        
        return metadata
    except Exception as e:
        logger.warning(f"Failed to read frontmatter for {key}: {e}")
        return {}

async def audit_spaces(settings):
    """
     audits the Spaces bucket.
    """
    s3 = do_client.s3_client
    bucket = settings.digitalocean_spaces_bucket
    
    if not s3 or not bucket:
        logger.error("Spaces not configured.")
        return {}

    logger.info(f"Scanning bucket: {bucket}...")
    
    # 1. List all objects
    # We want to group by top-level folder (client_slug)
    client_stats = defaultdict(lambda: {
        "total_files": 0,
        "content_types": defaultdict(int),
        "document_sources": defaultdict(int)
    })
    
    paginator = s3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket)

    for page in page_iterator:
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            key = obj['Key']
            if key.endswith('/'): # Skip folders
                continue
                
            parts = key.split('/')
            if len(parts) < 2:
                continue
                
            client_slug = parts[0]
            
            # Infer document_source from path (faster than reading file)
            # Structure: {client_slug}/{source_folder}/{filename}
            # BUT sometimes source_folder is mapped (e.g. drive).
            # Let's rely on frontmatter for accuracy as requested, or fallback to path.
            
            # We need frontmatter for content_type anyway.
            # Reading every file might be slow. Let's sample or just do it?
            # User asked for "breakdown of counts", implying accuracy.
            # Let's try to read header.
            
            meta = await get_file_frontmatter(bucket, key, s3)
            
            # Get Content Type
            c_type = meta.get('content_type', 'unknown')
            
            # Get Document Source
            # Fallback to path inference if missing in frontmatter
            d_source = meta.get('document_source')
            if not d_source:
                 # infer from second part of path if available
                 if len(parts) > 2:
                     d_source = parts[1]
                 else:
                     d_source = 'unknown'
            
            client_stats[client_slug]["total_files"] += 1
            client_stats[client_slug]["content_types"][c_type] += 1
            client_stats[client_slug]["document_sources"][d_source] += 1
            
            # Progress log every 100 files total (across all clients) could be noisy
            # We'll just let it run.
            
    return client_stats

async def audit_kbs():
    """
    Audits Knowledge Bases.
    """
    logger.info("Fetching Knowledge Bases...")
    kbs = await do_client.list_knowledge_bases()
    logger.info(f"Found {len(kbs)} Knowledge Bases.")
    
    kb_audit = []
    
    for kb in kbs:
        uuid = kb.get('uuid')
        name = kb.get('name')
        region = kb.get('region') or kb.get('datacenter')
        
        # Get data sources
        sources = await do_client.list_data_sources(uuid)
        
        source_summary = []
        is_correctly_configured = False
        pointing_to_root = False
        
        for s in sources:
            s_details = s.get("spaces_data_source", {})
            bucket = s_details.get("bucket_name")
            prefix = s_details.get("item_path") or s_details.get("prefix", "")
            
            source_info = f"{bucket}/{prefix}"
            source_summary.append(source_info)
            
            # Check if this source matches the client name (assuming KB name is client slug)
            # Expected prefix: {name}/
            expected_prefix = f"{name}/"
            
            if prefix.rstrip('/') == expected_prefix.rstrip('/'):
                is_correctly_configured = True
            
            if not prefix or prefix == "/":
                pointing_to_root = True
                
        kb_audit.append({
            "name": name,
            "uuid": uuid,
            "region": region,
            "sources": source_summary,
            "is_correctly_configured": is_correctly_configured,
            "pointing_to_root": pointing_to_root,
            "raw": kb,
        })
        
    return kb_audit

async def upload_directory_to_spaces(directory: Path, bucket: str, prefix: str):
    """
    Recursively uploads a directory to DigitalOcean Spaces.
    """
    if not do_client.s3_client:
        logger.error("Spaces client not initialized. Skipping upload.")
        return

    logger.info(f"Uploading {directory} to Spaces bucket {bucket} with prefix {prefix}...")
    
    for path in directory.rglob("*"):
        if path.is_file():
            # Calculate relative path for key
            rel_path = path.relative_to(directory)
            key = f"{prefix}/{rel_path}".replace("\\", "/") # Ensure forward slashes
            
            # Determine content type (basic)
            content_type = "application/octet-stream"
            if path.suffix == ".json":
                content_type = "application/json"
            elif path.suffix == ".csv":
                content_type = "text/csv"
            elif path.suffix == ".md":
                content_type = "text/markdown"
            elif path.suffix == ".html":
                content_type = "text/html"
            
            try:
                with open(path, "rb") as f:
                    file_content = f.read()
                    do_client.upload_file_content(file_content, key, content_type)
                # logger.info(f"Uploaded {rel_path} to {key}") # Verbose
            except Exception as e:
                logger.error(f"Failed to upload {path}: {e}")
                
    logger.info("Upload complete.")

def load_client_metadata(io_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Loads client metadata from CSV files in the io directory.
    Returns a dict mapping client_slug -> metadata dict.
    """
    metadata = defaultdict(dict)
    
    # 1. Load from bulk_onboarding_run_file.csv (Original source)
    onboarding_file = io_dir / "bulk_onboarding_run_file.csv"
    if onboarding_file.exists():
        try:
            with open(onboarding_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    slug = row.get("client-slug")
                    if slug:
                        metadata[slug]["drive_folder"] = row.get("drive-folder")
                        metadata[slug]["website"] = row.get("client-website")
        except Exception as e:
            logger.error(f"Error reading {onboarding_file}: {e}")
            
    # 2. Load from intake_domains.csv (Intake processing results)
    intake_file = io_dir / "intake_domains.csv"
    if intake_file.exists():
        try:
            with open(intake_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    slug = row.get("client-slug")
                    if slug:
                        # Update/Override with potentially processed data
                        if row.get("drive-folder"):
                            metadata[slug]["drive_folder"] = row.get("drive-folder")
                        
                        metadata[slug]["intake_domain"] = row.get("intake-domain")
                        metadata[slug]["intake_status"] = row.get("status")
                        
                        # Sometimes original-client-website is in this CSV too
                        if row.get("original-client-website"):
                            metadata[slug]["website"] = row.get("original-client-website")
                            
        except Exception as e:
            logger.error(f"Error reading {intake_file}: {e}")
            
    return metadata

async def main():
    settings = get_settings()
    
    print("\n=== STARTING AUDIT ===\n")

    io_dir = Path(__file__).resolve().parent / "io"
    io_dir.mkdir(parents=True, exist_ok=True)
    kb_master_dir = io_dir / "_mintleads_kb_master"
    kb_master_clients_dir = kb_master_dir / "clients"
    kb_master_reports_dir = kb_master_dir / "reports"
    kb_master_clients_dir.mkdir(parents=True, exist_ok=True)
    kb_master_reports_dir.mkdir(parents=True, exist_ok=True)
    kb_inspect_dir = kb_master_reports_dir / "kb_inspect"
    kb_inspect_dir.mkdir(parents=True, exist_ok=True)
    
    # Load metadata from CSVs
    client_metadata = load_client_metadata(io_dir)
    logger.info(f"Loaded metadata for {len(client_metadata)} clients.")

    # 1. Audit Spaces
    print("--- 1. Analyzing Client Folders in Spaces ---")
    client_stats = await audit_spaces(settings)
    
    print(f"\nFound {len(client_stats)} client folders.")
    for client, stats in sorted(client_stats.items()):
        print(f"\nClient: {client}")
        print(f"  Total Files: {stats['total_files']}")
        print("  Content Types:")
        for ct, count in stats['content_types'].items():
            print(f"    - {ct}: {count}")
        print("  Document Sources:")
        for ds, count in stats['document_sources'].items():
            print(f"    - {ds}: {count}")

    # 2. Audit KBs
    print("\n\n--- 2. Analyzing Knowledge Bases ---")
    kb_audit = await audit_kbs()
    
    print(f"\nFound {len(kb_audit)} Knowledge Bases.")
    
    misconfigured_kbs = []
    
    for kb in kb_audit:
        status = "OK"
        if not kb['is_correctly_configured']:
            status = "MISCONFIGURED"
            misconfigured_kbs.append(kb)
        if kb['pointing_to_root']:
            status = "DANGER (Points to Root)"
            if kb not in misconfigured_kbs: misconfigured_kbs.append(kb)
            
        print(f"\nKB Name: {kb['name']}")
        print(f"  UUID: {kb['uuid']}")
        print(f"  Status: {status}")
        print(f"  Sources: {kb['sources']}")

    # 3. Summary of Action Items
    print("\n\n=== SUMMARY OF ACTION ITEMS ===")
    if misconfigured_kbs:
        print(f"Found {len(misconfigured_kbs)} Knowledge Bases that need attention:")
        for kb in misconfigured_kbs:
            issue = "Incorrect Prefix"
            if kb['pointing_to_root']: issue = "Points to Root (Global Access)"
            print(f"- {kb['name']} ({kb['uuid']}): {issue}. Sources: {kb['sources']}")
            print(f"  Expected Source: {do_client.settings.digitalocean_spaces_bucket}/{kb['name']}/")
    else:
        print("All Knowledge Bases appear to be correctly configured to their respective client folders.")

    # 3.5 Fetch agents for region and attachment checks
    agents = await do_client.list_agents()

    # 4. Export to CSV
    print("\n\n=== EXPORTING TO CSV ===")
    output_file = kb_master_reports_dir / 'client_audit_results.csv'
    
    # Pre-process KB data for merging by name (client slug)
    kb_map = {kb['name']: kb for kb in kb_audit}
    
    # Identify all unique dynamic keys (content types, doc sources) across all clients
    all_content_types = set()
    all_doc_sources = set()
    
    for stats in client_stats.values():
        all_content_types.update(stats['content_types'].keys())
        all_doc_sources.update(stats['document_sources'].keys())
        
    sorted_ct_keys = sorted(list(all_content_types))
    sorted_ds_keys = sorted(list(all_doc_sources))
    
    # Build Headers
    csv_headers = ['Client Name', 'Total Files', 'KB Status', 'KB UUID', 'KB Sources']
    # Dynamic Headers
    csv_headers.extend([f'Type: {k}' for k in sorted_ct_keys])
    csv_headers.extend([f'Source: {k}' for k in sorted_ds_keys])
    
    # All unique client names from both sources
    all_clients = set(client_stats.keys()) | set(kb_map.keys())
    
    try:
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_headers)
            writer.writeheader()
            
            for client in sorted(list(all_clients)):
                row = {'Client Name': client}
                
                # Fill Spaces Data
                if client in client_stats:
                    stats = client_stats[client]
                    row['Total Files'] = stats['total_files']
                    for ct, count in stats['content_types'].items():
                        row[f'Type: {ct}'] = count
                    for ds, count in stats['document_sources'].items():
                        row[f'Source: {ds}'] = count
                else:
                    # Client has a KB but no files in Spaces (or empty folder)
                    row['Total Files'] = 0
                
                # Fill KB Data
                if client in kb_map:
                    kb = kb_map[client]
                    status = "OK"
                    if not kb['is_correctly_configured']:
                        status = "MISCONFIGURED"
                    if kb['pointing_to_root']:
                        status = "DANGER (Points to Root)"
                        
                    row['KB Status'] = status
                    row['KB UUID'] = kb['uuid']
                    row['KB Sources'] = "; ".join(kb['sources'])
                else:
                    row['KB Status'] = "MISSING"
                    
                writer.writerow(row)
                
        print(f"Successfully exported audit results to {output_file}")
        
    except Exception as e:
        logger.error(f"Failed to write CSV: {e}")

    # 5. Emit per-client JSON and summary.json for _client_kb_master
    # 5a. Emit KB inspect details
    for kb in kb_audit:
        try:
            inspect_path = kb_inspect_dir / f"{kb['name']}.json"
            inspect_payload = {
                "knowledge_base": kb.get("raw", {}),
                "sources": kb.get("sources", []),
                "status": {
                    "is_correctly_configured": kb.get("is_correctly_configured"),
                    "pointing_to_root": kb.get("pointing_to_root"),
                },
            }
            inspect_path.write_text(json.dumps(inspect_payload, indent=2))
        except Exception as e:
            logger.error(f"Failed to write kb inspect for {kb.get('name')}: {e}")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "clients": len(all_clients),
            "kbs_ok": 0,
            "kbs_misconfigured": 0,
            "kbs_root": 0,
            "kbs_missing": 0,
            "clients_zero_files": 0,
            "clients_missing_intake": 0,  # not computed here
            "region_mismatches": 0,       # kb vs agent region
        },
        "agents": {
            "total": len(agents),
            "by_region": defaultdict(int),
            "with_kb_region_mismatch": 0,
            "list": [], 
        },
        "top_warnings": [],
        "reports": {
            "client_audit_results_csv": str(output_file.relative_to(kb_master_dir)),
            "kb_inspect_dir": "reports/kb_inspect/",
        },
    }

    # Helper to add warning
    def add_warning(slug: str, msg: str):
        summary["top_warnings"].append({"client_slug": slug, "warning": msg})

    # Build mapping for KB regions by uuid for agent checks
    kb_region_by_uuid = {}
    for kb in kb_audit:
        if kb.get("uuid"):
            kb_region_by_uuid[kb["uuid"]] = kb.get("region")

    # Agent region stats and mismatches
    for agent in agents:
        region = agent.get("region")
        if region:
            summary["agents"]["by_region"][region] += 1
        
        # Check KB mismatch
        kb_list = agent.get("knowledge_base_uuids") or agent.get("knowledge_bases") or []
        has_mismatch = False
        for kb_uuid in kb_list:
            kb_region = kb_region_by_uuid.get(kb_uuid)
            if kb_region and region and kb_region != region:
                has_mismatch = True
        
        if has_mismatch:
            summary["agents"]["with_kb_region_mismatch"] += 1
            summary["totals"]["region_mismatches"] += 1

        # Add agent summary
        summary["agents"]["list"].append({
            "name": agent.get("name"),
            "uuid": agent.get("uuid"),
            "region": region,
            "model_uuid": agent.get("model_uuid"),
            "knowledge_base_uuids": kb_list,
            "has_region_mismatch": has_mismatch
        })

    # Build per-client JSON
    for client in sorted(list(all_clients)):
        stats = client_stats.get(client, None)
        kb = kb_map.get(client, None)
        
        # Get metadata for this client
        meta = client_metadata.get(client, {})

        kb_status = "missing"
        if kb:
            kb_status = "ok" if kb["is_correctly_configured"] else "misconfigured"
            if kb["pointing_to_root"]:
                kb_status = "root"
        if kb_status == "ok":
            summary["totals"]["kbs_ok"] += 1
        elif kb_status == "misconfigured":
            summary["totals"]["kbs_misconfigured"] += 1
        elif kb_status == "root":
            summary["totals"]["kbs_root"] += 1
        elif kb_status == "missing":
            summary["totals"]["kbs_missing"] += 1

        # Counts
        total_files = stats["total_files"] if stats else 0
        if total_files == 0:
            summary["totals"]["clients_zero_files"] += 1
            add_warning(client, "zero files in Spaces")
            
        # Intake missing warning
        if not meta.get("intake_domain") and not meta.get("website"):
             summary["totals"]["clients_missing_intake"] += 1
             # Optional: add warning, but might be noisy if many are missing

        if kb_status == "misconfigured":
            add_warning(client, "KB misconfigured (prefix mismatch)")
        if kb_status == "root":
            add_warning(client, "KB points to root (global access risk)")
        if kb_status == "missing":
            add_warning(client, "KB missing")

        content_types = (stats or {}).get("content_types", {})
        document_sources = (stats or {}).get("document_sources", {})

        # Find agents associated with this client's KB
        client_agents = []
        if kb:
            kb_uuid = kb.get("uuid")
            for agent in agents:
                agent_kbs = agent.get("knowledge_base_uuids") or agent.get("knowledge_bases") or []
                if kb_uuid in agent_kbs:
                    client_agents.append(agent.get("name"))

        client_record = {
            "client_slug": client,
            "drive_folder_url": meta.get("drive_folder", ""),
            "website_url": meta.get("website", ""),
            "intake": {
                "intake_file_id": None, # Not strictly in CSVs, skipped for now
                "intake_domain": meta.get("intake_domain"),
                "checked_at": None,
                "status": meta.get("intake_status", "unknown"),
            },
            "kb": {
                "kb_uuid": kb.get("uuid") if kb else None,
                "kb_region": kb.get("region") if kb else None,
                "kb_tags": [],
                "kb_sources": kb.get("sources") if kb else [],
                "kb_status": kb_status,
                "last_audit_at": None,
                "details_ref": None,
            },
            "spaces": {
                "spaces_prefix": f"{client}/",
                "total_files": total_files,
                "content_types": content_types,
                "document_sources": document_sources,
                "last_audit_at": None,
            },
            "ingest": {
                "last_ingest_at": None,
                "last_reindex_at": None,
                "last_drive_sync_at": None,
            },
            "agents": client_agents,
            "warnings": [w["warning"] for w in summary["top_warnings"] if w["client_slug"] == client],
            "ui": {
                "title": None,
                "favicon": None,
            },
            "timestamps": {
                "created_at": None,
                "updated_at": None,
            },
        }

        client_json_path = kb_master_clients_dir / f"{client}.json"
        try:
            client_json_path.write_text(json.dumps(client_record, indent=2))
        except Exception as e:
            logger.error(f"Failed to write client JSON for {client}: {e}")

    # Write summary.json
    summary_path = kb_master_dir / "summary.json"
    # Convert defaultdicts for JSON
    summary["agents"]["by_region"] = dict(summary["agents"]["by_region"])

    try:
        summary_path.write_text(json.dumps(summary, indent=2))
        print(f"Wrote summary to {summary_path}")
    except Exception as e:
        logger.error(f"Failed to write summary.json: {e}")

    # 6. Upload _mintleads_kb_master to Spaces
    print("\n=== UPLOADING TO SPACES ===")
    await upload_directory_to_spaces(kb_master_dir, settings.digitalocean_spaces_bucket, "_mintleads_kb_master")

if __name__ == "__main__":
    asyncio.run(main())
