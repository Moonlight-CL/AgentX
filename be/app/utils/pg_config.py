import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager

_pool = None


def init_pg_pool():
    global _pool
    database_url = os.environ["DATABASE_URL"]
    _pool = pool.ThreadedConnectionPool(minconn=2, maxconn=10, dsn=database_url)


def close_pg_pool():
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None


@contextmanager
def get_pg_connection():
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)
