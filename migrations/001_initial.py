"""Database migration: Initial schema.

Revision ID: 001_initial
Revises: 
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Setup Alembic metadata
migration_meta_data = sa.MetaData()


def upgrade():
    """Apply migrations."""
    # Create ENUM types
    op.execute("CREATE TYPE submission_status AS ENUM ('success', 'failed', 'pending')")

    # Create groups table
    op.create_table(
        'groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('display_unit_minutes', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('admin_token', sa.String(255), nullable=False, unique=True),
        sa.Column('invite_url', sa.String(500), nullable=False, unique=True),
        sa.Column('share_url', sa.String(500), nullable=False, unique=True),
        sa.Column('max_participants', sa.Integer(), nullable=False, server_default='50'),
    )
    op.create_index('ix_groups_expires_at', 'groups', ['expires_at'])

    # Create submissions table
    op.create_table(
        'submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nickname', sa.String(255), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.Enum('success', 'failed', 'pending', name='submission_status'), nullable=False),
        sa.Column('error_reason', sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_submissions_group_id', 'submissions', ['group_id'])
    op.create_unique_constraint('uq_submissions_group_nickname', 'submissions', ['group_id', 'nickname'])

    # Create intervals table
    op.create_table(
        'intervals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('start_minute', sa.Integer(), nullable=False),
        sa.Column('end_minute', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_intervals_submission_id', 'intervals', ['submission_id'])
    op.create_index('ix_intervals_day_start', 'intervals', ['day_of_week', 'start_minute'])

    # Create group_free_time_results table
    op.create_table(
        'group_free_time_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('availability_by_day', postgresql.JSON(), nullable=True),
        sa.Column('free_time_intervals', postgresql.JSON(), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.Enum('success', 'failed', 'pending', name='submission_status'), nullable=False),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_group_free_time_results_group_id', 'group_free_time_results', ['group_id'])

    # Create deletion_logs table
    op.create_table(
        'deletion_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('group_id',postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.String(100), nullable=False),
        sa.Column('submission_count', sa.Integer(), nullable=True),
        sa.Column('asset_count', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_deletion_logs_group_id', 'deletion_logs', ['group_id'])


def downgrade():
    """Revert migrations."""
    op.drop_table('deletion_logs')
    op.drop_table('group_free_time_results')
    op.drop_table('intervals')
    op.drop_table('submissions')
    op.drop_table('groups')
    op.execute("DROP TYPE submission_status")
