from services.base import Services
from services.migration_service import PostgresMigrationService

from repositories.base import Repositories
from repositories.block_repository import BlockRepository
from repositories.workspace_repository import WorkspaceRepository

from utils.psycopg2 import db_manager


services = Services(
    migration=PostgresMigrationService()
)

def get_services() -> Services:
    return services

pool = db_manager.get_pool()

repositories = Repositories(
    block=BlockRepository(pool),
    workspace=WorkspaceRepository(pool)
)

def get_repositories() -> Repositories:
    return repositories
