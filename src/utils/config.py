import environ


@environ.config(prefix="")
class AppConfig:
    postgres_db_name = environ.var()
    postgres_db_port = environ.var()
    postgres_db_host = environ.var()
    postgres_db_username = environ.var()
    postgres_db_password = environ.var()
    postgres_db_min_connections = environ.var()
    postgres_db_max_connections = environ.var()


config = environ.to_config(AppConfig)
