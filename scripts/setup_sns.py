#!/usr/bin/env python3
import boto3
import os
from pathlib import Path
from dotenv import load_dotenv, set_key

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def setup_sns():
    print("=" * 70)
    print("SNS SETUP - Creating Notification Topic")
    print("=" * 70)
    
    try:
        sns = boto3.client('sns',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_SNS_REGION', 'us-east-1'))
        print(f"\nConnected to AWS SNS")
    except Exception as e:
        print(f"\nFailed: {e}")
        return False
    
    topic_arn = os.getenv('AWS_SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:669688919516:product-notifications')
    
    try:
        # Get topic attributes to verify it exists
        attrs = sns.get_topic_attributes(TopicArn=topic_arn)
        display_name = attrs['Attributes'].get('DisplayName', 'N/A')
        
        # Get subscriptions
        resp = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
        subs = resp.get('Subscriptions', [])
        confirmed = [s for s in subs if s['SubscriptionArn'] != 'PendingConfirmation']
        pending = [s for s in subs if s['SubscriptionArn'] == 'PendingConfirmation']
        
        print(f"\nTopic already exists")
        print(f"Topic ARN: {topic_arn}")
        print(f"Display Name: {display_name}")
        print(f"Confirmed subscribers: {len(confirmed)}")
        
        if confirmed:
            print(f"\nSubscribers:")
            for sub in confirmed:
                print(f"  - {sub['Protocol']}: {sub['Endpoint']}")
        
        if pending:
            print(f"Pending confirmations: {len(pending)}")
        
        set_key(env_path, 'AWS_SNS_TOPIC_ARN', topic_arn)
        set_key(env_path, 'SNS_TOPIC_ARN', topic_arn)
        return True
        
    except sns.exceptions.NotFoundException:
        print(f"\n[1/1] Creating Topic: product-notifications")
        print("-" * 70)
        
        try:
            resp = sns.create_topic(
                Name='product-notifications',
                Attributes={'DisplayName': 'Product Notifications'}
            )
            new_arn = resp['TopicArn']
            print(f"Topic created: {new_arn}")
            print("\nTo add email subscriptions:")
            print("   1. Go to AWS SNS Console")
            print("   2. Find topic: product-notifications")
            print("   3. Create subscription -> Email")
            print("   4. Confirm subscription email")
            
            set_key(env_path, 'AWS_SNS_TOPIC_ARN', new_arn)
            set_key(env_path, 'SNS_TOPIC_ARN', new_arn)
            return True
            
        except Exception as e:
            print(f"Error creating topic: {e}")
            return False
    
    except Exception as e:
        print(f"Error checking topic: {e}")
        return False

if __name__ == "__main__":
    print("\nStarting SNS Setup...\n")
    if setup_sns():
        print("\n" + "=" * 70)
        print("SNS SETUP COMPLETE!")
        print("=" * 70 + "\n")
    else:
        print("\nSETUP FAILED\n")
        exit(1)
