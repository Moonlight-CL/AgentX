"""
Unit tests for app/config/pg_config_service.py — PGConfigService.

All tests patch 'app.config.pg_config_service.get_pg_connection' so that no
real database is required.
"""
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from app.config.pg_config_service import PGConfigService  # type: ignore
from app.config.models import (  # type: ignore
    SystemConfig, ConfigCategory, CreateConfigRequest, UpdateConfigRequest,
)

# ---------------------------------------------------------------------------
# Column layout
# ---------------------------------------------------------------------------

CONFIG_COLUMNS = [
    'key', 'value', 'key_display_name', 'type', 'parent',
    'seq_num', 'created_at', 'updated_at',
]

CONFIG_DESCRIPTION = [(col,) for col in CONFIG_COLUMNS]


def _config_row(**overrides):
    defaults = {
        'key': 'k1', 'value': '{}', 'key_display_name': 'K1',
        'type': 'item', 'parent': None, 'seq_num': 0,
        'created_at': '2024-01-01', 'updated_at': '2024-01-01',
    }
    defaults.update(overrides)
    return defaults


def _config_tuple(d):
    return tuple(d[c] for c in CONFIG_COLUMNS)


# ---------------------------------------------------------------------------
# Context-manager helpers
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, fetchone_val=None, fetchall_val=None):
        self.execute = MagicMock()
        self._fetchone_val = fetchone_val
        self._fetchall_val = fetchall_val or []
        self.description = list(CONFIG_DESCRIPTION)

    def fetchone(self):
        return self._fetchone_val

    def fetchall(self):
        return self._fetchall_val

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass


def _pg(cursor):
    @contextmanager
    def _cm():
        yield _FakeConn(cursor)
    return _cm


PATCH_TARGET = 'app.config.pg_config_service.get_pg_connection'


# ===========================================================================
# create_config
# ===========================================================================

def test_create_config_returns_system_config():
    cur = _FakeCursor()
    req = CreateConfigRequest(key='k1', value='{}', type='item')
    with patch(PATCH_TARGET, _pg(cur)):
        config = PGConfigService().create_config(req)
    assert isinstance(config, SystemConfig)
    assert config.key == 'k1'
    assert config.value == '{}'


def test_create_config_executes_insert_with_correct_table():
    cur = _FakeCursor()
    req = CreateConfigRequest(key='k1', value='{}', type='item')
    with patch(PATCH_TARGET, _pg(cur)):
        PGConfigService().create_config(req)
    cur.execute.assert_called_once()
    sql = cur.execute.call_args[0][0]
    assert 'configurations' in sql.lower()
    assert 'INSERT' in sql.upper()


# ===========================================================================
# get_config
# ===========================================================================

def test_get_config_found():
    row = _config_tuple(_config_row())
    cur = _FakeCursor(fetchone_val=row)
    with patch(PATCH_TARGET, _pg(cur)):
        config = PGConfigService().get_config('k1')
    assert config is not None
    assert config.key == 'k1'


def test_get_config_not_found():
    cur = _FakeCursor(fetchone_val=None)
    with patch(PATCH_TARGET, _pg(cur)):
        config = PGConfigService().get_config('missing')
    assert config is None


def test_get_config_exception_returns_none():
    @contextmanager
    def _boom():
        raise RuntimeError('db error')
        yield  # noqa

    with patch(PATCH_TARGET, _boom):
        config = PGConfigService().get_config('k1')
    assert config is None


# ===========================================================================
# update_config
# ===========================================================================

def test_update_config_found():
    existing_row = _config_tuple(_config_row())
    update_cur = _FakeCursor()
    call_idx = [0]

    @contextmanager
    def _ctx():
        if call_idx[0] == 0:
            # get_config query
            cur = _FakeCursor(fetchone_val=existing_row)
        else:
            # UPDATE query
            cur = _FakeCursor()
        call_idx[0] += 1
        yield _FakeConn(cur)

    req = UpdateConfigRequest(value='new_val')
    with patch(PATCH_TARGET, _ctx):
        config = PGConfigService().update_config('k1', req)
    assert config is not None
    assert config.value == 'new_val'


def test_update_config_not_found():
    cur = _FakeCursor(fetchone_val=None)
    req = UpdateConfigRequest(value='new_val')
    with patch(PATCH_TARGET, _pg(cur)):
        config = PGConfigService().update_config('missing', req)
    assert config is None


