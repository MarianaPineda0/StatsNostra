"""agregar confianza a predicciones

Revision ID: 89b8d15bef23
Revises: fe9f3554bedb
Create Date: 2026-10-23 17:30:44.308223

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89b8d15bef23'
down_revision: Union[str, None] = 'fe9f3554bedb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fase Expand: la columna admite NULL, asi la version estable (que no la
    # conoce) sigue leyendo y escribiendo igual y el canary se puede abortar
    # sin tocar datos. La fase Contract iria en otra migracion, cuando la
    # estable ya no exista
    op.add_column('predicciones', sa.Column('confianza', sa.SmallInteger(), nullable=True))
    op.create_check_constraint(
        'ck_prediccion_confianza_rango',
        'predicciones',
        'confianza IS NULL OR (confianza >= 1 AND confianza <= 5)',
    )


def downgrade() -> None:
    op.drop_constraint('ck_prediccion_confianza_rango', 'predicciones', type_='check')
    op.drop_column('predicciones', 'confianza')
