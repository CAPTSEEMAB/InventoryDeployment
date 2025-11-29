import boto3
import os
import jwt
import requests
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class CognitoClient:
    def __init__(self):
        self.region = os.getenv('AWS_COGNITO_REGION', 'us-east-1')
        self.user_pool_id = os.getenv('AWS_COGNITO_USER_POOL_ID')
        self.client_id = os.getenv('AWS_COGNITO_CLIENT_ID')
        
        self.cognito = boto3.client(
            'cognito-idp',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=self.region
        )
        self._jwks = None
        
    def get_jwks(self):
        if self._jwks is None:
            jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
            self._jwks = requests.get(jwks_url).json()
        return self._jwks
    
    def sign_up(self, email: str, password: str, name: str, role: str = "USER") -> Dict[str, Any]:
        try:
            response = self.cognito.sign_up(
                ClientId=self.client_id,
                Username=email,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'name', 'Value': name}
                ]
            )
            return {'success': True, 'message': 'User created successfully', 'user_sub': response['UserSub']}
        except Exception as e:
            return {'success': False, 'message': str(e), 'error': str(e)}
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        try:
            # Try with email/username as provided first
            try:
                response = self.cognito.initiate_auth(
                    ClientId=self.client_id,
                    AuthFlow='USER_PASSWORD_AUTH',
                    AuthParameters={'USERNAME': email, 'PASSWORD': password}
                )
            except:
                # If email fails, try to find username by listing users
                users_response = self.cognito.list_users(
                    UserPoolId=self.user_pool_id,
                    Filter=f'email = "{email}"',
                    Limit=1
                )
                if users_response['Users']:
                    username = users_response['Users'][0]['Username']
                    response = self.cognito.initiate_auth(
                        ClientId=self.client_id,
                        AuthFlow='USER_PASSWORD_AUTH',
                        AuthParameters={'USERNAME': username, 'PASSWORD': password}
                    )
                else:
                    raise Exception("User not found")
            
            return {
                'success': True,
                'message': 'Login successful',
                'token': response['AuthenticationResult']['AccessToken'],
                'id_token': response['AuthenticationResult']['IdToken'],
                'refresh_token': response['AuthenticationResult']['RefreshToken'],
                'expires_in': response['AuthenticationResult'].get('ExpiresIn', 3600),
                'user': {'email': email}
            }
        except Exception as e:
            return {'success': False, 'message': str(e), 'error': str(e)}
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        try:
            import json
            from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization
            import base64
            
            jwks = self.get_jwks()
            unverified_header = jwt.get_unverified_header(token)
            rsa_key = None
            
            for key in jwks['keys']:
                if key['kid'] == unverified_header['kid']:
                    # Convert JWK to PEM format
                    n = base64.urlsafe_b64decode(key['n'] + '==')
                    e = base64.urlsafe_b64decode(key['e'] + '==')
                    n_int = int.from_bytes(n, 'big')
                    e_int = int.from_bytes(e, 'big')
                    
                    public_numbers = RSAPublicNumbers(e_int, n_int)
                    public_key = public_numbers.public_key(default_backend())
                    rsa_key = public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )
                    break
            
            if not rsa_key:
                return {'valid': False, 'message': 'Public key not found'}
            
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=['RS256'],
                options={'verify_exp': True, 'verify_aud': False}
            )
            
            return {'valid': True, 'user': payload}
        except Exception as e:
            return {'valid': False, 'message': str(e)}

_client = None
def get_cognito_client():
    global _client
    if not _client:
        _client = CognitoClient()
    return _client
