#!/usr/bin/env python3
import boto3
import os
from pathlib import Path
from dotenv import load_dotenv, set_key

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def setup_s3():
    print("=" * 70)
    print("S3 SETUP - Creating Storage Bucket")
    print("=" * 70)
    
    try:
        s3 = boto3.client('s3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_S3_REGION', 'us-east-1'))
        print(f"\nConnected to AWS S3")
    except Exception as e:
        print(f"\nFailed: {e}")
        return False
    
    bucket = os.getenv('AWS_S3_BUCKET_NAME', 'inventory-bulk-data-1763464996')
    
    try:
        s3.head_bucket(Bucket=bucket)
        resp = s3.list_objects_v2(Bucket=bucket, MaxKeys=100)
        file_count = resp.get('KeyCount', 0)
        print(f"\nBucket already exists: {bucket}")
        print(f"Bucket is accessible")
        print(f"Files in bucket: {file_count}")
        
        if file_count > 0 and 'Contents' in resp:
            print(f"\nRecent files:")
            for obj in resp['Contents'][:5]:
                size_kb = obj['Size'] / 1024
                print(f"  - {obj['Key']} ({size_kb:.1f} KB)")
        
        set_key(env_path, 'AWS_S3_BUCKET_NAME', bucket)
        return True
        
    except s3.exceptions.NoSuchBucket:
        print(f"\n[1/1] Creating Bucket: {bucket}")
        print("-" * 70)
        
        try:
            region = os.getenv('AWS_S3_REGION', 'us-east-1')
            if region == 'us-east-1':
                s3.create_bucket(Bucket=bucket)
            else:
                s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={'LocationConstraint': region})
            
            print(f"Bucket created: {bucket}")
            
            s3.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={'Status': 'Enabled'})
            print("Versioning enabled")
            
            s3.put_bucket_encryption(Bucket=bucket, ServerSideEncryptionConfiguration={
                'Rules': [{'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]
            })
            print("Encryption enabled")
            
            s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            })
            print("Public access blocked")
            
            set_key(env_path, 'AWS_S3_BUCKET_NAME', bucket)
            return True
            
        except Exception as e:
            print(f"Error creating bucket: {e}")
            return False
    
    except Exception as e:
        print(f"Error checking bucket: {e}")
        return False

if __name__ == "__main__":
    print("\nStarting S3 Setup...\n")
    if setup_s3():
        print("\n" + "=" * 70)
        print("S3 SETUP COMPLETE!")
        print("=" * 70 + "\n")
    else:
        print("\nSETUP FAILED\n")
        exit(1)
