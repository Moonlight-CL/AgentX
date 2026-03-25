"""
Integration tests for PGUserService against a real PostgreSQL database.

Each test runs inside a transaction that is rolled back on completion, so the
database is left clean after the suite.

Run with:
    INTEGRATION_DATABASE_URL=postgresql://... uv run --no-sync pytest tests/integration/ -v -m integration
"""
import uuid

import pytest

pytestmark = pytest.mark.integration


def _uid(prefix: str = 'user') -> str:
    """Return a unique string suitable for use as a username / identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------------------------
# create_user / get_user_by_id
# ---------------------------------------------------------------------------

def test_create_and_get_user_by_id(user_service):
    from app.user.models import UserCreate, UserStatus, AuthProvider

    username = _uid()
    user_data = UserCreate(username=username, email=f"{username}@example.com", password='S3cur3!')
    created = user_service.create_user(user_data)

    assert created.user_id
    assert created.username == username
    assert created.email == f"{username}@example.com"
    assert created.status == UserStatus.ACTIVE
    assert created.auth_provider == AuthProvider.LOCAL
    assert created.password_hash
    assert created.salt

    fetched = user_service.get_user_by_id(created.user_id)
    assert fetched is not None
    assert fetched.user_id == created.user_id
    assert fetched.username == username


def test_create_user_duplicate_raises_value_error(user_service):
    from app.user.models import UserCreate

    username = _uid()
    user_data = UserCreate(username=username, email=f"{username}@test.com", password='pass1')
    user_service.create_user(user_data)

    with pytest.raises(ValueError, match="already exists"):
        user_service.create_user(user_data)


# ---------------------------------------------------------------------------
# get_user_by_username
# ---------------------------------------------------------------------------

def test_get_user_by_username(user_service):
    from app.user.models import UserCreate

    username = _uid()
    user_service.create_user(UserCreate(username=username, password='pass'))

    result = user_service.get_user_by_username(username)
    assert result is not None
    assert result.username == username


def test_get_user_by_id_not_found(user_service):
    result = user_service.get_user_by_id('nonexistent_' + uuid.uuid4().hex)
    assert result is None


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------

def test_authenticate_user_success(user_service):
    from app.user.models import UserCreate

    username = _uid()
    password = 'MySecret123'
    user_service.create_user(UserCreate(username=username, password=password))

    result = user_service.authenticate_user(username, password)
    assert result is not None
    assert result.username == username


def test_authenticate_user_wrong_password(user_service):
    from app.user.models import UserCreate

    username = _uid()
    user_service.create_user(UserCreate(username=username, password='correct_pw'))

    result = user_service.authenticate_user(username, 'wrong_pw')
    assert result is None


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------

def test_update_user_email(user_service):
    from app.user.models import UserCreate, UserUpdate

    username = _uid()
    created = user_service.create_user(UserCreate(username=username, password='pw'))

    new_email = f"new_{username}@example.com"
    updated = user_service.update_user(created.user_id, UserUpdate(email=new_email))

    assert updated is not None
    assert updated.email == new_email


def test_update_user_not_found(user_service):
    from app.user.models import UserUpdate

    result = user_service.update_user('nonexistent_' + uuid.uuid4().hex, UserUpdate(email='x@x.com'))
    assert result is None


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------

def test_delete_user(user_service):
    from app.user.models import UserCreate

    username = _uid()
    created = user_service.create_user(UserCreate(username=username, password='pw'))

    user_service.delete_user(created.user_id)

    assert user_service.get_user_by_id(created.user_id) is None


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------

def test_list_users(user_service):
    from app.user.models import UserCreate

    usernames = [_uid() for _ in range(3)]
    for uname in usernames:
        user_service.create_user(UserCreate(username=uname, password='pw'))

    users = user_service.list_users()
    fetched_names = {u.username for u in users}
    for uname in usernames:
        assert uname in fetched_names


# ---------------------------------------------------------------------------
# create_azure_user / get_user_by_azure_object_id
# ---------------------------------------------------------------------------

def test_create_azure_user(user_service):
    azure_oid = uuid.uuid4().hex
    azure_info = {
        'azure_object_id': azure_oid,
        'email': f'azure_{azure_oid[:8]}@corp.com',
        'name': 'Test Azure User',
        'given_name': 'Test',
        'family_name': 'Azure',
        'tenant_id': 'tenant-123',
    }
    created = user_service.create_azure_user(azure_info)

    assert created.azure_object_id == azure_oid
    assert created.display_name == 'Test Azure User'

    fetched = user_service.get_user_by_azure_object_id(azure_oid)
    assert fetched is not None
    assert fetched.azure_object_id == azure_oid


# ---------------------------------------------------------------------------
# update_last_login
# ---------------------------------------------------------------------------

def test_update_last_login(user_service):
    from app.user.models import UserCreate

    username = _uid()
    created = user_service.create_user(UserCreate(username=username, password='pw'))

    # last_login is None right after creation
    fetched_before = user_service.get_user_by_id(created.user_id)
    assert fetched_before.last_login is None

    result = user_service.update_last_login(created.user_id)
    assert result is True

    fetched_after = user_service.get_user_by_id(created.user_id)
    assert fetched_after.last_login is not None


# ---------------------------------------------------------------------------
# change_password
# ---------------------------------------------------------------------------

def test_change_password(user_service):
    from app.user.models import UserCreate

    username = _uid()
    old_pw = 'OldPass1!'
    new_pw = 'NewPass2!'
    created = user_service.create_user(UserCreate(username=username, password=old_pw))

    result = user_service.change_password(created.user_id, old_pw, new_pw)
    assert result is True

    # Authenticate with the new password
    auth_result = user_service.authenticate_user(username, new_pw)
    assert auth_result is not None

    # Old password no longer works
    old_auth = user_service.authenticate_user(username, old_pw)
    assert old_auth is None


def test_change_password_wrong_old_password(user_service):
    from app.user.models import UserCreate

    username = _uid()
    correct_pw = 'CorrectPass!'
    created = user_service.create_user(UserCreate(username=username, password=correct_pw))

    result = user_service.change_password(created.user_id, 'WrongOld!', 'NewPass!')
    assert result is False

    # Original password still authenticates
    auth_result = user_service.authenticate_user(username, correct_pw)
    assert auth_result is not None
