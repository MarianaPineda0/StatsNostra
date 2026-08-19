"""Fixtures compartidas: aislan cada test en una transaccion sobre la BD real.

No se usa una base de datos mock ni SQLite en memoria — las pruebas corren
contra PostgreSQL de verdad (la misma BD de desarrollo local), para que las
constraints reales (UNIQUE, CHECK, FK) tambien queden validadas.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app

settings = get_settings()
engine = create_engine(settings.database_url)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture()
def db_session():
    # Cada prueba corre dentro de una transaccion (con savepoint anidado
    # para soportar los commit() internos de los repositorios) que se
    # revierte al final, dejando la BD real intacta entre pruebas.
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _reiniciar_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    # Reemplaza la dependencia get_db real por una que entrega la sesion
    # transaccional de arriba, para que las peticiones HTTP del test usen
    # esa misma transaccion (y por lo tanto tambien se revierta al final)
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
