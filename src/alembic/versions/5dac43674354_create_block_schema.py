from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = '5dac43674354'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workspaces',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True)
    )

    op.create_table(
        'blocks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('properties', JSONB, server_default='{}'),
        sa.Column('workspace_id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], )
    )

    op.create_table(
        'block_content_association',
        sa.Column('parent_block_id', UUID(as_uuid=True), nullable=False),
        sa.Column('child_block_id', UUID(as_uuid=True), nullable=False),
        sa.Column('position', sa.Integer, nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['parent_block_id'], ['blocks.id'], ),
        sa.ForeignKeyConstraint(['child_block_id'], ['blocks.id'], ),
        sa.PrimaryKeyConstraint('parent_block_id', 'child_block_id')
    )

    op.create_index('idx_blocks_workspace_id', 'blocks', ['workspace_id'])
    op.create_index('idx_blocks_type', 'blocks', ['type'])
    op.create_index('idx_block_content_parent', 'block_content_association', ['parent_block_id'])
    op.create_index('idx_block_content_child', 'block_content_association', ['child_block_id'])
    op.create_index('idx_block_content_position', 'block_content_association', ['position'])

def downgrade() -> None:
    op.drop_table('block_content_association')
    op.drop_table('blocks')
    op.drop_table('workspaces')
