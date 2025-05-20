from repositories.block_repository import BlockRepository
from repositories.workspace_repository import WorkspaceRepository


class Repositories:
    def __init__(
        self, 
        block: BlockRepository,
        workspace: WorkspaceRepository
    ):
        self.block = block
        self.workspace = workspace
