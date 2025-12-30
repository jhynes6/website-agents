"""
Inspect S3 object metadata in DigitalOcean Spaces.

This script allows you to view both standard S3 metadata and custom metadata
(x-amz-meta-*) for objects in a DigitalOcean Spaces bucket.
"""

import sys
import json
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

import boto3
from app.config import get_settings


def list_objects_with_metadata(bucket: str, prefix: str = "", max_keys: int = 50, region: str = "tor1"):
    """
    List objects in a Space and display their metadata.
    
    Args:
        bucket: Bucket/Space name
        prefix: Prefix to filter objects (e.g., "client-name/")
        max_keys: Maximum number of objects to list
        region: DigitalOcean region (tor1, nyc3, sfo3, etc.)
    """
    settings = get_settings()
    
    # Initialize S3 client
    s3 = boto3.client(
        's3',
        endpoint_url=f'https://{region}.digitaloceanspaces.com',
        aws_access_key_id=settings.digitalocean_spaces_key,
        aws_secret_access_key=settings.digitalocean_spaces_secret,
        region_name=region
    )
    
    print(f"\n{'='*80}")
    print(f"Listing objects in: {bucket}/{prefix}")
    print(f"Region: {region}")
    print(f"{'='*80}\n")
    
    try:
        # List objects
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=max_keys)
        
        if 'Contents' not in response or len(response['Contents']) == 0:
            print("No objects found.")
            return
        
        objects = response['Contents']
        print(f"Found {len(objects)} objects (max: {max_keys})")
        print()
        
        for idx, obj in enumerate(objects, 1):
            key = obj['Key']
            size = obj['Size']
            last_modified = obj['LastModified']
            
            # Skip directories (keys ending with /)
            if key.endswith('/'):
                print(f"{idx}. {key} [DIRECTORY]")
                continue
            
            print(f"{idx}. {key}")
            print(f"   Size: {size:,} bytes")
            print(f"   Last Modified: {last_modified}")
            
            # Get detailed metadata
            try:
                head = s3.head_object(Bucket=bucket, Key=key)
                
                # Standard S3 metadata
                print(f"   Content-Type: {head.get('ContentType', 'N/A')}")
                print(f"   ETag: {head.get('ETag', 'N/A')}")
                
                # Custom metadata (x-amz-meta-*)
                metadata = head.get('Metadata', {})
                if metadata:
                    print(f"   ✅ Custom Metadata:")
                    for meta_key, meta_value in sorted(metadata.items()):
                        print(f"      {meta_key}: {meta_value}")
                else:
                    print(f"   ❌ No custom metadata (x-amz-meta-*)")
                
            except Exception as e:
                print(f"   ⚠️  Error retrieving metadata: {e}")
            
            print()
        
        # Show if there are more objects
        if response.get('IsTruncated', False):
            print(f"⚠️  More objects available. Increase max_keys to see more.")
    
    except Exception as e:
        print(f"❌ Error: {e}")


def inspect_single_object(bucket: str, key: str, region: str = "tor1"):
    """
    Inspect metadata for a single object.
    
    Args:
        bucket: Bucket/Space name
        key: Object key (full path)
        region: DigitalOcean region
    """
    settings = get_settings()
    
    # Initialize S3 client
    s3 = boto3.client(
        's3',
        endpoint_url=f'https://{region}.digitaloceanspaces.com',
        aws_access_key_id=settings.digitalocean_spaces_key,
        aws_secret_access_key=settings.digitalocean_spaces_secret,
        region_name=region
    )
    
    print(f"\n{'='*80}")
    print(f"Inspecting: {bucket}/{key}")
    print(f"Region: {region}")
    print(f"{'='*80}\n")
    
    try:
        head = s3.head_object(Bucket=bucket, Key=key)
        
        print("Standard Metadata:")
        print(f"  ContentType: {head.get('ContentType')}")
        print(f"  ContentLength: {head.get('ContentLength'):,} bytes")
        print(f"  LastModified: {head.get('LastModified')}")
        print(f"  ETag: {head.get('ETag')}")
        print(f"  VersionId: {head.get('VersionId', 'N/A')}")
        print(f"  StorageClass: {head.get('StorageClass', 'STANDARD')}")
        print()
        
        print("Custom Metadata (x-amz-meta-*):")
        metadata = head.get('Metadata', {})
        if metadata:
            for meta_key, meta_value in sorted(metadata.items()):
                print(f"  {meta_key}: {meta_value}")
        else:
            print("  (none)")
        print()
        
        print("All Response Keys:")
        print(f"  {', '.join(sorted(head.keys()))}")
        print()
        
        # Pretty print full response as JSON
        print("Full Response (JSON):")
        # Convert datetime objects to strings for JSON serialization
        response_json = {}
        for k, v in head.items():
            if hasattr(v, 'isoformat'):
                response_json[k] = v.isoformat()
            else:
                response_json[k] = v
        print(json.dumps(response_json, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Error: {e}")


def interactive_mode():
    """Interactive mode for browsing Spaces."""
    settings = get_settings()
    
    print("\n" + "="*80)
    print("DigitalOcean Spaces Metadata Inspector")
    print("="*80)
    
    # Get bucket
    bucket = input(f"\nBucket name [{settings.digitalocean_spaces_bucket}]: ").strip()
    if not bucket:
        bucket = settings.digitalocean_spaces_bucket
    
    # Get region
    region = input(f"Region [tor1]: ").strip() or "tor1"
    
    while True:
        print("\n" + "-"*80)
        print("Options:")
        print("  1. List objects with metadata (by prefix)")
        print("  2. Inspect single object")
        print("  q. Quit")
        print("-"*80)
        
        choice = input("\nChoice: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == '1':
            prefix = input("Prefix (e.g., 'client-name/'): ").strip()
            max_keys = input("Max keys [50]: ").strip()
            max_keys = int(max_keys) if max_keys else 50
            list_objects_with_metadata(bucket, prefix, max_keys, region)
        elif choice == '2':
            key = input("Object key (full path): ").strip()
            if key:
                inspect_single_object(bucket, key, region)
        else:
            print("Invalid choice")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Inspect S3 object metadata in DigitalOcean Spaces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python inspect_spaces_metadata.py
  
  # List objects in a prefix
  python inspect_spaces_metadata.py --bucket mintleads-clients-kb --prefix wendt-partners/website/
  
  # Inspect a single object
  python inspect_spaces_metadata.py --bucket mintleads-clients-kb --key wendt-partners/website/sense.json
  
  # Use a different region
  python inspect_spaces_metadata.py --bucket my-bucket --prefix clients/ --region nyc3
        """
    )
    
    parser.add_argument("--bucket", "-b", help="Bucket/Space name", type=str)
    parser.add_argument("--prefix", "-p", help="Prefix to filter objects", type=str, default="")
    parser.add_argument("--key", "-k", help="Single object key to inspect", type=str)
    parser.add_argument("--region", "-r", help="DigitalOcean region (default: tor1)", type=str, default="tor1")
    parser.add_argument("--max-keys", "-m", help="Maximum number of objects to list (default: 50)", type=int, default=50)
    
    args = parser.parse_args()
    
    # Command-line mode
    if args.bucket:
        if args.key:
            # Inspect single object
            inspect_single_object(args.bucket, args.key, args.region)
        else:
            # List objects
            list_objects_with_metadata(args.bucket, args.prefix, args.max_keys, args.region)
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()

