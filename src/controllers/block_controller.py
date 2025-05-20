import uuid
from typing import Any, Dict, List

from litestar import Controller, get, post, put, delete, patch
from litestar.exceptions import NotFoundException, HTTPException
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND

from models.block import (
    BlockCreate, BlockUpdate, BlockMove,
    BlockResponse, BlockContentResponse,
    BatchOperationResult, BatchOperationType,
    BatchOperationRequest, BatchOperationResponse,
    BlockAppendChild, BlockDelete
)
from repositories.base import Repositories


class BlockController(Controller):
    path = "/blocks"
    tags = ["blocks"]
    
    @post("/", status_code=HTTP_201_CREATED)
    async def append_block_child(
        self, data: BlockAppendChild, repositories: Repositories
    ) -> BlockResponse:
        block = repositories.block.append_block_child(
            block_type=data.type,
            properties=data.properties,
            workspace_id=data.workspace_id,
            parent_id=data.parent_id
        )
        return BlockResponse.parse_obj(block)
    
    @get("/{block_id:uuid}", status_code=HTTP_200_OK)
    async def get_block(
        self, block_id: uuid.UUID, repositories: Repositories
    ) -> BlockResponse:
        block = repositories.block.get_block(block_id)
        if not block:
            raise NotFoundException(f"Block with ID {block_id} not found")
        return BlockResponse.parse_obj(block)
    
    @get("/")
    async def get_all_blocks(self, repositories: Repositories) -> List[Dict[str, Any]]:
        return repositories.block.get_all()
    
    @get("/{block_id:uuid}/content", status_code=HTTP_200_OK)
    async def get_block_with_content(
        self, block_id: uuid.UUID, repositories: Repositories
    ) -> BlockContentResponse:
        block_with_content = repositories.block.get_block_with_content(block_id)
        if not block_with_content:
            raise NotFoundException(f"Block with ID {block_id} not found")
        return BlockContentResponse.parse_obj(block_with_content)
    
    @get("/{block_id:uuid}/children", status_code=HTTP_200_OK)
    async def get_block_children(
        self, block_id: uuid.UUID, repositories: Repositories
    ) -> List[BlockResponse]:
        children = repositories.block.get_block_children(block_id)
        return [BlockResponse.parse_obj(child) for child in children]
    
    @put("/{block_id:uuid}", status_code=HTTP_200_OK)
    async def update_block(
        self, block_id: uuid.UUID, data: BlockUpdate, repositories: Repositories
    ) -> BlockResponse:
        block = repositories.block.update_block(
            block_id=block_id,
            properties=data.properties,
            block_type=data.type
        )
        if not block:
            raise NotFoundException(f"Block with ID {block_id} not found")
        return BlockResponse.parse_obj(block)
    
    @patch("/{block_id:uuid}/move", status_code=HTTP_200_OK)
    async def move_block(
        self, block_id: uuid.UUID, data: BlockMove, repositories: Repositories
    ) -> BlockResponse:
        block = repositories.block.move_block(
            block_id=block_id,
            new_parent_id=data.parent_id,
            new_position=data.position
        )
        if not block:
            raise NotFoundException(f"Block with ID {block_id} not found")
        return BlockResponse.parse_obj(block)
    
    @delete("/{block_id:uuid}", status_code=HTTP_200_OK)
    async def delete_block(
        self, block_id: uuid.UUID,  repositories: Repositories
    ) -> Dict[str, Any]:
        deleted = repositories.block.delete_block(block_id)
        if not deleted:
            raise NotFoundException(f"Block with ID {block_id} not found")
        return {"success": True, "message": f"Block {block_id} deleted"}

    @get("/{workspace_id:uuid}/tree", status_code=HTTP_200_OK)
    async def get_blocks_tree(self, workspace_id: uuid.UUID, repositories: Repositories) -> List[Dict[str, Any]]:
        workspace = repositories.workspace.get_by_id(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Workspace with ID {workspace_id} not found"
            )
        
        tree = repositories.block.get_blocks_tree(workspace_id)
        return tree

    @post("/batch", status_code=HTTP_200_OK)
    async def batch_operations(
        self, data: BatchOperationRequest, repositories: Repositories
    ) -> BatchOperationResponse:
        operation_handlers = {
            BatchOperationType.CREATE: self._handle_create_operation,
            BatchOperationType.UPDATE: self._handle_update_operation,
            BatchOperationType.MOVE: self._handle_move_operation,
            BatchOperationType.DELETE: self._handle_delete_operation,
        }
        
        results = []
        for operation in data.operations:
            handler = operation_handlers.get(operation.type)
            result = await handler(operation, repositories)
            results.append(result)
        
        return BatchOperationResponse(results=results)
    
    async def _handle_create_operation(
        self, operation: BatchOperationType, repositories: Repositories
    ) -> BatchOperationResult:
        result = BatchOperationResult(
            success=False,
            operation_type=operation.type,
            block_id=operation.block_id
        )
        
        try:
            if not operation.data or not isinstance(operation.data, BlockCreate):
                result.error = "Missing or invalid data for CREATE operation"
                return result
                
            block = repositories.block.create_block(
                block_id=operation.block_id,
                block_type=operation.data.type,
                properties=operation.data.properties,
                workspace_id=operation.data.workspace_id,
                parent_id=operation.data.parent_id,
                position=operation.data.position
            )
            result.success = True
            result.block_id = block["id"]
            result.result = BlockResponse.parse_obj(block)
        except Exception as e:
            result.error = str(e)
            
        return result
    
    async def _handle_update_operation(
        self, operation: BatchOperationType, repositories: Repositories
    ) -> BatchOperationResult:
        result = BatchOperationResult(
            success=False,
            operation_type=operation.type,
            block_id=operation.block_id
        )
        
        try:
            if not operation.block_id:
                result.error = "Missing block_id for UPDATE operation"
                return result
                
            if not operation.data or not isinstance(operation.data, BlockUpdate):
                result.error = "Missing or invalid data for UPDATE operation"
                return result
                
            block = repositories.block.update_block(
                block_id=operation.block_id,
                properties=operation.data.properties,
                block_type=operation.data.type
            )
            
            if not block:
                result.error = f"Block with ID {operation.block_id} not found"
                return result
                
            result.success = True
            result.result = BlockResponse.parse_obj(block)
        except Exception as e:
            result.error = str(e)
            
        return result
    
    async def _handle_move_operation(
        self, operation: BatchOperationType, repositories: Repositories
    ) -> BatchOperationResult:
        result = BatchOperationResult(
            success=False,
            operation_type=operation.type,
            block_id=operation.block_id
        )
        
        try:
            if not operation.block_id:
                result.error = "Missing block_id for MOVE operation"
                return result
                
            if not operation.data or not isinstance(operation.data, BlockMove):
                result.error = "Missing or invalid data for MOVE operation"
                return result
                
            block = repositories.block.move_block(
                block_id=operation.block_id,
                new_parent_id=operation.data.parent_id,
                new_position=operation.data.position
            )
            
            if not block:
                result.error = f"Block with ID {operation.block_id} not found"
                return result
                
            result.success = True
            result.result = BlockResponse.parse_obj(block)
        except Exception as e:
            result.error = str(e)
            
        return result
    
    async def _handle_delete_operation(
        self, operation: BatchOperationType, repositories: Repositories
    ) -> BatchOperationResult:
        result = BatchOperationResult(
            success=False,
            operation_type=operation.type,
            block_id=operation.block_id
        )
        
        try:
            if not operation.block_id:
                result.error = "Missing block_id for DELETE operation"
                return result
                
            deleted = repositories.block.delete_block(operation.block_id, BlockDelete)
            
            if not deleted:
                result.error = f"Block with ID {operation.block_id} not found"
                return result
                
            result.success = True
            result.result = {"message": f"Block {operation.block_id} deleted"}
        except Exception as e:
            result.error = str(e)
            
        return result
