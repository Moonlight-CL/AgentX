import uuid
import hashlib
import secrets
from datetime import datetime
from typing import Optional, List

from .models import User, UserCreate, UserUpdate, UserStatus, AuthProvider
from ..utils.pg_config import get_pg_connection


class PGUserService:
    """PostgreSQL implementation of UserService."""

    def _generate_salt(self) -> str:
        return secrets.token_hex(32)

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()

    def create_user(self, user_data: UserCreate) -> User:
        if self.get_user_by_username(user_data.username):
            raise ValueError(f"Username '{user_data.username}' already exists")

        salt = self._generate_salt()
        password_hash = self._hash_password(user_data.password, salt)
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
            updated_at=current_time,
        )

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (user_id, username, email, password_hash, salt, status,
                                       is_admin, user_groups, created_at, updated_at, auth_provider)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                    """,
                    (
                        user.user_id, user.username, user.email,
                        user.password_hash, user.salt, user.status.value,
                        user.is_admin,
                        '[]',
                        user.created_at, user.updated_at,
                        user.auth_provider.value,
                    ),
                )
        return user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                row = cur.fetchone()
                if row:
                    return self._row_to_user(cur, row)
        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                row = cur.fetchone()
                if row:
                    return self._row_to_user(cur, row)
        return None

    def get_user_by_azure_object_id(self, azure_object_id: str) -> Optional[User]:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE azure_object_id = %s", (azure_object_id,))
                row = cur.fetchone()
                if row:
                    return self._row_to_user(cur, row)
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                row = cur.fetchone()
                if row:
                    return self._row_to_user(cur, row)
        return None

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = self.get_user_by_username(username)
        if not user or user.status != UserStatus.ACTIVE:
            return None
        password_hash = self._hash_password(password, user.salt)
        if password_hash == user.password_hash:
            self.update_last_login(user.user_id)
            return user
        return None

    def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        fields = ['updated_at = %s']
        values = [datetime.now().isoformat()]

        if user_data.email is not None:
            fields.append('email = %s')
            values.append(user_data.email)
        if user_data.status is not None:
            fields.append('status = %s')
            values.append(user_data.status.value)
        if user_data.is_admin is not None:
            fields.append('is_admin = %s')
            values.append(user_data.is_admin)
        if user_data.user_groups is not None:
            import json
            fields.append('user_groups = %s::jsonb')
            values.append(json.dumps(user_data.user_groups))

        values.append(user_id)
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s",
                    values,
                )
        return self.get_user_by_id(user_id)

    def update_last_login(self, user_id: str) -> bool:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET last_login = %s WHERE user_id = %s",
                        (datetime.now().isoformat(), user_id),
                    )
            return True
        except Exception as e:
            print(f"Error updating last login for user {user_id}: {e}")
            return False

    def delete_user(self, user_id: str) -> bool:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            return True
        except Exception as e:
            print(f"Error deleting user {user_id}: {e}")
            return False

    def list_users(self, limit: int = 100) -> List[User]:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users LIMIT %s", (limit,))
                rows = cur.fetchall()
                return [self._row_to_user(cur, row) for row in rows]

    def create_azure_user(self, azure_user_info: dict) -> User:
        azure_object_id = azure_user_info.get("azure_object_id")
        email = azure_user_info.get("email")

        if not azure_object_id:
            raise ValueError("Azure object ID is required")

        existing_user = self.get_user_by_azure_object_id(azure_object_id)
        if existing_user:
            return self.update_azure_user(existing_user.user_id, azure_user_info)

        username = email.split('@')[0] if email else f"azure_{azure_object_id[:8]}"
        counter = 1
        original_username = username
        while self.get_user_by_username(username):
            username = f"{original_username}_{counter}"
            counter += 1

        user_id = uuid.uuid4().hex
        current_time = datetime.now().isoformat()

        user = User(
            user_id=user_id,
            username=username,
            email=email,
            status=UserStatus.ACTIVE,
            auth_provider=AuthProvider.AZURE_AD,
            azure_object_id=azure_object_id,
            azure_tenant_id=azure_user_info.get("tenant_id"),
            display_name=azure_user_info.get("name"),
            given_name=azure_user_info.get("given_name"),
            family_name=azure_user_info.get("family_name"),
            created_at=current_time,
            updated_at=current_time,
        )

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (user_id, username, email, status, is_admin, auth_provider,
                                       azure_object_id, azure_tenant_id, display_name, given_name,
                                       family_name, created_at, updated_at, user_groups)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        user.user_id, user.username, user.email,
                        user.status.value, user.is_admin, user.auth_provider.value,
                        user.azure_object_id, user.azure_tenant_id,
                        user.display_name, user.given_name, user.family_name,
                        user.created_at, user.updated_at, '[]',
                    ),
                )
        return user

    def update_azure_user(self, user_id: str, azure_user_info: dict) -> User:
        fields = ['updated_at = %s']
        values = [datetime.now().isoformat()]

        if azure_user_info.get("email"):
            fields.append('email = %s')
            values.append(azure_user_info["email"])
        if azure_user_info.get("name"):
            fields.append('display_name = %s')
            values.append(azure_user_info["name"])
        if azure_user_info.get("given_name"):
            fields.append('given_name = %s')
            values.append(azure_user_info["given_name"])
        if azure_user_info.get("family_name"):
            fields.append('family_name = %s')
            values.append(azure_user_info["family_name"])

        values.append(user_id)
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s",
                    values,
                )
        return self.get_user_by_id(user_id)

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        if user.auth_provider != AuthProvider.LOCAL or not user.password_hash or not user.salt:
            return False
        old_hash = self._hash_password(old_password, user.salt)
        if old_hash != user.password_hash:
            return False

        new_salt = self._generate_salt()
        new_hash = self._hash_password(new_password, new_salt)
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET password_hash = %s, salt = %s, updated_at = %s WHERE user_id = %s",
                        (new_hash, new_salt, datetime.now().isoformat(), user_id),
                    )
            return True
        except Exception as e:
            print(f"Error changing password for user {user_id}: {e}")
            return False

    def _row_to_user(self, cur, row) -> User:
        import json
        col_names = [desc[0] for desc in cur.description]
        item = dict(zip(col_names, row))
        user_groups = item.get('user_groups')
        if isinstance(user_groups, str):
            user_groups = json.loads(user_groups)
        return User(
            user_id=item['user_id'],
            username=item['username'],
            email=item.get('email'),
            password_hash=item.get('password_hash'),
            salt=item.get('salt'),
            status=UserStatus(item.get('status', 'active')),
            is_admin=item.get('is_admin', False),
            user_groups=user_groups,
            created_at=item['created_at'],
            updated_at=item['updated_at'],
            last_login=item.get('last_login'),
            auth_provider=AuthProvider(item.get('auth_provider', 'local')),
            azure_object_id=item.get('azure_object_id'),
            azure_tenant_id=item.get('azure_tenant_id'),
            display_name=item.get('display_name'),
            given_name=item.get('given_name'),
            family_name=item.get('family_name'),
        )
