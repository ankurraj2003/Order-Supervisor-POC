
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Supervisors table
    op.create_table(
        'supervisors',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('base_instruction', sa.Text(), nullable=False),
        sa.Column('available_actions', JSONB(), nullable=False, server_default='[]'),
        sa.Column('default_wake_behavior', JSONB(), nullable=True),
        sa.Column('model_config', JSONB(), nullable=True),
        sa.Column('wake_guidance', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Runs table
    op.create_table(
        'runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('supervisor_id', UUID(as_uuid=True), sa.ForeignKey('supervisors.id'), nullable=False),
        sa.Column('order_id', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='running'),
        sa.Column('state', JSONB(), nullable=False, server_default='{}'),
        sa.Column('wake_guidance', sa.Text(), nullable=True),
        sa.Column('additional_instructions', ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('next_wake_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('max_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('final_summary', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Activities table
    op.create_table(
        'activities',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('subtype', sa.String(100), nullable=True),
        sa.Column('content', JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Indexes
    op.create_index('ix_runs_status', 'runs', ['status'])
    op.create_index('ix_runs_order_id', 'runs', ['order_id'])
    op.create_index('ix_activities_run_id', 'activities', ['run_id'])
    op.create_index('ix_activities_type', 'activities', ['type'])
    op.create_index('ix_activities_created_at', 'activities', ['created_at'])


def downgrade() -> None:
    op.drop_table('activities')
    op.drop_table('runs')
    op.drop_table('supervisors')

