"""add document_chunks

Revision ID: 23ad0a009bfa
Revises: cd72e49b2fea
Create Date: 2026-07-19 00:00:00.000000

"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "23ad0a009bfa"
down_revision: str | Sequence[str] | None = "cd72e49b2fea"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=True),
        # Generated column, not writable by the ORM - see app/models/document_chunk.py.
        sa.Column(
            "content_tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', content)", persisted=True),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_chunk"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index(
        "ix_document_chunks_content_tsv", "document_chunks", ["content_tsv"], postgresql_using="gin"
    )
    # Deliberately no ivfflat/hnsw index on `embedding`: at personal-corpus scale
    # (low hundreds of chunks) a brute-force cosine scan is effectively instant,
    # and ANN indexes need a representative data distribution to tune (lists/
    # probes) that doesn't exist yet. Revisit if the corpus grows substantially.


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_document_chunks_content_tsv", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
