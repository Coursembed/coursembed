import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

from psycopg2.extras import RealDictCursor, register_uuid
from psycopg2.pool import ThreadedConnectionPool


class WorkspaceRepository:
    def __init__(self, pool: ThreadedConnectionPool):
        self.pool = pool
        register_uuid()

    def _get_connection(self):
        return self.pool.getconn()

    def _return_connection(self, conn):
        self.pool.putconn(conn)

    def get_all(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, name, description, created_at, updated_at
                    FROM workspaces
                    WHERE deleted_at IS NULL
                    ORDER BY created_at DESC
                """
                )
                return cursor.fetchall()
        finally:
            self._return_connection(conn)

    def get_by_id(self, workspace_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, name, description, created_at, updated_at
                    FROM workspaces
                    WHERE id = %s AND deleted_at IS NULL
                """,
                    (workspace_id,),
                )
                return cursor.fetchone()
        finally:
            self._return_connection(conn)

    def create(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        conn = self._get_connection()
        try:
            workspace_id = uuid.uuid4()
            curr_time = datetime.now()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    INSERT INTO workspaces (id, name, description, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, name, description, created_at, updated_at
                """,
                    (workspace_id, name, description, curr_time, curr_time),
                )
                conn.commit()
                return cursor.fetchone()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self._return_connection(conn)

    def update(
        self,
        workspace_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            workspace = self.get_by_id(workspace_id)
            if not workspace:
                return None

            name = name if name is not None else workspace["name"]
            description = (
                description if description is not None else workspace["description"]
            )

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    UPDATE workspaces
                    SET name = %s, description = %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, name, description, created_at, updated_at
                """,
                    (name, description, workspace_id),
                )
                conn.commit()
                return cursor.fetchone()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self._return_connection(conn)

    def delete(self, workspace_id: uuid.UUID) -> bool:
        conn = self._get_connection()
        try:
            workspace = self.get_by_id(workspace_id)
            if not workspace:
                return False

            current_time = datetime.now()

            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE blocks
                    SET deleted_at = %s
                    WHERE workspace_id = %s AND deleted_at IS NULL
                """,
                    (current_time, workspace_id),
                )

                cursor.execute(
                    """
                    UPDATE workspaces
                    SET deleted_at = %s
                    WHERE id = %s AND deleted_at IS NULL
                """,
                    (current_time, workspace_id),
                )

                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self._return_connection(conn)
