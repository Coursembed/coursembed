from litestar import Litestar
from litestar.di import Provide
from litestar.config.cors import CORSConfig
from litestar.middleware.logging import LoggingMiddlewareConfig

from dependencies import get_services
from dependencies import get_repositories

from controllers.migration_controller import MigrationController
from controllers.block_controller import BlockController
from controllers.workspace_controller import WorkspaceController
from controllers.s3_controller import S3Controller


logging_middleware_config = LoggingMiddlewareConfig()

cors_config = CORSConfig(allow_origins=["*"])

app = Litestar(
    route_handlers=[
        MigrationController,
        BlockController,
        WorkspaceController,
        S3Controller
    ],
    dependencies={
        "services": Provide(get_services, sync_to_thread=False),
        "repositories": Provide(get_repositories, sync_to_thread=False)
    },
    middleware=[logging_middleware_config.middleware],
    cors_config=cors_config, 
    debug=True
)
