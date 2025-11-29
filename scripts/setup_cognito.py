#!/usr/bin/env python3
"""AWS Cognito Setup Script"""

import boto3
import os
from pathlib import Path
from dotenv import load_dotenv, set_key

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def setup_cognito():
    print("=" * 70)
    print("COGNITO SETUP - Creating User Pool & App Client")
    print("=" * 70)
    
    try:
        cognito = boto3.client('cognito-idp',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1'))
        print(f"\nConnected to AWS Cognito in region: {os.getenv('AWS_REGION', 'us-east-1')}")
    except Exception as e:
        print(f"\nFailed to connect to AWS: {e}")
        return False
    
    # Use existing pool ID from .env or default
    existing_pool_id = os.getenv('COGNITO_USER_POOL_ID') or os.getenv('AWS_COGNITO_USER_POOL_ID', 'us-east-1_Uu6LQa4l0')
    existing_client_id = os.getenv('COGNITO_APP_CLIENT_ID') or os.getenv('AWS_COGNITO_CLIENT_ID', '139o1ehs7pkvsmqb3cheatvbv5')
    
    try:
        pool = cognito.describe_user_pool(UserPoolId=existing_pool_id)
        pool_name = pool['UserPool']['Name']
        
        print(f"\nUser Pool already exists")
        print(f"User Pool ID: {existing_pool_id}")
        print(f"Pool Name: {pool_name}")
        print(f"App Client ID: {existing_client_id}")
        
        # Update .env with both variable names for compatibility
        set_key(env_path, 'COGNITO_USER_POOL_ID', existing_pool_id)
        set_key(env_path, 'AWS_COGNITO_USER_POOL_ID', existing_pool_id)
        set_key(env_path, 'COGNITO_APP_CLIENT_ID', existing_client_id)
        set_key(env_path, 'AWS_COGNITO_CLIENT_ID', existing_client_id)
        return True
        
    except cognito.exceptions.ResourceNotFoundException:
        print(f"\nExisting pool not found, creating new one...")
    
    print(f"\n[1/2] Creating Cognito User Pool")
    print("-" * 70)
    
    try:
        response = cognito.create_user_pool(
            PoolName='inventory-user-pool',
            Policies={'PasswordPolicy': {'MinimumLength': 8, 'RequireUppercase': True, 'RequireLowercase': True, 'RequireNumbers': True, 'RequireSymbols': False}},
            AutoVerifiedAttributes=['email'],
            UsernameAttributes=['email'],
            UsernameConfiguration={'CaseSensitive': False},
            Schema=[{'Name': 'email', 'AttributeDataType': 'String', 'Required': True, 'Mutable': True}]
        )
        user_pool_id = response['UserPool']['Id']
        print(f"User Pool created: {user_pool_id}")
        set_key(env_path, 'COGNITO_USER_POOL_ID', user_pool_id)
        set_key(env_path, 'AWS_COGNITO_USER_POOL_ID', user_pool_id)
    except Exception as e:
        print(f"Error creating user pool: {e}")
        return False
    
    print(f"\n[2/2] Creating App Client")
    print("-" * 70)
    
    try:
        response = cognito.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName='inventory-api-client',
            GenerateSecret=False,
            ExplicitAuthFlows=['ALLOW_USER_PASSWORD_AUTH', 'ALLOW_REFRESH_TOKEN_AUTH', 'ALLOW_USER_SRP_AUTH'],
            PreventUserExistenceErrors='ENABLED'
        )
        app_client_id = response['UserPoolClient']['ClientId']
        print(f"App Client created: {app_client_id}")
        set_key(env_path, 'COGNITO_APP_CLIENT_ID', app_client_id)
        set_key(env_path, 'AWS_COGNITO_CLIENT_ID', app_client_id)
        return True
    except Exception as e:
        print(f"Error creating app client: {e}")
        return False

def verify_cognito():
    print("\n" + "=" * 70)
    print("VERIFICATION - Testing Cognito Access")
    print("=" * 70)
    try:
        # Reload env to get updated values
        load_dotenv(dotenv_path=env_path, override=True)
        cognito = boto3.client('cognito-idp',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1'))
        pool_id = os.getenv('COGNITO_USER_POOL_ID')
        pool = cognito.describe_user_pool(UserPoolId=pool_id)
        print(f"\nUser Pool '{pool['UserPool']['Name']}' is accessible")
        print(f"Pool ID: {pool_id}")
        return True
    except Exception as e:
        print(f"\nVerification failed: {e}")
        return False

if __name__ == "__main__":
    print("\nStarting Cognito Setup...\n")
    if not os.getenv('AWS_ACCESS_KEY_ID'):
        print("AWS_ACCESS_KEY_ID not found in .env file")
        exit(1)
    if not os.getenv('AWS_SECRET_ACCESS_KEY'):
        print("AWS_SECRET_ACCESS_KEY not found in .env file")
        exit(1)
    
    success = setup_cognito()
    if success:
        verify_cognito()
        print("\n" + "=" * 70)
        print("COGNITO SETUP COMPLETE!")
        print("=" * 70 + "\n")
    else:
        print("\n" + "=" * 70)
        print("SETUP FAILED")
        print("=" * 70 + "\n")
        exit(1)
