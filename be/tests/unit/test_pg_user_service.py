"""
Unit tests for app/user/pg_user_service.py — PGUserService.

All tests patch 'app.user.pg_user_service.get_pg_connection' so that no
real database is required.  The mock connection/cursor setup mirrors the
psycopg2 context-manager protocol:

    with get_pg_connection() as conn:   # outer CM
        with conn.cursor() as cur:       # inner CM
            cur.execute(...)
            row = cur.fetchone()

We use a contextmanager-based patch so that both 'with' levels work.
"""
import json
import hashlib
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, call

from app.user.pg_user_service import PGUserService  # type: ignore
from app.user.models import (  # type: ignore
    User, UserCreate, UserUpdate, UserStatus, AuthProvider,
)


# ---------------------------------------------------------------------------
# Column layout used by _row_to_user (must match SELECT * order in the DB)
# ---------------------------------------------------------------------------

COLUMNS = [
    'user_id', 'username', 'email', 'password_hash', 'salt', 'status',
    'is_admin', 'user_groups', 'created_at', 'updated_at', 'last_login',
    'auth_provider', 'azure_object_id', 'azure_tenant_id',
    'display_name', 'given_name', 'family_name',
]

DESCRIPTION = [(col,) for col in COLUMNS]


def _row(**overrides):
    """Return a tuple row in the same order as COLUMNS with sensible defaults."""
    defaults = {
        'user_id': 'uid1',
        'username': 'alice',
        'email': 'alice@test.com',
        'password_hash': 'deadbeef',
        'salt': 'saltsalt',
        'status': 'active',
        'is_admin': False,
        'user_groups': '[]',
        'created_at': '2024-01-01T00:00:00',
        'updated_at': '2024-01-01T00:00:00',
        'last_login': None,
        'auth_provider': 'local',
        'azure_object_id': None,
        'azure_tenant_id': None,
        'display_name': None,
        'given_name': None,
        'family_name': None,
    }
    defaults.update(overrides)
    return tuple(defaults[c] for c in COLUMNS)


# ---------------------------------------------------------------------------
# Context-manager helpers
# ---------------------------------------------------------------------------

