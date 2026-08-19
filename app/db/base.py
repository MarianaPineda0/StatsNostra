from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase base de todos los modelos (Apostador, Partido, Prediccion).

    Alembic usa Base.metadata para saber que tablas debe generar/migrar
    (ver migrations/env.py) — por eso todos los modelos deben heredar de aqui.
    """
