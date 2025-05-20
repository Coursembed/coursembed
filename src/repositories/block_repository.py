import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from psycopg2.extras import RealDictCursor, Json, register_uuid
from psycopg2.pool import ThreadedConnectionPool


class BlockRepository:
    def __init__(self, pool: ThreadedConnectionPool):
        self.pool = pool
        register_uuid()
    
    def _get_connection(self):
        return self.pool.getconn()
    
    def _return_connection(self, conn):
        self.pool.putconn(conn)
    
    def create_block(
        self,
        block_id: uuid.UUID,
        block_type: str,
        properties: Dict[str, Any], 
        workspace_id: uuid.UUID,
        parent_id: Optional[uuid.UUID] = None,
        position: int = 0
    ) -> Dict[str, Any]:
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if parent_id:
                    self._shift_positions(cursor, parent_id, position)
                
                cursor.execute(
                    """
                    INSERT INTO blocks (
                        id, type, properties, workspace_id
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        block_id, block_type, Json(properties), workspace_id
                    )
                )
                block = cursor.fetchone()
                
                if parent_id:
                    cursor.execute(
                        """
                        INSERT INTO block_content_association (
                            parent_block_id, child_block_id, position
                        ) VALUES (%s, %s, %s)
                        """,
                        (parent_id, block_id, position)
                    )
                
                conn.commit()
                
                result = dict(block)
                result['position'] = position
                result['parent_id'] = parent_id
                
                return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self._return_connection(conn)
    
    def _shift_positions(self, cursor, parent_id: uuid.UUID, from_position: int) -> None:
        cursor.execute(
            """
            UPDATE block_content_association
            SET position = position + 1
            WHERE parent_block_id = %s AND position >= %s
            """,
            (parent_id, from_position)
        )

    def append_block_child(
        self,
        block_type: str,
        properties: Dict[str, Any], 
        workspace_id: uuid.UUID,
        parent_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        conn = self._get_connection()
        block_id = uuid.uuid4()
        position = 0

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if parent_id:
                    self._shift_positions(cursor, parent_id, position)
                
                cursor.execute(
                    """
                    INSERT INTO blocks (
                        id, type, properties, workspace_id
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        block_id, block_type, Json(properties), workspace_id
                    )
                )
                block = cursor.fetchone()
                
                if parent_id:
                    cursor.execute(
                        """
                        INSERT INTO block_content_association (
                            parent_block_id, child_block_id, position
                        ) VALUES (%s, %s, %s)
                        """,
                        (parent_id, block_id, position)
                    )
                
                conn.commit()
                
                result = dict(block)
                result['position'] = position
                result['parent_id'] = parent_id
                
                return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self._return_connection(conn)
    
    def get_block(self, block_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, type, properties, workspace_id FROM blocks 
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (block_id,)
                )
                block = cursor.fetchone()
                
                if not block:
                    return None
                
                position_info = self._get_block_position(block_id)
                
                result = dict(block)
                if position_info:
                    parent_id, position = position_info
                    result['position'] = position
                    result['parent_id'] = parent_id
                else:
                    result['position'] = 0
                    result['parent_id'] = None
                    
                return result
        finally:
            self._return_connection(conn)

    def get_all(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT b.id, b.type, b.properties, b.workspace_id,
                           bca.parent_block_id as parent_id,
                           COALESCE(bca.position, 0) as position
                    FROM blocks b
                    LEFT JOIN block_content_association bca ON b.id = bca.child_block_id
                    WHERE b.deleted_at IS NULL
                    ORDER BY b.created_at DESC
                """)
                return cursor.fetchall()
        finally:
            self._return_connection(conn)
    
    def get_block_with_content(self, block_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, type, properties, workspace_id FROM blocks 
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (block_id,)
                )
                block = cursor.fetchone()
                
                if not block:
                    return None
                
                position_info = self._get_block_position(block_id)
                
                result = dict(block)
                if position_info:
                    parent_id, position = position_info
                    result['position'] = position
                    result['parent_id'] = parent_id
                else:
                    result['position'] = 0
                    result['parent_id'] = None
                
                cursor.execute(
                    """
                    SELECT b.id, b.type, b.properties, b.workspace_id,
                           bca.parent_block_id as parent_id, 
                           bca.position as position
                    FROM blocks b
                    JOIN block_content_association bca ON b.id = bca.child_block_id
                    WHERE bca.parent_block_id = %s AND b.deleted_at IS NULL
                    ORDER BY bca.position
                    """,
                    (block_id,)
                )
                content_blocks = cursor.fetchall()
                
                result['content'] = [dict(b) for b in content_blocks]
                
                return result
        finally:
            self._return_connection(conn)
    
    def get_block_children(self, block_id: uuid.UUID) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT b.id, b.type, b.properties, b.workspace_id,
                           bca.parent_block_id as parent_id, 
                           bca.position AS position 
                    FROM blocks b
                    JOIN block_content_association bca ON b.id = bca.child_block_id
                    WHERE bca.parent_block_id = %s AND b.deleted_at IS NULL
                    ORDER BY bca.position
                    """,
                    (block_id,)
                )
                children = cursor.fetchall()
                return [dict(child) for child in children]
        finally:
            self._return_connection(conn)
    
    def _get_block_position(self, block_id: uuid.UUID) -> Optional[Tuple[uuid.UUID, int]]:
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT parent_block_id, position FROM block_content_association
                    WHERE child_block_id = %s
                    """,
                    (block_id,)
                )
                result = cursor.fetchone()
                return result if result else None
        finally:
            self._return_connection(conn)
    
    def update_block(
        self, 
        block_id: uuid.UUID, 
        properties: Optional[Dict[str, Any]] = None,
        block_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM blocks 
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (block_id,)
                )
                block = cursor.fetchone()
                
                if not block:
                    return None
                
                update_parts = []
                update_values = []
                
                if properties:
                    current_props = block['properties'] or {}
                    current_props.update(properties)
                    update_parts.append("properties = %s")
                    update_values.append(Json(current_props))
                
                if block_type:
                    update_parts.append("type = %s")
                    update_values.append(block_type)
                
                update_parts.append("updated_at = %s")
                update_values.append(datetime.now())
                
                if update_parts:
                    update_query = f"""
                        UPDATE blocks SET {', '.join(update_parts)}
                        WHERE id = %s
                        RETURNING *
                    """
                    update_values.append(block_id)
                    
                    cursor.execute(update_query, update_values)
                    updated_block = cursor.fetchone()
                    conn.commit()
                    
                    result = dict(updated_block)
                    position_info = self._get_block_position(block_id)
                    
                    if position_info:
                        parent_id, position = position_info
                        result['position'] = position
                        result['parent_id'] = parent_id
                    else:
                        result['position'] = 0
                        result['parent_id'] = None
                        
                    return result
                
                result = dict(block)
                position_info = self._get_block_position(block_id)
                
                if position_info:
                    parent_id, position = position_info
                    result['position'] = position
                    result['parent_id'] = parent_id
                else:
                    result['position'] = 0
                    result['parent_id'] = None
                    
                return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self._return_connection(conn)
    
    def delete_block(self, block_id: uuid.UUID) -> bool:
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id FROM blocks 
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (block_id,)
                )
                if not cursor.fetchone():
                    return False
                
                position_info = self._get_block_position(block_id)
                
                self._delete_children_recursively(cursor, block_id)
                
                cursor.execute(
                    """
                    DELETE FROM block_content_association
                    WHERE child_block_id = %s
                    """,
                    (block_id,)
                )
                
                cursor.execute(
                    """
                    DELETE FROM blocks 
                    WHERE id = %s
                    """,
                    (block_id,)
                )
                
                if position_info:
                    parent_id, position = position_info
                    cursor.execute(
                        """
                        UPDATE block_content_association
                        SET position = position - 1
                        WHERE parent_block_id = %s AND position > %s
                        """,
                        (parent_id, position)
                    )
                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self._return_connection(conn)

    def _delete_children_recursively(self, cursor, parent_id: uuid.UUID) -> None:
        cursor.execute(
            """
            SELECT child_block_id FROM block_content_association
            WHERE parent_block_id = %s
            """,
            (parent_id,)
        )
        children = [row[0] for row in cursor.fetchall()]
        
        for child_id in children:
            self._delete_children_recursively(cursor, child_id)
            
            cursor.execute(
                """
                DELETE FROM block_content_association
                WHERE parent_block_id = %s OR child_block_id = %s
                """,
                (child_id, child_id)
            )
            
            cursor.execute(
                """
                DELETE FROM blocks 
                WHERE id = %s
                """,
                (child_id,)
            )
    
    def move_block(
        self, 
        block_id: uuid.UUID, 
        new_parent_id: uuid.UUID,
        new_position: int
    ) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM blocks 
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (block_id,)
                )
                block = cursor.fetchone()
                if not block:
                    return None
                
                cursor.execute(
                    """
                    SELECT id FROM blocks 
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (new_parent_id,)
                )
                if not cursor.fetchone():
                    return None
                
                position_info = self._get_block_position(block_id)
                
                if position_info:
                    old_parent_id, old_position = position_info
                    cursor.execute(
                        """
                        DELETE FROM block_content_association
                        WHERE parent_block_id = %s AND child_block_id = %s
                        """,
                        (old_parent_id, block_id)
                    )
                    
                    cursor.execute(
                        """
                        UPDATE block_content_association
                        SET position = position - 1
                        WHERE parent_block_id = %s AND position > %s
                        """,
                        (old_parent_id, old_position)
                    )
                
                self._shift_positions(cursor, new_parent_id, new_position)
                
                cursor.execute(
                    """
                    UPDATE blocks
                    SET updated_at = %s
                    WHERE id = %s
                    RETURNING *
                    """,
                    (datetime.now(), block_id)
                )
                updated_block = cursor.fetchone()

                cursor.execute(
                    """
                    INSERT INTO block_content_association (
                        parent_block_id, child_block_id, position
                    ) VALUES (%s, %s, %s)
                    """,
                    (new_parent_id, block_id, new_position)
                )
                
                conn.commit()
                
                result = dict(updated_block)
                result['position'] = new_position
                result['parent_id'] = new_parent_id
                return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self._return_connection(conn)

    def get_blocks_tree(
        self,
        workspace_id: uuid.UUID,
        parent_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if parent_id:
                    cursor.execute(
                        """
                        SELECT b.id, b.type, b.properties, b.workspace_id,
                               bca.parent_block_id as parent_id,
                               bca.position
                        FROM blocks b
                        JOIN block_content_association bca ON b.id = bca.child_block_id
                        WHERE b.workspace_id = %s AND bca.parent_block_id = %s 
                        AND b.deleted_at IS NULL
                        ORDER BY bca.position
                        """,
                        (workspace_id, parent_id)
                    )
                else:
                    cursor.execute(
                        """
                        SELECT b.id, b.type, b.properties, b.workspace_id, 
                               NULL as parent_id, 0 as position 
                        FROM blocks b
                        LEFT JOIN block_content_association bca ON b.id = bca.child_block_id
                        WHERE b.workspace_id = %s 
                        AND bca.child_block_id IS NULL 
                        AND b.deleted_at IS NULL
                        """,
                        (workspace_id,)
                    )
                
                blocks = [dict(block) for block in cursor.fetchall()]
                
                for block in blocks:
                    block["content"] = self._get_children_recursive(
                        workspace_id=workspace_id, 
                        parent_id=block["id"],
                        conn=conn
                    )
                        
                return blocks
        finally:
            self._return_connection(conn)
    
    def _get_children_recursive(
        self,
        workspace_id: uuid.UUID,
        parent_id: uuid.UUID,
        conn
    ) -> List[Dict[str, Any]]:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT b.id, b.type, b.properties, b.workspace_id,
                       bca.parent_block_id as parent_id,
                       bca.position
                FROM blocks b
                JOIN block_content_association bca ON b.id = bca.child_block_id
                WHERE b.workspace_id = %s AND bca.parent_block_id = %s 
                AND b.deleted_at IS NULL
                ORDER BY bca.position
                """,
                (workspace_id, parent_id)
            )
            
            children = [dict(block) for block in cursor.fetchall()]
            
            for child in children:
                child["content"] = self._get_children_recursive(
                    workspace_id=workspace_id,
                    parent_id=child["id"],
                    conn=conn
                )
                
            return children
