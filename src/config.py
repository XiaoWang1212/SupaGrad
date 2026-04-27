import os


class BaseConfig:
    DEBUG = False
    TESTING = False
    APP_NAME = "SupaGrad API"
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")


class DevelopmentConfig(BaseConfig):
    pass


class ProductionConfig(BaseConfig):
    pass


class TestingConfig(BaseConfig):
    pass


def get_config(config_name: str | None = None):
    config_map = {
        None: DevelopmentConfig,
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    return config_map.get(config_name, DevelopmentConfig)
