import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict, UUID4
from sqlalchemy import Column, ForeignKey, String, Table, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


Base = declarative_base()

block_content_association = Table(
    'block_content_association',
    Base.metadata,
    Column('parent_block_id', UUID(as_uuid=True), ForeignKey('blocks.id'), primary_key=True),
    Column('child_block_id', UUID(as_uuid=True), ForeignKey('blocks.id'), primary_key=True),
    Column('position', Integer, nullable=False, default=0)
)

class Block(Base):
    __tablename__ = 'blocks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False)
    properties = Column(JSONB, default={})
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)

    parent = relationship("Block", remote_side=[id], back_populates="children")
    children = relationship("Block", back_populates="parent")
    content_blocks = relationship(
        "Block",
        secondary="block_content_association",
        primaryjoin="Block.id == block_content_association.c.parent_block_id",
        secondaryjoin="Block.id == block_content_association.c.child_block_id",
        back_populates="container_blocks"
    )
    container_blocks = relationship(
        "Block",
        secondary="block_content_association",
        primaryjoin="Block.id == block_content_association.c.child_block_id",
        secondaryjoin="Block.id == block_content_association.c.parent_block_id",
        back_populates="content_blocks"
    )


class BlockTypeEnum(str, Enum):
    ROOT_BLOCK = "root_block"
    PAGE = "page"
    TEXT = "text"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    BULLET_LIST = "bullet_list"
    NUMBERED_LIST = "numbered_list"
    TO_DO = "to_do"
    TOGGLE = "toggle"
    CODE = "code"
    IMAGE = "image"
    FILE = "file"


class BlockCreate(BaseModel):
    workspace_id: UUID4
    type: BlockTypeEnum
    properties: Dict[str, Any] = Field(default_factory=dict)
    parent_id: Optional[UUID4] = None
    position: int = 0


class BlockAppendChild(BaseModel):
    type: BlockTypeEnum
    properties: Dict[str, Any] = Field(default_factory=dict)
    parent_id: UUID4
    workspace_id: UUID4


class BlockUpdate(BaseModel):
    type: Optional[BlockTypeEnum] = None
    properties: Optional[Dict[str, Any]] = None


class BlockMove(BaseModel):
    parent_id: Optional[UUID4]
    position: int = 0


class BlockDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BlockResponse(BaseModel):
    id: UUID4
    type: str
    properties: Dict[str, Any]
    parent_id: Optional[UUID4] = None
    workspace_id: UUID4
    position: int


class BlockContentResponse(BlockResponse):
    content: List[BlockResponse] = Field(default_factory=list)


class BatchOperationType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"


class BatchBlockOperation(BaseModel):
    type: BatchOperationType
    block_id: UUID4
    data: Optional[Union[BlockCreate, BlockUpdate, dict]] = None


class BatchOperationRequest(BaseModel):
    operations: List[BatchBlockOperation]


class BatchOperationResult(BaseModel):
    success: bool
    operation_type: BatchOperationType
    block_id: Optional[UUID4] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class BatchOperationResponse(BaseModel):
    results: List[BatchOperationResult]