class _FakeCursor:
    """Cursor that supports 'with conn.cursor() as cur:' protocol."""

    def __init__(self, fetchone_val=None, fetchall_val=None):
        self.execute = MagicMock()
        self.fetchone = MagicMock(return_value=fetchone_val)
        self.fetchall = MagicMock(return_value=fetchall_val or [])
        self.description = list(DESCRIPTION)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _FakeConn:
    """Connection whose .cursor() returns a _FakeCursor via context manager."""

    def __init__(self, cursor: _FakeCursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass


def _pg_ctx(cursor: _FakeCursor):
    """Return a context-manager factory that yields a _FakeConn."""
    @contextmanager
    def _cm():
        yield _FakeConn(cursor)
    return _cm


# ---------------------------------------------------------------------------
# Convenience: build a PGUserService with get_pg_connection pre-patched
# ---------------------------------------------------------------------------

def _service_with_cursor(cursor: _FakeCursor):
    """Create a PGUserService whose get_pg_connection uses *cursor*."""
    svc = PGUserService()
    svc._pg_ctx = _pg_ctx(cursor)  # store for multi-call tests
    return svc


PATCH_TARGET = 'app.user.pg_user_service.get_pg_connection'


# ---------------------------------------------------------------------------
# _row_to_user
# ---------------------------------------------------------------------------

def test_row_to_user_basic():
    svc = PGUserService()
    cur = _FakeCursor()
    row = _row()
    user = svc._row_to_user(cur, row)
    assert user.user_id == 'uid1'
    assert user.username == 'alice'
    assert user.email == 'alice@test.com'
    assert user.status == UserStatus.ACTIVE
    assert user.auth_provider == AuthProvider.LOCAL
    assert user.user_groups == []


def test_row_to_user_with_json_string_groups():
    svc = PGUserService()
    cur = _FakeCursor()
    row = _row(user_groups='["grp1","grp2"]')
    user = svc._row_to_user(cur, row)
    assert user.user_groups == ['grp1', 'grp2']


def test_row_to_user_with_list_groups():
    """user_groups may already be a list (psycopg2 JSON column auto-decode)."""
    svc = PGUserService()
    cur = _FakeCursor()
    row = _row(user_groups=['grp1', 'grp2'])
    user = svc._row_to_user(cur, row)
    assert user.user_groups == ['grp1', 'grp2']


def test_row_to_user_azure_fields():
    svc = PGUserService()
    cur = _FakeCursor()
    row = _row(
        auth_provider='azure_ad',
        azure_object_id='oid-123',
        azure_tenant_id='tid-456',
        display_name='Alice Smith',
        given_name='Alice',
        family_name='Smith',
    )
    user = svc._row_to_user(cur, row)
    assert user.auth_provider == AuthProvider.AZURE_AD
    assert user.azure_object_id == 'oid-123'
    assert user.display_name == 'Alice Smith'


# ---------------------------------------------------------------------------
# get_user_by_id
# ---------------------------------------------------------------------------

def test_get_user_by_id_found():
    cur = _FakeCursor(fetchone_val=_row())
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        user = PGUserService().get_user_by_id('uid1')
    assert user is not None
    assert user.user_id == 'uid1'
    cur.execute.assert_called_once()
    args = cur.execute.call_args[0]
    assert 'user_id' in args[0]
    assert args[1] == ('uid1',)


def test_get_user_by_id_not_found():
    cur = _FakeCursor(fetchone_val=None)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        user = PGUserService().get_user_by_id('nonexistent')
    assert user is None


# ---------------------------------------------------------------------------
# get_user_by_username
# ---------------------------------------------------------------------------

def test_get_user_by_username_found():
    cur = _FakeCursor(fetchone_val=_row())
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        user = PGUserService().get_user_by_username('alice')
    assert user is not None
    assert user.username == 'alice'


def test_get_user_by_username_not_found():
    cur = _FakeCursor(fetchone_val=None)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        user = PGUserService().get_user_by_username('nobody')
    assert user is None


# ---------------------------------------------------------------------------
# get_user_by_azure_object_id
# ---------------------------------------------------------------------------

def test_get_user_by_azure_object_id_found():
    cur = _FakeCursor(fetchone_val=_row(azure_object_id='oid-123'))
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        user = PGUserService().get_user_by_azure_object_id('oid-123')
    assert user is not None
    assert user.azure_object_id == 'oid-123'


def test_get_user_by_azure_object_id_not_found():
    cur = _FakeCursor(fetchone_val=None)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        user = PGUserService().get_user_by_azure_object_id('oid-none')
    assert user is None


# ---------------------------------------------------------------------------
# get_user_by_email
# ---------------------------------------------------------------------------

def test_get_user_by_email_found():
    cur = _FakeCursor(fetchone_val=_row(email='alice@test.com'))
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        user = PGUserService().get_user_by_email('alice@test.com')
    assert user is not None
    assert user.email == 'alice@test.com'


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

def test_create_user_success():
    """create_user first calls get_user_by_username (returns None) then INSERT."""
    cur = _FakeCursor(fetchone_val=None)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        svc = PGUserService()
        user = svc.create_user(UserCreate(username='bob', email='bob@test.com', password='pw'))
    assert user.username == 'bob'
    assert user.email == 'bob@test.com'
    assert user.password_hash is not None
    assert user.salt is not None
    # execute should have been called twice: SELECT then INSERT
    assert cur.execute.call_count == 2


def test_create_user_duplicate_username():
    """create_user raises ValueError when username already exists."""
    cur = _FakeCursor(fetchone_val=_row(username='alice'))
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        svc = PGUserService()
        with pytest.raises(ValueError, match="already exists"):
            svc.create_user(UserCreate(username='alice', password='pw'))


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------

def _make_user_with_password(password: str) -> tuple:
    """Return (row_tuple, salt, hash) for a user with the given password."""
    import secrets
    salt = secrets.token_hex(4)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256', password.encode(), salt.encode(), 100000
    ).hex()
    return _row(password_hash=pw_hash, salt=salt, status='active'), salt, pw_hash


def test_authenticate_user_success():
    row, salt, pw_hash = _make_user_with_password('correct-password')
    # get_user_by_username returns the row; update_last_login also needs a conn
    call_count = [0]

    @contextmanager
    def multi_call_ctx():
        cur = _FakeCursor(fetchone_val=row)
        yield _FakeConn(cur)
        call_count[0] += 1

    with patch(PATCH_TARGET, multi_call_ctx):
        svc = PGUserService()
        user = svc.authenticate_user('alice', 'correct-password')
    assert user is not None
    assert user.username == 'alice'


