import os
import sys
import boto3
from pathlib import Path
from botocore.exceptions import ClientError

# Add project root to path to import config
sys.path.append(str(Path.cwd()))

from backend.app.config import get_settings

def test_spaces_connection():
    print("--- Testing DigitalOcean Spaces Credentials ---")
    
    settings = get_settings()
    
    key = settings.digitalocean_spaces_key
    secret = settings.digitalocean_spaces_secret
    region = settings.digitalocean_spaces_region
    bucket = settings.digitalocean_spaces_bucket
    
    print(f"Key ID: {'*' * 10}{key[-4:] if key else 'None'}")
    print(f"Secret: {'*' * 10}{secret[-4:] if secret else 'None'}")
    print(f"Region: {region}")
    print(f"Bucket: {bucket}")
    print("-" * 40)

    if not key or not secret or not region or not bucket:
        print("❌ Missing configuration. Please check your .env file.")
        return

    try:
        session = boto3.session.Session()
        client = session.client(
            's3',
            region_name=region,
            endpoint_url=f"https://{region}.digitaloceanspaces.com",
            aws_access_key_id=key,
            aws_secret_access_key=secret
        )
        
        print(f"Attempting to list objects in bucket '{bucket}'...")
        # Try to list 1 object to verify read access
        client.list_objects_v2(Bucket=bucket, MaxKeys=1)
        print("✅ Read Access: Success")
        
        # Try to upload a small test file to verify write access
        test_filename = "connection_test.txt"
        print(f"Attempting to upload test file '{test_filename}'...")
        client.put_object(
            Bucket=bucket,
            Key=test_filename,
            Body=b"Connection test successful.",
            ACL="private",
            ContentType="text/plain"
        )
        print("✅ Write Access: Success")
        
        # Cleanup
        print("Cleaning up test file...")
        client.delete_object(Bucket=bucket, Key=test_filename)
        print("✅ Delete Access: Success")
        
        print("\n🎉 All checks passed! Your Spaces credentials are valid.")

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        print(f"\n❌ Operation Failed: {error_code}")
        print(f"Message: {error_msg}")
        
        if error_code == "InvalidAccessKeyId":
            print("\n👉 Diagnosis: The Access Key ID is invalid or does not exist.")
        elif error_code == "SignatureDoesNotMatch":
            print("\n👉 Diagnosis: The Secret Access Key is incorrect.")
        elif error_code == "NoSuchBucket":
            print("\n👉 Diagnosis: The bucket name is incorrect or does not exist.")
            
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")

if __name__ == "__main__":
    test_spaces_connection()

