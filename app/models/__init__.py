# Reexporta los 3 modelos para que un simple "import app.models" (usado en
# migrations/env.py) los registre todos en Base.metadata, sin que Alembic
# tenga que importar cada archivo de app/models/ por separado.
from app.models.apostador import Apostador
from app.models.partido import EstadoPartido, Partido
from app.models.prediccion import Prediccion

__all__ = ["Apostador", "EstadoPartido", "Partido", "Prediccion"]
