"""
Unit tests for app/utils/pg_config.py.

Tests cover:
  - init_pg_pool() success and missing DATABASE_URL
  - close_pg_pool() with and without an active pool
  - get_pg_connection() happy path (commit + putconn)
  - get_pg_connection() error path (rollback + putconn + re-raise)
"""
import os
import pytest
from unittest.mock import MagicMock, patch, call
from contextlib import contextmanager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_pool_state():
    """Reset the module-level _pool back to None between tests."""
    import app.utils.pg_config as pg  # type: ignore
    pg._pool = None


# ---------------------------------------------------------------------------
# init_pg_pool
# ---------------------------------------------------------------------------

def test_init_pg_pool_creates_pool():
    _reset_pool_state()
    import app.utils.pg_config as pg  # type: ignore

    mock_pool = MagicMock()
    with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://localhost/test'}), \
         patch('app.utils.pg_config.pool') as mock_pool_module:
        mock_pool_module.ThreadedConnectionPool.return_value = mock_pool
        pg.init_pg_pool()

        mock_pool_module.ThreadedConnectionPool.assert_called_once_with(
            minconn=2,
            maxconn=10,
            dsn='postgresql://localhost/test',
        )
        assert pg._pool is mock_pool


def test_init_pg_pool_raises_when_no_database_url():
    _reset_pool_state()
    import app.utils.pg_config as pg  # type: ignore

    env_without_db_url = {k: v for k, v in os.environ.items() if k != 'DATABASE_URL'}
    with patch.dict(os.environ, env_without_db_url, clear=True):
        with pytest.raises(KeyError):
            pg.init_pg_pool()


# ---------------------------------------------------------------------------
# close_pg_pool
# ---------------------------------------------------------------------------

def test_close_pg_pool_calls_closeall():
    import app.utils.pg_config as pg  # type: ignore

    mock_pool = MagicMock()
    pg._pool = mock_pool
    pg.close_pg_pool()

    mock_pool.closeall.assert_called_once()
    assert pg._pool is None


def test_close_pg_pool_when_pool_is_none_is_noop():
    import app.utils.pg_config as pg  # type: ignore

    pg._pool = None
    # Must not raise
    pg.close_pg_pool()
    assert pg._pool is None


# ---------------------------------------------------------------------------
# get_pg_connection — happy path
# ---------------------------------------------------------------------------

def test_get_pg_connection_happy_path():
    import app.utils.pg_config as pg  # type: ignore

    mock_conn = MagicMock()
    mock_pool = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    pg._pool = mock_pool

    with pg.get_pg_connection() as conn:
        assert conn is mock_conn

    mock_pool.getconn.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.rollback.assert_not_called()
    mock_pool.putconn.assert_called_once_with(mock_conn)


# ---------------------------------------------------------------------------
# get_pg_connection — error path
# ---------------------------------------------------------------------------

def test_get_pg_connection_rolls_back_on_exception():
    import app.utils.pg_config as pg  # type: ignore

    mock_conn = MagicMock()
    mock_pool = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    pg._pool = mock_pool

    with pytest.raises(RuntimeError, match='boom'):
        with pg.get_pg_connection() as conn:
            raise RuntimeError('boom')

    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()
    # putconn must still be called even after rollback
    mock_pool.putconn.assert_called_once_with(mock_conn)


def test_get_pg_connection_putconn_called_even_after_rollback():
    """Verify putconn is in the finally block, not only on success."""
    import app.utils.pg_config as pg  # type: ignore

    mock_conn = MagicMock()
    mock_pool = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    pg._pool = mock_pool

    class _SentinelError(Exception):
        pass

    with pytest.raises(_SentinelError):
        with pg.get_pg_connection():
            raise _SentinelError('test error')

    assert mock_pool.putconn.call_count == 1


# ---------------------------------------------------------------------------
# get_pg_connection — yields the connection from the pool
# ---------------------------------------------------------------------------

def test_get_pg_connection_yields_correct_connection():
    import app.utils.pg_config as pg  # type: ignore

    conn_a = MagicMock(name='conn_a')
    conn_b = MagicMock(name='conn_b')
    mock_pool = MagicMock()
    mock_pool.getconn.side_effect = [conn_a, conn_b]
    pg._pool = mock_pool

    with pg.get_pg_connection() as c1:
        pass
    with pg.get_pg_connection() as c2:
        pass

    assert c1 is conn_a
    assert c2 is conn_b
    assert mock_pool.putconn.call_args_list == [call(conn_a), call(conn_b)]
