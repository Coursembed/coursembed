from services.migration_service import PostgresMigrationService


class Services:
    def __init__(
        self, migration: PostgresMigrationService
    ):
        self.migration = migration
