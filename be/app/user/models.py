import boto3
import uuid
import hashlib
import secrets
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum
from ..utils.aws_config import get_aws_region

class UserStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class User(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    password_hash: str
    salt: str
    status: UserStatus = UserStatus.ACTIVE
    is_admin: bool = False
    user_groups: Optional[List[str]] = None  # List of user group IDs
    created_at: str
    updated_at: str
    last_login: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    status: Optional[UserStatus] = None
    is_admin: Optional[bool] = None
    user_groups: Optional[List[str]] = None

class TokenData(BaseModel):
    user_id: str
    username: str
    exp: datetime

class UserService:
    """
    A service to manage User objects in DynamoDB.
    """
    
    dynamodb_table_name = "UserTable"
    
    def __init__(self):
        aws_region = get_aws_region()
        self.dynamodb = boto3.resource('dynamodb', region_name=aws_region)
    
    def _generate_salt(self) -> str:
        """Generate a random salt for password hashing."""
        return secrets.token_hex(32)
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash a password with the given salt."""
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user in DynamoDB.
        
        :param user_data: The user creation data.
        :return: The created User object.
        :raises ValueError: If username already exists.
        """
        # Check if username already exists
        if self.get_user_by_username(user_data.username):
            raise ValueError(f"Username '{user_data.username}' already exists")
        
        # Generate salt and hash password
        salt = self._generate_salt()
        password_hash = self._hash_password(user_data.password, salt)
        
        # Create user object
        user_id = uuid.uuid4().hex
        current_time = datetime.now().isoformat()
        
        user = User(
            user_id=user_id,
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            salt=salt,
            status=UserStatus.ACTIVE,
            created_at=current_time,
            updated_at=current_time
        )
        
        # Save to DynamoDB
        table = self.dynamodb.Table(self.dynamodb_table_name)
        item = {
            'user_id': user.user_id,
            'username': user.username,
            'password_hash': user.password_hash,
            'salt': user.salt,
            'status': user.status.value,
            'is_admin': user.is_admin,
            'created_at': user.created_at,
            'updated_at': user.updated_at
        }
        
        if user.email:
            item['email'] = user.email
        
        if user.user_groups:
            item['user_groups'] = user.user_groups
        
        table.put_item(Item=item)
        
        return user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Retrieve a user by their ID.
        
        :param user_id: The user ID to search for.
        :return: User object if found, None otherwise.
        """
        table = self.dynamodb.Table(self.dynamodb_table_name)
        response = table.get_item(Key={'user_id': user_id})
        
        if 'Item' in response:
            return self._map_user_item(response['Item'])
        return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Retrieve a user by their username.
        
        :param username: The username to search for.
        :return: User object if found, None otherwise.
        """
        table = self.dynamodb.Table(self.dynamodb_table_name)
        
        # Use GSI to query by username
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('username').eq(username)
        )
        
        items = response.get('Items', [])
        if items:
            return self._map_user_item(items[0])
        return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password.
        
        :param username: The username.
        :param password: The plain text password.
        :return: User object if authentication successful, None otherwise.
        """
        user = self.get_user_by_username(username)
        if not user:
            return None
        
        # Check if user is active
        if user.status != UserStatus.ACTIVE:
            return None
        
        # Verify password
        password_hash = self._hash_password(password, user.salt)
        if password_hash == user.password_hash:
            # Update last login time
            self.update_last_login(user.user_id)
            return user
        
        return None
    
    def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """
        Update user information.
        
        :param user_id: The user ID to update.
        :param user_data: The update data.
        :return: Updated User object if successful, None otherwise.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        table = self.dynamodb.Table(self.dynamodb_table_name)
        update_expression = "SET updated_at = :updated_at"
        expression_values = {
            ':updated_at': datetime.now().isoformat()
        }
        
        if user_data.email is not None:
            update_expression += ", email = :email"
            expression_values[':email'] = user_data.email
        
        if user_data.status is not None:
            update_expression += ", #status = :status"
            expression_values[':status'] = user_data.status.value
        
        if user_data.is_admin is not None:
            update_expression += ", is_admin = :is_admin"
            expression_values[':is_admin'] = user_data.is_admin
        
        if user_data.user_groups is not None:
            update_expression += ", user_groups = :user_groups"
            expression_values[':user_groups'] = user_data.user_groups
        
        expression_names = {}
        if user_data.status is not None:
            expression_names['#status'] = 'status'
        
        kwargs = {
            'Key': {'user_id': user_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values,
            'ReturnValues': 'ALL_NEW'
        }
        
        if expression_names:
            kwargs['ExpressionAttributeNames'] = expression_names
        
        response = table.update_item(**kwargs)
        
        if 'Attributes' in response:
            return self._map_user_item(response['Attributes'])
        return None
    
    def update_last_login(self, user_id: str) -> bool:
        """
        Update the last login time for a user.
        
        :param user_id: The user ID.
        :return: True if successful, False otherwise.
        """
        table = self.dynamodb.Table(self.dynamodb_table_name)
        
        try:
            table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET last_login = :last_login',
                ExpressionAttributeValues={
                    ':last_login': datetime.now().isoformat()
                }
            )
            return True
        except Exception as e:
            print(f"Error updating last login for user {user_id}: {e}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user from DynamoDB.
        
        :param user_id: The user ID to delete.
        :return: True if deletion was successful, False otherwise.
        """
        table = self.dynamodb.Table(self.dynamodb_table_name)
        
        try:
            response = table.delete_item(Key={'user_id': user_id})
            return response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200
        except Exception as e:
            print(f"Error deleting user {user_id}: {e}")
            return False
    
    def list_users(self, limit: int = 100) -> List[User]:
        """
        List all users with pagination.
        
        :param limit: Maximum number of users to return.
        :return: List of User objects.
        """
        table = self.dynamodb.Table(self.dynamodb_table_name)
        response = table.scan(Limit=limit)
        
        items = response.get('Items', [])
        return [self._map_user_item(item) for item in items]
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """
        Change a user's password.
        
        :param user_id: The user ID.
        :param old_password: The current password.
        :param new_password: The new password.
        :return: True if successful, False otherwise.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Verify old password
        old_password_hash = self._hash_password(old_password, user.salt)
        if old_password_hash != user.password_hash:
            return False
        
        # Generate new salt and hash new password
        new_salt = self._generate_salt()
        new_password_hash = self._hash_password(new_password, new_salt)
        
        # Update in database
        table = self.dynamodb.Table(self.dynamodb_table_name)
        
        try:
            table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET password_hash = :password_hash, salt = :salt, updated_at = :updated_at',
                ExpressionAttributeValues={
                    ':password_hash': new_password_hash,
                    ':salt': new_salt,
                    ':updated_at': datetime.now().isoformat()
                }
            )
            return True
        except Exception as e:
            print(f"Error changing password for user {user_id}: {e}")
            return False
    
    def _map_user_item(self, item: dict) -> User:
        """
        Map a DynamoDB item to a User object.
        
        :param item: The DynamoDB item.
        :return: User object.
        """
        return User(
            user_id=item['user_id'],
            username=item['username'],
            email=item.get('email'),
            password_hash=item['password_hash'],
            salt=item['salt'],
            status=UserStatus(item['status']),
            is_admin=item.get('is_admin', False),
            user_groups=item.get('user_groups'),
            created_at=item['created_at'],
            updated_at=item['updated_at'],
            last_login=item.get('last_login')
        )
