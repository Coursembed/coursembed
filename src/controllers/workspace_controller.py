import uuid
from typing import List, Dict, Any

from litestar import get, post, put, delete
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND
from litestar.exceptions import HTTPException
from litestar.controller import Controller

from models.workspace import WorkspaceCreate, WorkspaceUpdate
from repositories.base import Repositories


class WorkspaceController(Controller):
    path = "/workspaces"
    tags = ["workspaces"]

    @get("/")
    async def get_all_workspaces(self, repositories: Repositories) -> List[Dict[str, Any]]:
        return repositories.workspace.get_all()

    @get("/{workspace_id:uuid}", status_code=HTTP_200_OK)
    async def get_workspace(self, workspace_id: uuid.UUID, repositories: Repositories) -> Dict[str, Any]:
        workspace = repositories.workspace.get_by_id(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Workspace with ID {workspace_id} not found"
            )
        return workspace

    @post("/", status_code=HTTP_201_CREATED)
    async def create_workspace(self, data: WorkspaceCreate, repositories: Repositories) -> Dict[str, Any]:
        return repositories.workspace.create(
            name=data.name, 
            description=data.description
        )

    @put("/{workspace_id:uuid}", status_code=HTTP_200_OK)
    async def update_workspace(
        self, workspace_id: uuid.UUID, data: WorkspaceUpdate, repositories: Repositories
    ) -> Dict[str, Any]:
        updated_workspace = repositories.workspace.update(
            workspace_id=workspace_id,
            name=data.name,
            description=data.description
        )
        
        if not updated_workspace:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Workspace with ID {workspace_id} not found"
            )
        return updated_workspace

    @delete("/{workspace_id:uuid}", status_code=HTTP_200_OK)
    async def delete_workspace(self, workspace_id: uuid.UUID, repositories: Repositories) -> None:
        success = repositories.workspace.delete(workspace_id)
        if not success:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Workspace with ID {workspace_id} not found"
            )
        return {"success": True, "message": f"Workspace {workspace_id} deleted"}
