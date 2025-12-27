import boto3
import logging
import sys
from pathlib import Path
from botocore.client import Config

# Add backend directory to path so we can import app modules
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("share_links")

def generate_presigned_url(bucket: str, key: str, expiration: int = 3600):
    settings = get_settings()
    
    if not (settings.digitalocean_spaces_key and settings.digitalocean_spaces_secret and settings.digitalocean_spaces_region):
        logger.error("DigitalOcean Spaces credentials missing.")
        return None

    try:
        session = boto3.session.Session()
        client = session.client('s3',
                                region_name=settings.digitalocean_spaces_region,
                                endpoint_url=f"https://{settings.digitalocean_spaces_region}.digitaloceanspaces.com",
                                aws_access_key_id=settings.digitalocean_spaces_key,
                                aws_secret_access_key=settings.digitalocean_spaces_secret,
                                config=Config(signature_version='s3v4'))

        url = client.generate_presigned_url(ClientMethod='get_object',
                                            Params={
                                                'Bucket': bucket,
                                                'Key': key,
                                            },
                                            ExpiresIn=expiration)
        return url
    except Exception as e:
        logger.error(f"Error generating presigned URL for {key}: {e}")
        return None

def main():
    settings = get_settings()
    bucket = settings.digitalocean_spaces_bucket
    
    if not bucket:
        logger.error("Bucket name not configured.")
        return

    # Files to generate links for
    files_to_share = [
        "_client_kb_master/summary.json",
        "_client_kb_master/reports/client_audit_results.csv"
    ]
    
    print("\n=== GENERATING PRESIGNED URLs ===\n")
    
    for file_key in files_to_share:
        # Expiration set to 7 days (604800 seconds) or similar if needed, asking for 1 hour default
        # User didn't specify expiration, using 7 days for utility
        expiration = 604800 
        url = generate_presigned_url(bucket, file_key, expiration)
        
        if url:
            print(f"File: {file_key}")
            print(f"Link (Expires in 7 days): {url}\n")
        else:
            print(f"Failed to generate link for {file_key}\n")

if __name__ == "__main__":
    main()