def test_authenticate_user_wrong_password():
    row, _, _ = _make_user_with_password('correct-password')
    cur = _FakeCursor(fetchone_val=row)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        svc = PGUserService()
        user = svc.authenticate_user('alice', 'wrong-password')
    assert user is None


def test_authenticate_user_inactive_user():
    row, salt, pw_hash = _make_user_with_password('pw')
    inactive_row = _row(password_hash=pw_hash, salt=salt, status='inactive')
    cur = _FakeCursor(fetchone_val=inactive_row)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        svc = PGUserService()
        user = svc.authenticate_user('alice', 'pw')
    assert user is None


def test_authenticate_user_not_found():
    cur = _FakeCursor(fetchone_val=None)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        svc = PGUserService()
        user = svc.authenticate_user('ghost', 'pw')
    assert user is None


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------

def test_update_user_found():
    """update_user should call get_user_by_id twice (before and after update)."""
    existing_row = _row(email='old@test.com')
    updated_row = _row(email='new@test.com')
    responses = [existing_row, None, updated_row]  # get_by_id, UPDATE, get_by_id
    idx = [0]

    @contextmanager
    def cycling_ctx():
        val = responses[idx[0]] if idx[0] < len(responses) else None
        cur = _FakeCursor(fetchone_val=val)
        idx[0] += 1
        yield _FakeConn(cur)

    with patch(PATCH_TARGET, cycling_ctx):
        svc = PGUserService()
        user = svc.update_user('uid1', UserUpdate(email='new@test.com'))
    assert user is not None


def test_update_user_not_found():
    cur = _FakeCursor(fetchone_val=None)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        svc = PGUserService()
        user = svc.update_user('nonexistent', UserUpdate(email='x@test.com'))
    assert user is None


# ---------------------------------------------------------------------------
# update_last_login
# ---------------------------------------------------------------------------

def test_update_last_login_success():
    cur = _FakeCursor()
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        result = PGUserService().update_last_login('uid1')
    assert result is True
    cur.execute.assert_called_once()


def test_update_last_login_error():
    @contextmanager
    def _boom():
        raise RuntimeError('db error')
        yield  # make it a generator

    with patch(PATCH_TARGET, _boom):
        result = PGUserService().update_last_login('uid1')
    assert result is False


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------

def test_delete_user_success():
    cur = _FakeCursor()
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        result = PGUserService().delete_user('uid1')
    assert result is True
    cur.execute.assert_called_once()


def test_delete_user_error():
    @contextmanager
    def _boom():
        raise RuntimeError('db error')
        yield

    with patch(PATCH_TARGET, _boom):
        result = PGUserService().delete_user('uid1')
    assert result is False


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------

def test_list_users():
    rows = [_row(user_id='u1', username='a'), _row(user_id='u2', username='b')]
    cur = _FakeCursor(fetchall_val=rows)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        users = PGUserService().list_users(limit=10)
    assert len(users) == 2
    assert {u.username for u in users} == {'a', 'b'}


def test_list_users_empty():
    cur = _FakeCursor(fetchall_val=[])
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        users = PGUserService().list_users()
    assert users == []


# ---------------------------------------------------------------------------
# create_azure_user
# ---------------------------------------------------------------------------

def test_create_azure_user_new():
    """No existing user → INSERT a new Azure user."""
    # get_user_by_azure_object_id → None; get_user_by_username → None; INSERT
    cur = _FakeCursor(fetchone_val=None)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        svc = PGUserService()
        user = svc.create_azure_user({
            'azure_object_id': 'oid-1',
            'email': 'azure@test.com',
            'name': 'Azure User',
            'given_name': 'Azure',
            'family_name': 'User',
            'tenant_id': 'tid-1',
        })
    assert user.azure_object_id == 'oid-1'
    assert user.auth_provider == AuthProvider.AZURE_AD


