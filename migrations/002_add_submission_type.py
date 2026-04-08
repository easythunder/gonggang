"""Database migration: Add submission type and payload_ref columns.

Revision ID: 002_add_submission_type
Revises: 001_initial
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Apply migrations."""
    # Create submission_type ENUM
    op.execute("CREATE TYPE submission_type AS ENUM ('image', 'link', 'manual')")

    # Add type column with default 'image' for backward compatibility
    op.add_column(
        'submissions',
        sa.Column(
            'type',
            sa.Enum('image', 'link', 'manual', name='submission_type'),
            nullable=False,
            server_default='image',
        ),
    )

    # Add payload_ref column (nullable - only used for link/manual types)
    op.add_column(
        'submissions',
        sa.Column('payload_ref', sa.String(500), nullable=True),
    )


def downgrade():
    """Revert migrations."""
    op.drop_column('submissions', 'payload_ref')
    op.drop_column('submissions', 'type')
    op.execute("DROP TYPE submission_type")
