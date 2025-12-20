#!/usr/bin/env python3
"""
Script to generate a secure API key for service-to-service authentication.
This key should be stored securely in environment variables or AWS Secrets Manager.
"""

import secrets
import string

def generate_api_key(length: int = 64) -> str:
    """
    Generate a cryptographically secure random API key.
    
    Args:
        length: Length of the API key (default: 64 characters)
    
    Returns:
        A secure random API key string
    """
    # Use alphanumeric characters and some special characters
    alphabet = string.ascii_letters + string.digits + '-_'
    api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return api_key

def main():
    """Generate and display a new API key."""
    print("=" * 80)
    print("Service API Key Generator")
    print("=" * 80)
    print()
    
    # Generate API key
    api_key = generate_api_key()
    
    print("Generated API Key:")
    print("-" * 80)
    print(api_key)
    print("-" * 80)
    print()
    
    print("Configuration Instructions:")
    print("-" * 80)
    print("1. Backend (FastAPI):")
    print("   Set environment variable: SERVICE_API_KEY=" + api_key)
    print()
    print("2. Lambda Function:")
    print("   Set environment variable: SERVICE_API_KEY=" + api_key)
    print()
    print("3. For production, store in AWS Secrets Manager:")
    print("   aws secretsmanager create-secret \\")
    print("       --name agentx/service-api-key \\")
    print(f"       --secret-string '{api_key}'")
    print()
    print("4. Update Lambda to retrieve from Secrets Manager:")
    print("   Add IAM permission: secretsmanager:GetSecretValue")
    print("   Retrieve in Lambda code using AWS SDK")
    print("-" * 80)
    print()
    
    print("Security Notes:")
    print("-" * 80)
    print("- Store this key securely and never commit it to version control")
    print("- Rotate the key periodically (recommended: every 90 days)")
    print("- Use different keys for different environments (dev, staging, prod)")
    print("- Monitor API key usage for suspicious activity")
    print("-" * 80)

if __name__ == "__main__":
    main()
