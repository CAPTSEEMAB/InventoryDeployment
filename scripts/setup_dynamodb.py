#!/usr/bin/env python3
"""DynamoDB Setup Script"""
import boto3, os
from pathlib import Path
from dotenv import load_dotenv, set_key

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def setup_dynamodb():
    print("="*70 + "\nDYNAMODB SETUP - Creating Product Table\n" + "="*70)
    try:
        dynamodb = boto3.client('dynamodb', aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'), region_name=os.getenv('AWS_REGION', 'us-east-1'))
        print(f"\nConnected to AWS DynamoDB")
    except Exception as e:
        print(f"\nFailed: {e}"); return False
    
    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'inventory-products').strip("'")
    try:
        resp = dynamodb.describe_table(TableName=table_name)
        print(f"\nTable already exists")
        print(f"Table Name: {table_name}")
        print(f"Status: {resp['Table']['TableStatus']}")
        print(f"Items: {resp['Table']['ItemCount']}")
        
        # Show indexes
        gsi = resp['Table'].get('GlobalSecondaryIndexes', [])
        if gsi:
            print(f"Global Secondary Indexes: {len(gsi)}")
            for index in gsi:
                print(f"  - {index['IndexName']}")
        
        set_key(env_path, 'DYNAMODB_TABLE_NAME', table_name)
        return True
    except dynamodb.exceptions.ResourceNotFoundException:
        print(f"\n[1/1] Creating Table: {table_name}\n" + "-"*70)
        try:
            dynamodb.create_table(TableName=table_name, KeySchema=[{'AttributeName':'product_id','KeyType':'HASH'}],
                AttributeDefinitions=[{'AttributeName':'product_id','AttributeType':'S'},{'AttributeName':'category','AttributeType':'S'},{'AttributeName':'SKU','AttributeType':'S'}],
                GlobalSecondaryIndexes=[{'IndexName':'category-index','KeySchema':[{'AttributeName':'category','KeyType':'HASH'}],'Projection':{'ProjectionType':'ALL'}},
                    {'IndexName':'SKU-index','KeySchema':[{'AttributeName':'SKU','KeyType':'HASH'}],'Projection':{'ProjectionType':'ALL'}}], BillingMode='PAY_PER_REQUEST')
            print(f"Table created: {table_name}")
            dynamodb.get_waiter('table_exists').wait(TableName=table_name)
            set_key(env_path, 'DYNAMODB_TABLE_NAME', table_name)
            return True
        except Exception as e:
            print(f"Error: {e}"); return False

if __name__ == "__main__":
    print("\nStarting DynamoDB Setup...\n")
    if setup_dynamodb():
        print("\n" + "="*70 + "\nDYNAMODB SETUP COMPLETE!\n" + "="*70 + "\n")
    else:
        print("\nSETUP FAILED\n"); exit(1)
