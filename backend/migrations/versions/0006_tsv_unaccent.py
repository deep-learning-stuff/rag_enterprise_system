"""chunks: tsv tolerante a tildes (spanish + spanish_unaccent)

Revision ID: 0006_tsv_unaccent
Revises: 0005_chunk_tsv
Create Date: 2026-07-19

Problema: con la configuración `spanish` a secas, quien escribe sin tildes no encuentra
nada, porque el stemmer produce lexemas distintos ('almacén' -> 'almacen', pero
'almacen' -> 'almac').

Lo obvio sería aplicar `unaccent` antes del stemmer, pero medido resulta que eso ROMPE
otras coincidencias: el stemmer snowball español está pensado para texto CON tildes, y
al quitarlas algunas de sus reglas dejan de dispararse.

    palabra        spanish        spanish_unaccent
    almacén        almacen        almac        <- deja de casar con "almacenes"
    almacenes      almacen        almacen
    devolución     devolu         devolucion   <- deja de casar con "devoluciones"
    devoluciones   devolu         devolu

Por eso se indexa con LAS DOS configuraciones concatenadas (`||` une tsvectors): el
índice contiene los lexemas de ambas, así que cubre tanto singular/plural (que aporta
`spanish`) como la tolerancia a tildes (que aporta `spanish_unaccent`). La consulta une
las dos igual (ver retrieval/search.py); si no usara ambas, no encontraría la mitad.

Límite conocido y aceptado: escribir sin tilde cuando el documento usa el plural
("almacen" contra "almacenes") sigue sin casar por full-text; no hay combinación de
configuraciones que lo arregle. Ese caso lo cubre la búsqueda vectorial, a la que las
tildes le son indiferentes porque compara significado.

La columna `tsv` es GENERATED y la expresión de una columna generada no se puede
alterar: hay que borrarla y recrearla. Postgres la recalcula sola para las filas
existentes, así que no hay que reprocesar documentos ni volver a embeber.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_tsv_unaccent"
down_revision: Union[str, None] = "0005_chunk_tsv"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Expresión del tsv: los lexemas de las dos configuraciones, unidos.
_TSV_EXPR = "to_tsvector('spanish', texto) || to_tsvector('spanish_unaccent', texto)"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    # Copia de `spanish` en la que `unaccent` se aplica antes que el stemmer.
    op.execute("CREATE TEXT SEARCH CONFIGURATION spanish_unaccent (COPY = spanish)")
    op.execute(
        "ALTER TEXT SEARCH CONFIGURATION spanish_unaccent "
        "ALTER MAPPING FOR hword, hword_part, word WITH unaccent, spanish_stem"
    )

    op.execute("DROP INDEX IF EXISTS ix_chunks_tsv")
    op.execute("ALTER TABLE chunks DROP COLUMN tsv")
    op.execute(
        f"ALTER TABLE chunks ADD COLUMN tsv tsvector GENERATED ALWAYS AS ({_TSV_EXPR}) STORED"
    )
    op.execute("CREATE INDEX ix_chunks_tsv ON chunks USING gin (tsv)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_tsv")
    op.execute("ALTER TABLE chunks DROP COLUMN tsv")
    op.execute(
        "ALTER TABLE chunks ADD COLUMN tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('spanish', texto)) STORED"
    )
    op.execute("CREATE INDEX ix_chunks_tsv ON chunks USING gin (tsv)")
    op.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS spanish_unaccent")
    # La extensión no se borra: puede haberla creado o estar usándola otra cosa.
