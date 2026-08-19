from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# pool_pre_ping evita usar una conexion muerta del pool (por ejemplo, si
# Render reinicia la BD por inactividad): SQLAlchemy la prueba antes de
# usarla y la reemplaza si ya no responde.
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    # Dependencia de FastAPI: abre una sesion nueva por cada request y
    # garantiza su cierre al finalizar, incluso si la ruta lanza un error
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
