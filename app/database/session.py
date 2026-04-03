from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from ..config import Config

def create_engine(config: Config):
    return create_async_engine(
        config.DB_URL.get_secret_value(),
        pool_size=20,
        max_overflow=30,
        pool_timeout=60.0,
        pool_recycle=3600,
        pool_pre_ping=True
    )
def create_sessionmaker(engine):
    return async_sessionmaker(engine,expire_on_commit=False)