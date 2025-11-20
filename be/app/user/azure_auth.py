import jwt
import requests
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import base64

class AzureADAuth:
    """Azure AD authentication utilities."""
    
    def __init__(self):
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.enabled = bool(self.tenant_id and self.client_id)
        
        if not self.enabled:
            print("Azure AD SSO is disabled. AZURE_TENANT_ID and AZURE_CLIENT_ID not configured.")
        
        # Cache for public keys
        self._public_keys_cache = {}
        self._cache_expiry = None
    
    def _get_public_keys(self) -> Dict[str, Any]:
        """
        Get Azure AD public keys for JWT verification.
        
        :return: Dictionary of public keys indexed by key ID.
        """
        # Check cache first
        if self._cache_expiry and datetime.utcnow() < self._cache_expiry and self._public_keys_cache:
            return self._public_keys_cache
        
        try:
            # Get OpenID configuration
            config_url = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0/.well-known/openid-configuration"
            config_response = requests.get(config_url, timeout=10)
            config_response.raise_for_status()
            config = config_response.json()
            
            # Get JWKS (JSON Web Key Set)
            jwks_url = config["jwks_uri"]
            jwks_response = requests.get(jwks_url, timeout=10)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()
            
            # Parse keys
            public_keys = {}
            for key in jwks["keys"]:
                if key["kty"] == "RSA" and key["use"] == "sig":
                    # Convert JWK to PEM format
                    n = base64.urlsafe_b64decode(key["n"] + "==")
                    e = base64.urlsafe_b64decode(key["e"] + "==")
                    
                    # Create RSA public key
                    public_numbers = rsa.RSAPublicNumbers(
                        int.from_bytes(e, byteorder='big'),
                        int.from_bytes(n, byteorder='big')
                    )
                    public_key = public_numbers.public_key()
                    
                    # Convert to PEM format
                    pem = public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )
                    
                    public_keys[key["kid"]] = pem
            
            # Cache keys for 1 hour
            self._public_keys_cache = public_keys
            self._cache_expiry = datetime.utcnow() + timedelta(hours=1)
            
            return public_keys
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get Azure AD public keys: {str(e)}"
            )
    
    def verify_azure_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Azure AD JWT token and extract user information.
        
        :param token: Azure AD JWT token.
        :return: User information dict if valid, None otherwise.
        """
        if not self.enabled:
            return None
            
        try:
            print(f"token: {token}")
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            if not kid:
                return None
            
            # Get public keys
            public_keys = self._get_public_keys()
            
            if kid not in public_keys:
                return None
            
            # Verify and decode token
            public_key = public_keys[kid]
            
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            )
            
            # Extract user information
            user_info = {
                "azure_object_id": payload.get("oid"),
                "email": payload.get("email") or payload.get("preferred_username"),
                "name": payload.get("name"),
                "given_name": payload.get("given_name"),
                "family_name": payload.get("family_name"),
                "tenant_id": payload.get("tid"),
                "upn": payload.get("upn"),
                "roles": payload.get("roles", []),
                "groups": payload.get("groups", []),
                "exp": payload.get("exp"),
                "iat": payload.get("iat")
            }
            
            return user_info
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            print(f"Error verifying Azure AD token: {e}")
            return None
    
    def get_user_info_from_graph(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get additional user information from Microsoft Graph API.
        
        :param access_token: Azure AD access token with User.Read scope.
        :return: Extended user information.
        """
        if not self.enabled:
            return None
            
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Get user profile
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get user info from Graph API: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error getting user info from Graph API: {e}")
            return None
    
    def get_user_groups_from_graph(self, access_token: str) -> list:
        """
        Get user's group memberships from Microsoft Graph API.
        
        :param access_token: Azure AD access token with GroupMember.Read.All scope.
        :return: List of group information.
        """
        if not self.enabled:
            return []
            
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Get user's groups
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me/memberOf",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                groups = []
                for group in data.get("value", []):
                    if group.get("@odata.type") == "#microsoft.graph.group":
                        groups.append({
                            "id": group.get("id"),
                            "displayName": group.get("displayName"),
                            "mail": group.get("mail")
                        })
                return groups
            else:
                print(f"Failed to get user groups from Graph API: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error getting user groups from Graph API: {e}")
            return []

# Global instance
azure_auth = AzureADAuth()
