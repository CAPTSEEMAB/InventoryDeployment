import os
import boto3
from typing import List, Dict, Optional, BinaryIO
from pathlib import Path
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Load environment variables
ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ROOT_ENV, override=True)


class S3Client:    
    def __init__(self):
        self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_S3_REGION', 'us-east-1')
        self.bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
        
        if not all([self.aws_access_key_id, self.aws_secret_access_key, self.bucket_name]):
            raise ValueError("Missing S3 configuration in environment variables")
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )
        

    
    def upload_file(self, file_content: bytes, file_key: str, content_type: str = 'application/octet-stream') -> bool:
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_content,
                ContentType=content_type
            )
            return True
            
        except ClientError as e:
            return False
        except Exception as e:
            return False
    
    def download_file(self, file_key: str) -> Optional[bytes]:
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            content = response['Body'].read()
            return content
            
        except ClientError as e:
            return None
        except Exception as e:
            return None
    
    def list_files(self, prefix: str = '') -> List[Dict]:
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'etag': obj['ETag'].strip('"')
                    })
            
            return files
            
        except ClientError as e:
            return []
        except Exception as e:
            return []
    
    def delete_file(self, file_key: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            return True
            
        except ClientError as e:
            return False
        except Exception as e:
            return False
    
    def file_exists(self, file_key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError:
            return False
        except Exception:
            return False
    
    def get_file_url(self, file_key: str, expiration: int = 3600) -> Optional[str]:
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expiration
            )
            return url
            
        except ClientError as e:
            return None
        except Exception as e:
            return None