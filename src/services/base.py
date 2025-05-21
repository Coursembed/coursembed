from services.migration_service import PostgresMigrationService
from services.minio_service import MinioService


class Services:
    def __init__(
        self, 
        migration: PostgresMigrationService,
        s3: MinioService
    ):
        self.migration = migration
        self.s3 = s3
