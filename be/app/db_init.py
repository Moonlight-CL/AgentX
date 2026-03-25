import os
from .utils.pg_config import get_pg_connection


def init_pg_schema():
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'schema.sql')
    with open(schema_path) as f:
        sql = f.read()
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