def test_create_azure_user_existing_calls_update():
    """Existing user → delegates to update_azure_user."""
    existing_row = _row(
        auth_provider='azure_ad',
        azure_object_id='oid-1',
        user_id='uid-existing',
    )
    updated_row = _row(
        auth_provider='azure_ad',
        azure_object_id='oid-1',
        user_id='uid-existing',
        display_name='New Name',
    )
    responses = [existing_row, None, updated_row]
    idx = [0]

    @contextmanager
    def cycling_ctx():
        val = responses[idx[0]] if idx[0] < len(responses) else None
        cur = _FakeCursor(fetchone_val=val)
        idx[0] += 1
        yield _FakeConn(cur)

    with patch(PATCH_TARGET, cycling_ctx):
        svc = PGUserService()
        user = svc.create_azure_user({
            'azure_object_id': 'oid-1',
            'email': 'azure@test.com',
            'name': 'New Name',
        })
    assert user is not None


def test_create_azure_user_missing_object_id():
    svc = PGUserService()
    with pytest.raises(ValueError, match='Azure object ID is required'):
        svc.create_azure_user({'email': 'x@test.com'})


# ---------------------------------------------------------------------------
# update_azure_user
# ---------------------------------------------------------------------------

def test_update_azure_user():
    """update_azure_user should UPDATE then return get_user_by_id result."""
    updated_row = _row(display_name='New Name')
    responses = [None, updated_row]  # UPDATE (no fetchone), then get_by_id
    idx = [0]

    @contextmanager
    def cycling_ctx():
        val = responses[idx[0]] if idx[0] < len(responses) else None
        cur = _FakeCursor(fetchone_val=val)
        idx[0] += 1
        yield _FakeConn(cur)

    with patch(PATCH_TARGET, cycling_ctx):
        svc = PGUserService()
        user = svc.update_azure_user('uid1', {'email': 'x@test.com', 'name': 'New Name'})
    assert user is not None
    assert user.display_name == 'New Name'


# ---------------------------------------------------------------------------
# change_password
# ---------------------------------------------------------------------------

def test_change_password_success():
    row, _, pw_hash = _make_user_with_password('oldpass')
    responses = [row, None]  # get_user_by_id, UPDATE
    idx = [0]

    @contextmanager
    def cycling_ctx():
        val = responses[idx[0]] if idx[0] < len(responses) else None
        cur = _FakeCursor(fetchone_val=val)
        idx[0] += 1
        yield _FakeConn(cur)

    with patch(PATCH_TARGET, cycling_ctx):
        result = PGUserService().change_password('uid1', 'oldpass', 'newpass')
    assert result is True


def test_change_password_wrong_old_password():
    row, _, _ = _make_user_with_password('correct')
    cur = _FakeCursor(fetchone_val=row)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        result = PGUserService().change_password('uid1', 'wrong', 'newpass')
    assert result is False


def test_change_password_user_not_found():
    cur = _FakeCursor(fetchone_val=None)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        result = PGUserService().change_password('ghost', 'old', 'new')
    assert result is False


def test_change_password_azure_user():
    """Azure AD users cannot change password via this method."""
    azure_row = _row(auth_provider='azure_ad', password_hash=None, salt=None)
    cur = _FakeCursor(fetchone_val=azure_row)
    with patch(PATCH_TARGET, _pg_ctx(cur)):
        result = PGUserService().change_password('uid1', 'old', 'new')
    assert result is False


def test_change_password_db_error():
    row, _, _ = _make_user_with_password('oldpass')
    call_idx = [0]

    @contextmanager
    def ctx():
        if call_idx[0] == 0:
            # First call: get_user_by_id succeeds
            cur = _FakeCursor(fetchone_val=row)
            call_idx[0] += 1
            yield _FakeConn(cur)
        else:
            # Second call: UPDATE raises
            raise RuntimeError('db error')
            yield  # pragma: no cover

    with patch(PATCH_TARGET, ctx):
        result = PGUserService().change_password('uid1', 'oldpass', 'newpass')
    assert result is False


# ---------------------------------------------------------------------------
# Password hashing helpers
# ---------------------------------------------------------------------------

def test_generate_salt_returns_hex_string():
    svc = PGUserService()
    salt = svc._generate_salt()
    assert isinstance(salt, str)
    assert len(salt) == 64  # 32 bytes → 64 hex chars


def test_hash_password_deterministic():
    svc = PGUserService()
    h1 = svc._hash_password('pw', 'salt')
    h2 = svc._hash_password('pw', 'salt')
    assert h1 == h2


def test_hash_password_different_salts():
    svc = PGUserService()
    h1 = svc._hash_password('pw', 'salt1')
    h2 = svc._hash_password('pw', 'salt2')
    assert h1 != h2
