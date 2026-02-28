import os


class BaseConfig:
    DEBUG = False
    TESTING = False
    APP_NAME = "SupaGrad API"
    APP_ENV = os.getenv("APP_ENV", "development")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True


def get_config(config_name: str | None = None):
    env = (config_name or os.getenv("APP_ENV", "development")).lower()

    if env == "production":
        return ProductionConfig
    if env == "testing":
        return TestingConfig
    return DevelopmentConfig
