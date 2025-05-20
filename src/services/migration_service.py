from alembic.config import Config as AlembicConfig
from alembic import command

from utils.config import config


class PostgresMigrationService():
    def __init__(self):
        connection_url = f"postgresql://{config.postgres_db_username}:{config.postgres_db_password}@db:{config.postgres_db_port}/{config.postgres_db_name}"
        self.alembic_cfg = AlembicConfig("src/alembic.ini")
        self.alembic_cfg.set_section_option('alembic', 'sqlalchemy.url', connection_url)
    
    def up(self):
        command.upgrade(self.alembic_cfg, "head")
    
    def down_to_base(self):
        command.downgrade(self.alembic_cfg, "base")