def test_update_config_exception_returns_none():
    @contextmanager
    def _boom():
        raise RuntimeError('db error')
        yield  # noqa

    req = UpdateConfigRequest(value='new_val')
    with patch(PATCH_TARGET, _boom):
        config = PGConfigService().update_config('k1', req)
    assert config is None


# ===========================================================================
# delete_config
# ===========================================================================

def test_delete_config_success():
    cur = _FakeCursor()
    with patch(PATCH_TARGET, _pg(cur)):
        result = PGConfigService().delete_config('k1')
    assert result is True


def test_delete_config_error():
    @contextmanager
    def _boom():
        raise RuntimeError('db error')
        yield  # noqa

    with patch(PATCH_TARGET, _boom):
        result = PGConfigService().delete_config('k1')
    assert result is False


# ===========================================================================
# list_configs_by_parent
# ===========================================================================

def test_list_configs_by_parent():
    rows = [
        _config_tuple(_config_row(key='c1', parent='root')),
        _config_tuple(_config_row(key='c2', parent='root')),
    ]
    cur = _FakeCursor(fetchall_val=rows)
    with patch(PATCH_TARGET, _pg(cur)):
        configs = PGConfigService().list_configs_by_parent('root')
    assert len(configs) == 2
    assert {c.key for c in configs} == {'c1', 'c2'}


def test_list_configs_by_parent_empty():
    cur = _FakeCursor(fetchall_val=[])
    with patch(PATCH_TARGET, _pg(cur)):
        configs = PGConfigService().list_configs_by_parent('root')
    assert configs == []


def test_list_configs_by_parent_exception():
    @contextmanager
    def _boom():
        raise RuntimeError('db error')
        yield  # noqa

    with patch(PATCH_TARGET, _boom):
        configs = PGConfigService().list_configs_by_parent('root')
    assert configs == []


# ===========================================================================
# list_all_configs
# ===========================================================================

def test_list_all_configs():
    rows = [
        _config_tuple(_config_row(key='a', type='category')),
        _config_tuple(_config_row(key='b', type='item', parent='a')),
    ]
    cur = _FakeCursor(fetchall_val=rows)
    with patch(PATCH_TARGET, _pg(cur)):
        configs = PGConfigService().list_all_configs()
    assert len(configs) == 2
    assert {c.key for c in configs} == {'a', 'b'}


def test_list_all_configs_exception():
    @contextmanager
    def _boom():
        raise RuntimeError('db error')
        yield  # noqa

    with patch(PATCH_TARGET, _boom):
        configs = PGConfigService().list_all_configs()
    assert configs == []


# ===========================================================================
# get_category_tree
# ===========================================================================

def test_get_category_tree_builds_hierarchy():
    """One root category, one child category under it, one item in root category."""
    rows = [
        _config_tuple(_config_row(key='root', type='category', parent=None)),
        _config_tuple(_config_row(key='child', type='category', parent='root')),
        _config_tuple(_config_row(key='item1', type='item', parent='root')),
    ]
    cur = _FakeCursor(fetchall_val=rows)
    with patch(PATCH_TARGET, _pg(cur)):
        tree = PGConfigService().get_category_tree()

    assert len(tree) == 1
    root = tree[0]
    assert root.key == 'root'
    assert len(root.children) == 1
    assert root.children[0].key == 'child'
    assert len(root.configs) == 1
    assert root.configs[0].key == 'item1'


def test_get_category_tree_empty():
    cur = _FakeCursor(fetchall_val=[])
    with patch(PATCH_TARGET, _pg(cur)):
        tree = PGConfigService().get_category_tree()
    assert tree == []


# ===========================================================================
# get_root_categories
# ===========================================================================

def test_get_root_categories():
    rows = [
        _config_tuple(_config_row(key='cat1', type='category', parent=None)),
        _config_tuple(_config_row(key='cat2', type='category', parent=None)),
    ]
    cur = _FakeCursor(fetchall_val=rows)
    with patch(PATCH_TARGET, _pg(cur)):
        cats = PGConfigService().get_root_categories()
    assert len(cats) == 2
    assert {c.key for c in cats} == {'cat1', 'cat2'}


def test_get_root_categories_exception():
    @contextmanager
    def _boom():
        raise RuntimeError('db error')
        yield  # noqa

    with patch(PATCH_TARGET, _boom):
        cats = PGConfigService().get_root_categories()
    assert cats == []
