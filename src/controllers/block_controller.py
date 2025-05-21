import uuid
from typing import Any, Dict, List

from litestar import Controller, get, post, put, delete, patch
from litestar.exceptions import NotFoundException, HTTPException
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND

import models.block as block_models
from repositories.base import Repositories
from services.base import Services


class BlockController(Controller):
    path = "/blocks"
    tags = ["blocks"]
    
    @post("/", status_code=HTTP_201_CREATED)
    async def append_block_child(
        self, data: block_models.BlockAppendChild, repositories: Repositories,
    ) -> block_models.BlockResponse:
        block = repositories.block.append_block_child(
            block_type=data.type,
            properties=data.properties,
            workspace_id=data.workspace_id,
            parent_id=data.parent_id
        )
        return block_models.BlockResponse.parse_obj(block)
    
    @get("/{block_id:uuid}", status_code=HTTP_200_OK)
    async def get_block(
        self, block_id: uuid.UUID, repositories: Repositories
    ) -> block_models.BlockResponse:
        block = repositories.block.get_block(block_id)
        if not block:
            raise NotFoundException(f"Block with ID {block_id} not found")
        return block_models.BlockResponse.parse_obj(block)
    
    @get("/")
    async def get_all_blocks(self, repositories: Repositories) -> List[Dict[str, Any]]:
        return repositories.block.get_all()
    
    @get("/{block_id:uuid}/content", status_code=HTTP_200_OK)
    async def get_block_with_content(
        self, block_id: uuid.UUID, repositories: Repositories
    ) -> block_models.BlockContentResponse:
        block_with_content = repositories.block.get_block_with_content(block_id)
        if not block_with_content:
            raise NotFoundException(f"Block with ID {block_id} not found")
        return block_models.BlockContentResponse.parse_obj(block_with_content)
    
    @get("/{block_id:uuid}/children", status_code=HTTP_200_OK)
    async def get_block_children(
        self, block_id: uuid.UUID, repositories: Repositories
    ) -> List[block_models.BlockResponse]:
        children = repositories.block.get_block_children(block_id)
        return [block_models.BlockResponse.parse_obj(child) for child in children]
    
    @put("/{block_id:uuid}", status_code=HTTP_200_OK)
    async def update_block(
        self, block_id: uuid.UUID, data: block_models.BlockUpdate, repositories: Repositories
    ) -> block_models.BlockResponse:
        block = repositories.block.update_block(
            block_id=block_id,
            properties=data.properties,
            block_type=data.type
        )
        if not block:
            raise NotFoundException(f"Block with ID {block_id} not found")
        return block_models.BlockResponse.parse_obj(block)
    
    @patch("/{block_id:uuid}/move", status_code=HTTP_200_OK)
    async def move_block(
        self, block_id: uuid.UUID, data: block_models.BlockMove, repositories: Repositories
    ) -> block_models.BlockResponse:
        block = repositories.block.move_block(
            block_id=block_id,
            new_parent_id=data.parent_id,
            new_position=data.position
        )
        if not block:
            raise NotFoundException(f"Block with ID {block_id} not found")
        return block_models.BlockResponse.parse_obj(block)
    
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
        self, data: block_models.BatchOperationRequest, repositories: Repositories, services: Services
    ) -> block_models.BatchOperationResponse:
        operation_handlers = {
            block_models.BatchOperationType.CREATE: self._handle_create_operation,
            block_models.BatchOperationType.UPDATE: self._handle_update_operation,
            block_models.BatchOperationType.MOVE: self._handle_move_operation,
            block_models.BatchOperationType.DELETE: self._handle_delete_operation,
        }
        
        results = []
        for operation in data.operations:
            handler = operation_handlers.get(operation.type)
            result = await handler(operation, repositories, services)
            results.append(result)
        
        return block_models.BatchOperationResponse(results=results)
    
    async def _handle_create_operation(
        self, operation: block_models.BatchOperationType, repositories: Repositories, services: Services
    ) -> block_models.BatchOperationResult:
        result = block_models.BatchOperationResult(
            success=False,
            operation_type=operation.type,
            block_id=operation.block_id
        )
        
        try:
            if not operation.data or not isinstance(operation.data, block_models.BlockCreate):
                result.error = "Missing or invalid data for CREATE operation"
                return result
            
            if operation.data.type in [block_models.BlockTypeEnum.IMAGE, block_models.BlockTypeEnum.FILE]:
                file_path = services.s3.handle_block_file(operation.data.properties.get('file_path'), operation.block_id)
                if file_path:
                    operation.data.properties["file_path"] = file_path
                
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
            result.result = block_models.BlockResponse.parse_obj(block)
        except Exception as e:
            result.error = str(e)
            
        return result
    
    async def _handle_update_operation(
        self, operation: block_models.BatchOperationType, repositories: Repositories
    ) -> block_models.BatchOperationResult:
        result = block_models.BatchOperationResult(
            success=False,
            operation_type=operation.type,
            block_id=operation.block_id
        )
        
        try:
            if not operation.block_id:
                result.error = "Missing block_id for UPDATE operation"
                return result
                
            if not operation.data or not isinstance(operation.data, block_models.BlockUpdate):
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
            result.result = block_models.BlockResponse.parse_obj(block)
        except Exception as e:
            result.error = str(e)
            
        return result
    
    async def _handle_move_operation(
        self, operation: block_models.BatchOperationType, repositories: Repositories
    ) -> block_models.BatchOperationResult:
        result = block_models.BatchOperationResult(
            success=False,
            operation_type=operation.type,
            block_id=operation.block_id
        )
        
        try:
            if not operation.block_id:
                result.error = "Missing block_id for MOVE operation"
                return result
                
            if not operation.data or not isinstance(operation.data, block_models.BlockMove):
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
            result.result = block_models.BlockResponse.parse_obj(block)
        except Exception as e:
            result.error = str(e)
            
        return result
    
    async def _handle_delete_operation(
        self, operation: block_models.BatchOperationType, repositories: Repositories, services: Services
    ) -> block_models.BatchOperationResult:
        result = block_models.BatchOperationResult(
            success=False,
            operation_type=operation.type,
            block_id=operation.block_id
        )
        
        try:
            if not operation.block_id:
                result.error = "Missing block_id for DELETE operation"
                return result
            
            block = repositories.block.get_block(operation.block_id)
            if not block:
                result.error = f"Block with ID {operation.block_id} not found"
                return result

            if block["type"] in [block_models.BlockTypeEnum.IMAGE.value, block_models.BlockTypeEnum.FILE.value]:
                if "file_path" in block["properties"]:
                    services.s3.soft_delete(block["properties"]["file_path"])
            
            deleted = repositories.block.delete_block(operation.block_id)
            
            if deleted:
                result.success = True
                result.result = {"message": f"Block {operation.block_id} deleted"}
            else:
                result.error = f"Failed to delete block {operation.block_id}"
                
        except Exception as e:
            result.error = str(e)
            
        return result
