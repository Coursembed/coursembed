from contextlib import contextmanager
from typing import Any, Generator
from psycopg2.extras import RealDictCursor, register_uuid
from psycopg2.pool import ThreadedConnectionPool

from utils.config import config


class DatabaseConnectionManager:
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnectionManager, cls).__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance
    
    def _initialize_pool(self) -> None:
        if self._pool is None:
            register_uuid()

            self._pool = ThreadedConnectionPool(
                minconn=config.postgres_db_min_connections,
                maxconn=config.postgres_db_max_connections,
                host=config.postgres_db_host,
                port=config.postgres_db_port,
                dbname=config.postgres_db_name,
                user=config.postgres_db_username,
                password=config.postgres_db_password
            )
    
    def get_pool(self) -> ThreadedConnectionPool:
        return self._pool
    
    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        finally:
            if conn:
                self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, cursor_factory=RealDictCursor) -> Generator[Any, None, None]:
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def close_pool(self) -> None:
        if self._pool:
            self._pool.closeall()
            self._pool = None


db_manager = DatabaseConnectionManager()

def get_connection_pool() -> ThreadedConnectionPool:
    return db_manager.get_pool()
