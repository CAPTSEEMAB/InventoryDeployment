import os
import json
import uuid
import boto3
from typing import Dict, List, Optional, Any
from datetime import datetime
from botocore.exceptions import ClientError
from pathlib import Path
from dotenv import load_dotenv
from .interfaces import QueueMessage, QueueStats

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ROOT_ENV, override=True)


class SQSClient:
    
    def __init__(self):
        self.sqs_client = boto3.client(
            'sqs',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_SQS_REGION', 'us-east-1')
        )
        
        self.region = os.getenv('AWS_SQS_REGION', 'us-east-1')
        self.account_id = self._get_account_id()
        
        # Queue URLs cache
        self._queue_urls = {}
    
    def _get_account_id(self) -> str:
        """Get AWS account ID"""
        try:
            sts = boto3.client('sts')
            return sts.get_caller_identity()['Account']
        except Exception:
            return "unknown"
    
    def _get_queue_url(self, queue_name: str) -> Optional[str]:
        """Get queue URL, with caching"""
        if queue_name in self._queue_urls:
            return self._queue_urls[queue_name]
        
        try:
            response = self.sqs_client.get_queue_url(QueueName=queue_name)
            self._queue_urls[queue_name] = response['QueueUrl']
            return response['QueueUrl']
        except ClientError as e:
            if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                return None
            raise e
    
    def create_queue(self, queue_name: str, dead_letter_queue_arn: Optional[str] = None, 
                     visibility_timeout: int = 30, message_retention_period: int = 1209600) -> str:
        try:
            existing_url = self._get_queue_url(queue_name)
            if existing_url:
                return existing_url
            
            attributes = {
                'VisibilityTimeoutSeconds': str(visibility_timeout),
                'MessageRetentionPeriod': str(message_retention_period),
                'ReceiveMessageWaitTimeSeconds': '20'  # Long polling
            }
            
            # Add dead letter queue if specified
            if dead_letter_queue_arn:
                attributes['RedrivePolicy'] = json.dumps({
                    'deadLetterTargetArn': dead_letter_queue_arn,
                    'maxReceiveCount': 3
                })
            
            response = self.sqs_client.create_queue(
                QueueName=queue_name,
                Attributes=attributes
            )
            
            queue_url = response['QueueUrl']
            self._queue_urls[queue_name] = queue_url
            return queue_url
            
        except ClientError as e:
            raise Exception(f"Failed to create queue {queue_name}: {e}")
    
    def send_message(self, queue_name: str, message: QueueMessage, delay_seconds: int = 0) -> bool:
        try:
            queue_url = self._get_queue_url(queue_name)
            if not queue_url:
                return False
            
            # Convert message to JSON
            message_body = message.model_dump_json()
            
            # Send message
            self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=message_body,
                DelaySeconds=delay_seconds,
                MessageAttributes={
                    'message_type': {
                        'StringValue': message.message_type,
                        'DataType': 'String'
                    },
                    'retry_count': {
                        'StringValue': str(message.retry_count),
                        'DataType': 'Number'
                    }
                }
            )
            
            return True
            
        except ClientError as e:
            return False
        except Exception as e:
            return False
    
    def receive_messages(self, queue_name: str, max_messages: int = 1, 
                        wait_time: int = 20) -> List[Dict[str, Any]]:
        try:
            queue_url = self._get_queue_url(queue_name)
            if not queue_url:
                return []
            
            response = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(max_messages, 10),
                WaitTimeSeconds=wait_time,
                MessageAttributeNames=['All'],
                AttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            parsed_messages = []
            
            for msg in messages:
                try:
                    # Parse message body
                    message_data = json.loads(msg['Body'])
                    queue_message = QueueMessage.model_validate(message_data)
                    
                    parsed_messages.append({
                        'message': queue_message,
                        'receipt_handle': msg['ReceiptHandle'],
                        'message_id': msg['MessageId'],
                        'raw_message': msg
                    })
                except Exception as parse_error:
                    continue
            
            return parsed_messages
            
        except ClientError as e:
            return []
        except Exception as e:
            return []
    
    def delete_message(self, queue_name: str, receipt_handle: str) -> bool:
        try:
            queue_url = self._get_queue_url(queue_name)
            if not queue_url:
                return False
            
            self.sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            
            return True
            
        except ClientError as e:
            return False
        except Exception as e:
            return False
    
    def get_queue_stats(self, queue_name: str) -> Optional[QueueStats]:
        try:
            queue_url = self._get_queue_url(queue_name)
            if not queue_url:
                return None
            
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['All']
            )
            
            attributes = response['Attributes']
            
            return QueueStats(
                queue_name=queue_name,
                visible_messages=int(attributes.get('ApproximateNumberOfMessages', 0)),
                in_flight_messages=int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                delayed_messages=int(attributes.get('ApproximateNumberOfMessagesDelayed', 0)),
                created_timestamp=datetime.fromtimestamp(int(attributes.get('CreatedTimestamp', 0)))
            )
            
        except ClientError as e:
            return None
        except Exception as e:
            return None
    
    def purge_queue(self, queue_name: str) -> bool:
        try:
            queue_url = self._get_queue_url(queue_name)
            if not queue_url:
                return False
            
            self.sqs_client.purge_queue(QueueUrl=queue_url)
            return True
            
        except ClientError as e:
            return False
        except Exception as e:
            return False
    
    def list_queues(self, prefix: str = "") -> List[str]:
        try:
            if prefix:
                response = self.sqs_client.list_queues(QueueNamePrefix=prefix)
            else:
                response = self.sqs_client.list_queues()
            
            queue_urls = response.get('QueueUrls', [])
            queue_names = [url.split('/')[-1] for url in queue_urls]
            
            return queue_names
            
        except ClientError as e:
            return []
        except Exception as e:
            return []