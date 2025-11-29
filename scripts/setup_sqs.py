#!/usr/bin/env python3
import boto3
import os
from pathlib import Path
from dotenv import load_dotenv, set_key

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def setup_sqs():
    print("=" * 70)
    print("SQS SETUP - Creating Notification Queue")
    print("=" * 70)
    
    try:
        sqs = boto3.client('sqs',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_SQS_REGION', 'us-east-1'))
        print(f"\nConnected to AWS SQS")
    except Exception as e:
        print(f"\nFailed: {e}")
        return False
    
    queue_url = os.getenv('AWS_SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/669688919516/notification-processing-queue')
    
    try:
        # Get queue attributes to verify it exists
        resp = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['All']
        )
        attrs = resp['Attributes']
        
        print(f"\nQueue already exists")
        print(f"Queue URL: {queue_url}")
        print(f"Queue Name: notification-processing-queue")
        print(f"Messages available: {attrs.get('ApproximateNumberOfMessages', 0)}")
        print(f"Messages in flight: {attrs.get('ApproximateNumberOfMessagesNotVisible', 0)}")
        print(f"Visibility timeout: {attrs.get('VisibilityTimeout', 0)} seconds")
        print(f"Retention period: {int(attrs.get('MessageRetentionPeriod', 0)) // 86400} days")
        print(f"Long polling: {attrs.get('ReceiveMessageWaitTimeSeconds', 0)} seconds")
        
        set_key(env_path, 'AWS_SQS_QUEUE_URL', queue_url)
        set_key(env_path, 'SQS_QUEUE_URL', queue_url)
        return True
        
    except sqs.exceptions.QueueDoesNotExist:
        print(f"\n[1/1] Creating Queue: notification-processing-queue")
        print("-" * 70)
        
        try:
            resp = sqs.create_queue(
                QueueName='notification-processing-queue',
                Attributes={
                    'VisibilityTimeout': '60',
                    'MessageRetentionPeriod': '345600',
                    'ReceiveMessageWaitTimeSeconds': '10'
                }
            )
            new_url = resp['QueueUrl']
            print(f"Queue created: {new_url}")
            print(f"Visibility timeout: 60 seconds")
            print(f"Message retention: 4 days")
            print(f"Long polling: 10 seconds")
            
            set_key(env_path, 'AWS_SQS_QUEUE_URL', new_url)
            set_key(env_path, 'SQS_QUEUE_URL', new_url)
            return True
            
        except Exception as e:
            print(f"Error creating queue: {e}")
            return False
    
    except Exception as e:
        print(f"Error checking queue: {e}")
        return False

if __name__ == "__main__":
    print("\nStarting SQS Setup...\n")
    if setup_sqs():
        print("\n" + "=" * 70)
        print("SQS SETUP COMPLETE!")
        print("=" * 70 + "\n")
    else:
        print("\nSETUP FAILED\n")
        exit(1)
