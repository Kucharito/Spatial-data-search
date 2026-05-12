import os
from contextlib import contextmanager

from dotenv import load_dotenv
from psycopg import connect
from psycopg.rows import dict_row

load_dotenv()


def get_database_url() -> str:
    # Read database connection URL from environment.
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Environment variable DATABASE_URL is not set.")
    return database_url


@contextmanager
def get_connection():
    # Yield a PostgreSQL connection with dict-style rows.
    connection = connect(get_database_url(), row_factory=dict_row)
    try:
        yield connection
    finally:
        connection.close()
