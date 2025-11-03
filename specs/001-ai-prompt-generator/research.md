# Technology Research: AI Agent Prompt Generator

**Created**: 2025-11-03
**Purpose**: Resolve technical decisions for implementation planning

## Backend Language & Framework

**Decision**: Python 3.11+ with FastAPI

**Rationale**:
- Python has the most mature ecosystem for AI/ML development
- FastAPI provides excellent async support for real-time features
- Strong integration with LangChain and other AI frameworks
- Built-in API documentation and validation
- Extensive WebSocket support for real-time communication

**Alternatives considered**:
- Node.js + Express: Good real-time support but less mature AI ecosystem
- Go + Gin: Excellent performance but limited AI framework support

## AI Agent Orchestration Framework

**Decision**: Custom implementation using GLM API + LangChain

**Rationale**:
- LangChain provides robust agent orchestration primitives
- Custom implementation allows fine-tuned control over agent roles and communication
- GLM API provides reliable LLM capabilities
- Direct control over conversation context management
- Easier debugging and monitoring compared to black-box solutions

**Alternatives considered**:
- Microsoft AutoGen: Powerful but complex for simple three-agent use case
- CrewAI: Specialized for agent teams but less flexible for custom workflows

## Database Solution

**Decision**: PostgreSQL + pgvector for vector storage

**Rationale**:
- PostgreSQL provides strong consistency for conversation threading
- pgvector enables vector similarity search for conversation context
- Excellent support for time-series data with proper indexing
- Mature ecosystem with strong backup and recovery tools
- JSONB support for flexible agent message storage

**Alternatives considered**:
- MongoDB + ChromaDB: Flexible schema but complex consistency management
- SQLite + Faiss: Simple but limited scalability for concurrent users

## Testing Framework

**Decision**: pytest + async test patterns + mock agents

**Rationale**:
- pytest provides excellent async testing support
- Mock agents enable deterministic testing without API calls
- Integration tests can use real LLM APIs in isolated environments
- Strong parameterized testing for different conversation scenarios
- Easy CI/CD integration with GitHub Actions

**Alternatives considered**:
- unittest: Built-in but less feature-rich for async testing
- Playwright: Excellent for E2E testing but overkill for agent logic

## Deployment Platform

**Decision**: Docker containers with cloud hosting (AWS/GCP)

**Rationale**:
- Containerization ensures consistent environments
- Easy horizontal scaling for concurrent users
- Simplified dependency management for AI frameworks
- Support for GPU instances if needed for future local models
- Managed database services for reliability

**Alternatives considered**:
- Serverless (AWS Lambda): Cold start issues problematic for real-time features
- Traditional VPS: More manual management and scaling

## Performance Requirements

**Decision**:
- Message display: <2 seconds (98% of cases)
- Total generation time: <3 minutes
- Concurrent users: 100 simultaneous sessions
- Session storage: 10,000 historical sessions

**Rationale**: Based on success criteria SC-006, SC-001, and estimated usage patterns

**Constraints**:
- LLM API rate limits: Implement exponential backoff and request queuing
- Cost management: Implement session limits and cost monitoring
- Timeout handling: Maximum 5 iterations per conversation with 30-second per agent timeout

## Real-time Communication

**Decision**: WebSocket with fallback to Server-Sent Events

**Rationale**:
- WebSocket provides bidirectional communication for full interactivity
- SSE fallback for environments with WebSocket restrictions
- Easy implementation with FastAPI's WebSocket support
- Natural reconnection handling and error recovery

## Frontend Framework

**Decision**: React with TypeScript

**Rationale**:
- Strong ecosystem for real-time dashboards
- TypeScript provides type safety for API integration
- Excellent WebSocket client libraries
- Component-based architecture fits well with agent conversation UI
- Strong testing support with React Testing Library

## Scale and Storage Requirements

**Decision**:
- Short-term storage: Redis for active session caching
- Long-term storage: PostgreSQL with partitioning by date
- File storage: Cloud storage for any generated files
- Search: Full-text search on conversation content

**Architecture**:
- Horizontal scaling through stateless API servers
- Session affinity not required with external Redis cache
- Database read replicas for historical data access
- CDN for static frontend assets

## Interactive User Input System

**Decision**: WebSocket-based bidirectional communication with session state management

**Rationale**:
- WebSocket enables real-time bidirectional communication for user inputs during active sessions
- Session state management ensures proper pause/resume functionality
- Event-driven architecture handles user input processing and system responses
- Redis-based session state persistence across server restarts
- Proper queuing mechanisms prevent input conflicts during agent processing

**Key Components**:
- User input queue for processing supplementary inputs
- Session state machine for managing pause/resume cycles
- Event-driven architecture for real-time UI updates
- Conflict resolution for simultaneous user inputs

**Alternatives considered**:
- HTTP polling: Higher latency and less responsive user experience
- Long polling: Complex implementation and scalability issues

## Clarifying Question System

**Decision**: Agent-initiated clarifying questions with user response handling

**Rationale**:
- Product Manager agent can detect ambiguity and initiate clarification requests
- Structured question format ensures consistent user experience
- Question prioritization handles multiple ambiguities efficiently
- User response processing integrates seamlessly with conversation flow
- Timeout handling prevents infinite waiting states

**Key Features**:
- Automatic ambiguity detection in user input
- Question prioritization based on impact on requirements generation
- Response validation and conflict resolution
- Integration with conversation context management
- Visual indicators for question/response status

**Performance Considerations**:
- Question generation within 5 seconds of ambiguity detection
- Response processing within 3 seconds of user submission
- Maximum 3 clarifying questions per session to prevent analysis paralysis

## Enhanced Session State Management

**Decision**: Complex state machine with waiting states and intervention tracking

**Rationale**:
- Session must support multiple states: active, waiting_for_user, processing, completed
- Intervention limits prevent infinite user input cycles (maximum 3 per session)
- State persistence ensures session recovery across server restarts
- Proper cleanup of waiting states prevents resource leaks

**State Transitions**:
- active → waiting_for_user (user input requested)
- waiting_for_user → processing (user input received)
- processing → active (requirements updated, collaboration resumes)
- active → waiting_for_user (clarifying questions asked)
- waiting_for_user → completed (maximum interventions reached)

**Safety Mechanisms**:
- Maximum 3 user interventions per session
- 30-second timeout for user responses
- Automatic session completion after 5 total iterations
- Conflict resolution for contradictory user inputs

## Enhanced Real-time Communication

**Decision**: Multi-channel WebSocket architecture with message type routing

**Rationale**:
- Separate channels for agent messages, user inputs, and system notifications
- Message type routing ensures proper frontend handling
- Priority queuing for critical system messages
- Back-pressure prevention for high-frequency updates

**Communication Channels**:
- agent_messages: Agent dialogue updates
- user_inputs: User supplementary inputs
- clarifying_questions: Agent questions to users
- system_status: Waiting states, errors, completion notifications

**Performance Optimizations**:
- Message batching for high-frequency updates
- Selective message broadcasting to reduce client load
- Compression for large message payloads
- Connection pooling for WebSocket management