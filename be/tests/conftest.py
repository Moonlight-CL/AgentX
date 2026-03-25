"""
Shared test fixtures and helpers for the AgentX backend test suite.
"""
import pytest
from unittest.mock import MagicMock


class MockCursor:
    """A mock psycopg2 cursor that supports context manager protocol."""

    def __init__(self):
        self.execute = MagicMock()
        self.fetchone = MagicMock(return_value=None)
        self.fetchall = MagicMock(return_value=[])
        # description is a list of (col_name,) tuples, mirroring psycopg2
        self.description = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockConn:
    """A mock psycopg2 connection that supports context manager protocol."""

    def __init__(self):
        self._cursor = MockCursor()

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass


@pytest.fixture
def mock_cursor():
    """Return a fresh MockCursor instance."""
    return MockCursor()


@pytest.fixture
def mock_conn(mock_cursor):
    """Return a MockConn whose cursor is the shared mock_cursor fixture."""
    conn = MockConn()
    conn._cursor = mock_cursor
    return conn
