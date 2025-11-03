# Data Model: AI Agent Prompt Generator

**Created**: 2025-11-03
**Database**: PostgreSQL + pgvector

## Core Entities

### Session

Represents a complete prompt generation session with all agent interactions and user interventions.

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_input TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- active, waiting_for_user, processing, completed, failed, timeout
    final_prompt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    iteration_count INTEGER DEFAULT 0,
    user_intervention_count INTEGER DEFAULT 0,
    max_interventions INTEGER DEFAULT 3,
    waiting_for_user_since TIMESTAMP WITH TIME ZONE,
    current_question_id UUID,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX idx_sessions_waiting ON sessions(status, waiting_for_user_since) WHERE status = 'waiting_for_user';
```

### Agent Message

Individual messages from agents within a session.

```sql
CREATE TABLE agent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_type VARCHAR(20) NOT NULL, -- product_manager, technical_developer, team_lead
    message_content TEXT NOT NULL,
    message_type VARCHAR(20) NOT NULL, -- requirement, solution, review, approval, rejection
    sequence_number INTEGER NOT NULL,
    parent_message_id UUID REFERENCES agent_messages(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_time_ms INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_agent_messages_session_sequence ON agent_messages(session_id, sequence_number);
CREATE INDEX idx_agent_messages_agent_type ON agent_messages(agent_type);
```

### Conversation Context

Pre-computed context for agents to reference previous conversations.

```sql
CREATE TABLE conversation_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_type VARCHAR(20) NOT NULL,
    context_summary TEXT NOT NULL,
    key_points JSONB DEFAULT '[]'::jsonb,
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_count INTEGER DEFAULT 0
);

CREATE INDEX idx_conversation_contexts_session_agent ON conversation_contexts(session_id, agent_type);
```

### Session Metrics

Performance and usage metrics for sessions.

```sql
CREATE TABLE session_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    total_messages INTEGER DEFAULT 0,
    total_duration_seconds INTEGER,
    average_response_time_ms INTEGER,
    agent_message_counts JSONB DEFAULT '{}'::jsonb,
    user_satisfaction_rating INTEGER, -- 1-5 scale, nullable
    user_intervention_count INTEGER DEFAULT 0,
    clarifying_question_count INTEGER DEFAULT 0,
    total_waiting_time_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_session_metrics_session_id ON session_metrics(session_id);
```

### Supplementary User Input

Additional user input provided during active agent collaboration sessions.

```sql
CREATE TABLE supplementary_user_inputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    input_content TEXT NOT NULL,
    input_type VARCHAR(20) NOT NULL DEFAULT 'supplementary', -- supplementary, clarification_response
    provided_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_status VARCHAR(20) DEFAULT 'pending', -- pending, processed, failed
    incorporated_into_requirements BOOLEAN DEFAULT FALSE,
    sequence_number INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_supplementary_inputs_session ON supplementary_user_inputs(session_id, provided_at);
CREATE INDEX idx_supplementary_inputs_status ON supplementary_user_inputs(processing_status);
```

### Clarifying Questions

Questions from Product Manager agent to resolve ambiguous user input.

```sql
CREATE TABLE clarifying_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(20) NOT NULL, -- ambiguity, clarification, confirmation
    priority INTEGER DEFAULT 1, -- 1=high, 2=medium, 3=low
    asked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_deadline TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'pending', -- pending, answered, expired, cancelled
    response_text TEXT,
    responded_at TIMESTAMP WITH TIME ZONE,
    agent_type VARCHAR(20) DEFAULT 'product_manager',
    sequence_number INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_clarifying_questions_session ON clarifying_questions(session_id, asked_at);
CREATE INDEX idx_clarifying_questions_status ON clarifying_questions(status, response_deadline);
```

### Session Waiting States

Tracks waiting periods when system is paused for user input or responses.

```sql
CREATE TABLE session_waiting_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    waiting_type VARCHAR(20) NOT NULL, -- user_input, clarifying_question_response
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    status VARCHAR(20) DEFAULT 'active', -- active, resolved, timeout, cancelled
    related_entity_id UUID, -- ID of user_input or clarifying_question
    timeout_duration_seconds INTEGER DEFAULT 30,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_waiting_states_session ON session_waiting_states(session_id, started_at);
CREATE INDEX idx_waiting_states_status ON session_waiting_states(status, started_at);
```

## Entity Relationships

```
Session (1) ──── (N) Agent Messages
    │
    ├── (1) ──── (N) Conversation Contexts
    │
    ├── (1) ──── (1) Session Metrics
    │
    ├── (1) ──── (N) Supplementary User Inputs
    │
    ├── (1) ──── (N) Clarifying Questions
    │
    └── (1) ──── (N) Session Waiting States
