"""
Integration tests for PGConfigService against a real PostgreSQL database.

Each test runs inside a transaction that is rolled back on completion, so the
database is left clean after the suite.

Run with:
    INTEGRATION_DATABASE_URL=postgresql://... uv run --no-sync pytest tests/integration/ -v -m integration
"""
import uuid

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _key(prefix: str = 'cfg') -> str:
    """Return a unique config key."""
    return f"{prefix}.{uuid.uuid4().hex[:10]}"


def _make_create_request(**overrides):
    """Return a CreateConfigRequest with sensible defaults."""
    from app.config.models import CreateConfigRequest

    defaults = dict(
        key=_key(),
        value='test_value',
        key_display_name='Test Config',
        type='item',
        seq_num=0,
    )
    defaults.update(overrides)
    return CreateConfigRequest(**defaults)


# ---------------------------------------------------------------------------
# create_config / get_config
# ---------------------------------------------------------------------------

def test_create_and_get_config(config_service):
    req = _make_create_request(value='hello', key_display_name='My Config')
    created = config_service.create_config(req)

    assert created.key == req.key
    assert created.value == 'hello'
    assert created.key_display_name == 'My Config'

    fetched = config_service.get_config(created.key)
    assert fetched is not None
    assert fetched.key == created.key
    assert fetched.value == 'hello'


def test_get_config_not_found(config_service):
    result = config_service.get_config('nonexistent.' + uuid.uuid4().hex)
    assert result is None


# ---------------------------------------------------------------------------
# update_config
# ---------------------------------------------------------------------------

def test_update_config(config_service):
    from app.config.models import UpdateConfigRequest

    req = _make_create_request(value='original')
    created = config_service.create_config(req)

    updated = config_service.update_config(created.key, UpdateConfigRequest(value='updated'))
    assert updated is not None
    assert updated.value == 'updated'

    fetched = config_service.get_config(created.key)
    assert fetched.value == 'updated'


def test_update_config_not_found(config_service):
    from app.config.models import UpdateConfigRequest

    result = config_service.update_config('nonexistent.' + uuid.uuid4().hex, UpdateConfigRequest(value='x'))
    assert result is None


# ---------------------------------------------------------------------------
# delete_config
# ---------------------------------------------------------------------------

def test_delete_config(config_service):
    req = _make_create_request()
    created = config_service.create_config(req)

    result = config_service.delete_config(created.key)
    assert result is True

    assert config_service.get_config(created.key) is None


# ---------------------------------------------------------------------------
# list_configs_by_parent
# ---------------------------------------------------------------------------

def test_list_configs_by_parent(config_service):
    parent_key = _key('parent')
    # Create parent category
    config_service.create_config(
        _make_create_request(key=parent_key, type='category', value='{}')
    )

    # Create two child items under this parent
    child1 = _make_create_request(parent=parent_key, seq_num=1, value='v1')
    child2 = _make_create_request(parent=parent_key, seq_num=2, value='v2')
    config_service.create_config(child1)
    config_service.create_config(child2)

    # Create an item under a different parent (should not appear)
    other_parent = _key('other')
    config_service.create_config(_make_create_request(key=other_parent, type='category', value='{}'))
    config_service.create_config(_make_create_request(parent=other_parent, value='other'))

    children = config_service.list_configs_by_parent(parent_key)
    child_keys = {c.key for c in children}
    assert child1.key in child_keys
    assert child2.key in child_keys


# ---------------------------------------------------------------------------
# list_all_configs
# ---------------------------------------------------------------------------

def test_list_all_configs(config_service):
    keys = [_key() for _ in range(3)]
    for k in keys:
        config_service.create_config(_make_create_request(key=k, value='v'))

    all_configs = config_service.list_all_configs()
    fetched_keys = {c.key for c in all_configs}
    for k in keys:
        assert k in fetched_keys


# ---------------------------------------------------------------------------
# get_root_categories
# ---------------------------------------------------------------------------

def test_get_root_categories(config_service):
    root_key = _key('rootcat')
    config_service.create_config(
        _make_create_request(key=root_key, type='category', parent=None, value='{}')
    )

    # Child category (has a parent, should not appear in root categories)
    child_cat_key = _key('childcat')
    config_service.create_config(
        _make_create_request(key=child_cat_key, type='category', parent=root_key, value='{}')
    )

    root_cats = config_service.get_root_categories()
    root_cat_keys = {c.key for c in root_cats}
    assert root_key in root_cat_keys
    # child category should NOT appear as a root category
    assert child_cat_key not in root_cat_keys


# ---------------------------------------------------------------------------
# get_category_tree
# ---------------------------------------------------------------------------

def test_get_category_tree_basic(config_service):
    """Create a root category, a child category, and an item; verify tree."""
    root_key = _key('rootcat')
    child_key = _key('childcat')
    item_key = _key('itemkey')

    config_service.create_config(
        _make_create_request(key=root_key, type='category', parent=None, value='{}')
    )
    config_service.create_config(
        _make_create_request(key=child_key, type='category', parent=root_key, value='{}')
    )
    config_service.create_config(
        _make_create_request(key=item_key, type='item', parent=child_key, value='item_value')
    )

    tree = config_service.get_category_tree()
    assert isinstance(tree, list)

    # Find our root category in the tree
    root_nodes = [node for node in tree if node.key == root_key]
    assert len(root_nodes) == 1, f"Expected root category '{root_key}' in tree, got keys: {[n.key for n in tree]}"

    root_node = root_nodes[0]
    assert len(root_node.children) >= 1
    child_node = next((c for c in root_node.children if c.key == child_key), None)
    assert child_node is not None, f"Child category '{child_key}' not found under root"

    item_nodes = [cfg for cfg in child_node.configs if cfg.key == item_key]
    assert len(item_nodes) == 1
    assert item_nodes[0].value == 'item_value'
