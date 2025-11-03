"""Initial schema with all core tables

Revision ID: 001
Revises:
Create Date: 2025-11-03 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create sessions table
    op.create_table('sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_input', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('final_prompt', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('iteration_count', sa.Integer(), nullable=True),
        sa.Column('user_intervention_count', sa.Integer(), nullable=True),
        sa.Column('max_interventions', sa.Integer(), nullable=True),
        sa.Column('waiting_for_user_since', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_question_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sessions_status', 'sessions', ['status'], unique=False)
    op.create_index('idx_sessions_created_at', 'sessions', ['created_at'], unique=False)
    op.create_index('idx_sessions_waiting', 'sessions', ['status', 'waiting_for_user'], unique=False, postgresql_where=sa.text("status = 'waiting_for_user'"))

    # Create agent_messages table
    op.create_table('agent_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.String(length=20), nullable=False),
        sa.Column('message_content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(length=20), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('parent_message_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['parent_message_id'], ['agent_messages.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_agent_messages_session_sequence', 'agent_messages', ['session_id', 'sequence_number'], unique=False)
    op.create_index('idx_agent_messages_agent_type', 'agent_messages', ['agent_type'], unique=False)

    # Create conversation_contexts table
    op.create_table('conversation_contexts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.String(length=20), nullable=False),
        sa.Column('context_summary', sa.Text(), nullable=False),
        sa.Column('key_points', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_conversation_contexts_session_agent', 'conversation_contexts', ['session_id', 'agent_type'], unique=False)

    # Create session_metrics table
    op.create_table('session_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('total_messages', sa.Integer(), nullable=True),
        sa.Column('total_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('average_response_time_ms', sa.Integer(), nullable=True),
        sa.Column('agent_message_counts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('user_satisfaction_rating', sa.Integer(), nullable=True),
        sa.Column('user_intervention_count', sa.Integer(), nullable=True),
        sa.Column('clarifying_question_count', sa.Integer(), nullable=True),
        sa.Column('total_waiting_time_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_session_metrics_session_id', 'session_metrics', ['session_id'], unique=False)

    # Create supplementary_user_inputs table
    op.create_table('supplementary_user_inputs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('input_content', sa.Text(), nullable=False),
        sa.Column('input_type', sa.String(length=20), nullable=False),
        sa.Column('provided_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('processing_status', sa.String(length=20), nullable=True),
        sa.Column('incorporated_into_requirements', sa.Boolean(), nullable=True),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_supplementary_inputs_session', 'supplementary_user_inputs', ['session_id', 'provided_at'], unique=False)
    op.create_index('idx_supplementary_inputs_status', 'supplementary_user_inputs', ['processing_status'], unique=False)

    # Create clarifying_questions table
    op.create_table('clarifying_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=20), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('asked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('response_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('agent_type', sa.String(length=20), nullable=True),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_clarifying_questions_session', 'clarifying_questions', ['session_id', 'asked_at'], unique=False)
    op.create_index('idx_clarifying_questions_status', 'clarifying_questions', ['status', 'response_deadline'], unique=False)

    # Create session_waiting_states table
    op.create_table('session_waiting_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('waiting_type', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('related_entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('timeout_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_waiting_states_session', 'session_waiting_states', ['session_id', 'started_at'], unique=False)
    op.create_index('idx_waiting_states_status', 'session_waiting_states', ['status', 'started_at'], unique=False)

    # Create message_embeddings table
    op.create_table('message_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('embedding', postgresql.Vector(dim=1536), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['message_id'], ['agent_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_message_embeddings_embedding', 'message_embeddings', ['embedding'], unique=False, postgresql_using='ivfflat', postgresql_with={'index_type': 'vector_cosine_ops'})


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_index('idx_message_embeddings_embedding', table_name='message_embeddings')
    op.drop_table('message_embeddings')
    op.drop_index('idx_waiting_states_status', table_name='session_waiting_states')
    op.drop_index('idx_waiting_states_session', table_name='session_waiting_states')
    op.drop_table('session_waiting_states')
    op.drop_index('idx_clarifying_questions_status', table_name='clarifying_questions')
    op.drop_index('idx_clarifying_questions_session', table_name='clarifying_questions')
    op.drop_table('clarifying_questions')
    op.drop_index('idx_supplementary_inputs_status', table_name='supplementary_user_inputs')
    op.drop_index('idx_supplementary_inputs_session', table_name='supplementary_user_inputs')
    op.drop_table('supplementary_user_inputs')
    op.drop_index('idx_session_metrics_session_id', table_name='session_metrics')
    op.drop_table('session_metrics')
    op.drop_index('idx_conversation_contexts_session_agent', table_name='conversation_contexts')
    op.drop_table('conversation_contexts')
    op.drop_index('idx_agent_messages_agent_type', table_name='agent_messages')
    op.drop_index('idx_agent_messages_session_sequence', table_name='agent_messages')
    op.drop_table('agent_messages')
    op.drop_index('idx_sessions_waiting', table_name='sessions')
    op.drop_index('idx_sessions_created_at', table_name='sessions')
    op.drop_index('idx_sessions_status', table_name='sessions')
    op.drop_table('sessions')

    # Drop pgvector extension
    op.execute('DROP EXTENSION IF EXISTS vector')