```

## Data Validation Rules

### Session Validation
- `user_input`: Required, max 10,000 characters
- `status`: Must be one of: 'active', 'waiting_for_user', 'processing', 'completed', 'failed', 'timeout'
- `iteration_count`: Maximum 10 iterations (safety limit)
- `user_intervention_count`: Maximum 3 interventions per session
- `max_interventions`: Default 3, configurable per session

### Agent Message Validation
- `agent_type`: Must be one of: 'product_manager', 'technical_developer', 'team_lead'
- `message_type`: Must be one of: 'requirement', 'solution', 'review', 'approval', 'rejection'
- `sequence_number`: Must be sequential within session
- `message_content`: Required, max 50,000 characters

### Supplementary User Input Validation
- `input_content`: Required, max 10,000 characters
- `input_type`: Must be one of: 'supplementary', 'clarification_response'
- `processing_status`: Must be one of: 'pending', 'processed', 'failed'

### Clarifying Question Validation
- `question_text`: Required, max 5,000 characters
- `question_type`: Must be one of: 'ambiguity', 'clarification', 'confirmation'
- `priority`: Must be between 1-3 (1=high priority)
- `status`: Must be one of: 'pending', 'answered', 'expired', 'cancelled'

### Business Rules
- A session can have maximum 10 iterations (20 messages per agent type)
- Maximum 3 user interventions per session to prevent infinite loops
- Team Lead approval is required to complete a session
- Messages must reference parent messages for response threading
- Context summaries must be updated after every 3 messages
- User inputs are processed within 10 seconds (95% of cases)
- Clarifying questions expire after 30 seconds if not answered
- Maximum 3 clarifying questions per session to prevent analysis paralysis
- Waiting states cannot exceed 5 minutes total per session

## Vector Storage

### Message Embeddings

```sql
CREATE TABLE message_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES agent_messages(id) ON DELETE CASCADE,
    embedding vector(1536), -- GLM embedding vector size
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_message_embeddings_embedding ON message_embeddings USING ivfflat (embedding vector_cosine_ops);
```

### Context Search

Vector similarity search enables agents to find relevant previous messages:
- Semantic search within conversation history
- Context similarity across different sessions
- Pattern recognition for common prompt types

## State Transitions

### Session Lifecycle

```
[Created] → [Active] → [Completed]
    │           │           ↓
    │           ├──→ [Waiting for User] ────→ [Processing] ──┐
    │           │           ↑                        ↓   │
    │           │           └──────────────────────────┘   │
    │           ↓                                       ↓
    └───→ [Failed] ←───[Timeout]                       [Failed]
           ↑
    [Max Iterations Reached]
```

### User Intervention Flow

```
[Active Agent Collaboration]
           ↓
[User Supplementary Input]
           ↓
[Session Paused → Processing]
           ↓
[Requirements Updated]
           ↓
[Agent Collaboration Resumes]
```

### Clarifying Question Flow

```
[Ambiguous User Input Detected]
           ↓
[Product Manager Asks Question]
           ↓
[Session Paused for User Response]
           ↓
[User Provides Response]
           ↓
[Requirements Updated with Clarified Info]
           ↓
[Agent Collaboration Resumes]
```

### Agent Message Flow

```
Product Manager → Technical Developer → Team Lead
      ↑                                   ↓
      └─────── [Rejection] ←──────────────┘
                 ↓
           [Iteration Loop]
```

### Interactive State Machine

```
Active:
├── User Input → Waiting for User
├── Ambiguity Detected → Waiting for User
└── Team Lead Approval → Completed

Waiting for User:
├── User Input Received → Processing
├── User Response Received → Processing
├── Timeout → Failed
└── Max Interventions Reached → Completed

Processing:
├── Requirements Updated → Active
└── Processing Failed → Failed
```

## Performance Considerations

### Indexing Strategy
- Time-based indexes for historical queries
- Composite indexes for session-based lookups
- Vector indexes for semantic search

### Partitioning
- Sessions partitioned by created_at (monthly)
- Agent messages partitioned by session_id hash

### Caching Strategy
- Redis cache for active session contexts
- Materialized views for session statistics
- CDN caching for completed session data

## Data Retention

### Active Sessions
- Keep in Redis for 24 hours after completion
- Archive to PostgreSQL with immediate availability

### Historical Data
- Sessions retained for 1 year by default
- User-configurable retention policies
- Export functionality before deletion

### Cleanup Jobs
- Daily cleanup of timed-out sessions
- Weekly archive of old sessions
- Monthly vector embedding optimization