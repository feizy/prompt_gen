# Quickstart Guide: AI Agent Prompt Generator

**Version**: 1.0.0
**Last Updated**: 2025-11-03

## Overview

The AI Agent Prompt Generator enables users to create detailed, high-quality prompts for LLMs through a collaborative process involving three specialized AI agents: Product Manager, Technical Developer, and Team Lead. The system includes interactive features that allow users to provide supplementary input during active sessions and respond to clarifying questions from agents.

## Prerequisites

### Development Environment

```bash
# Python 3.11+ required
python --version

# PostgreSQL 14+ with pgvector extension
psql --version

# Redis 6+ for session caching
redis-server --version

# Node.js 18+ (for frontend development)
node --version
```

### Environment Variables

```bash
# Backend (.env)
DATABASE_URL=postgresql://user:password@localhost/promptgen
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...
JWT_SECRET=your-secret-key
LOG_LEVEL=info

# Frontend (.env)
REACT_APP_API_URL=http://localhost:8000/v1
REACT_APP_WS_URL=ws://localhost:8000/ws
```

## Installation

### Backend Setup

```bash
# Clone repository
git clone <repository-url>
cd prompt-gen

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Database setup
createdb promptgen
psql promptgen -c "CREATE EXTENSION IF NOT EXISTS vector;"
alembic upgrade head

# Start backend server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Install dependencies
cd frontend
npm install

# Start development server
npm start
```

## Basic Usage

### 1. Create a Session

```bash
curl -X POST http://localhost:8000/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "I want to create a chatbot for customer service that can handle common inquiries and escalate complex issues."
  }'
```

Response:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_input": "I want to create a chatbot for customer service...",
  "status": "active",
  "iteration_count": 0,
  "created_at": "2025-11-03T10:00:00Z",
  "updated_at": "2025-11-03T10:00:00Z",
  "final_prompt": null
}
```

### 2. Start Agent Collaboration

```bash
curl -X POST http://localhost:8000/v1/sessions/123e4567-e89b-12d3-a456-426614174000/start
```

### 3. Monitor Real-time Progress

Connect to WebSocket:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/sessions/123e4567-e89b-12d3-a456-426614174000');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('New message:', data);
};
```

### 4. Interactive Features

#### Adding Supplementary User Input

```bash
curl -X POST http://localhost:8000/v1/sessions/123e4567-e89b-12d3-a456-426614174000/user-input \
  -H "Content-Type: application/json" \
  -d '{
    "input_content": "Please also include multi-language support in the chatbot requirements",
    "input_type": "supplementary"
  }'
```

Response:
```json
{
  "id": "input-uuid-123",
  "processing_status": "pending",
  "message": "Processing your supplementary input...",
  "estimated_processing_time": 5,
  "session_status": {
    "status": "processing",
    "current_iteration": 3
  }
}
```

#### Responding to Clarifying Questions

First, check for pending questions:
```bash
curl "http://localhost:8000/v1/sessions/123e4567-e89b-12d3-a456-426614174000/clarifying-questions?status=pending"
```

Response:
```json
{
  "questions": [
    {
      "id": "question-uuid-456",
      "question_text": "Could you clarify what specific platforms the chatbot should support?",
      "question_type": "clarification",
      "priority": 1,
      "status": "pending",
      "response_deadline": "2025-11-03T10:05:00Z"
    }
  ],
  "total": 1,
  "has_pending": true
}
```

Respond to the question:
```bash
curl -X POST http://localhost:8000/v1/sessions/123e4567-e89b-12d3-a456-426614174000/clarifying-questions/question-uuid-456/response \
  -H "Content-Type: application/json" \
  -d '{
    "response_text": "The chatbot should support web, mobile app, and email platforms"
  }'
```

### 5. Get Final Result

```bash
curl http://localhost:8000/v1/sessions/123e4567-e89b-12d3-a456-426614174000
```

## Web Interface

Access the web interface at `http://localhost:3000`:

1. **Dashboard**: View active sessions and create new ones
2. **Active Session**: Watch real-time agent conversations and participate with interactive features
3. **History**: Browse and search previous sessions with complete interaction history
4. **Analytics**: View usage statistics and performance metrics
5. **User Input Panel**: Provide supplementary input during active sessions
6. **Clarifying Questions**: View and respond to questions from agents

## Testing

### Backend Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/contract/

# Run with coverage
pytest --cov=backend --cov-report=html
```

### Frontend Tests

```bash
# Run unit tests
npm test

# Run E2E tests
npm run test:e2e
```

## Common Workflows

### Creating a Complex Prompt with Interactive Features

1. **Input**: Describe your requirements in detail
2. **Agent Process**: Watch as agents collaborate to refine requirements
3. **Interactive Input**: Provide supplementary input when you think of additional requirements
4. **Clarification**: Respond to clarifying questions from the Product Manager
5. **Iteration**: Review agent feedback and wait for consensus
6. **Result**: Receive a comprehensive, well-structured prompt

### Interactive Session Management

```bash
# Create session
curl -X POST http://localhost:8000/v1/sessions -d '{"user_input": "..."}'

# Start collaboration
curl -X POST http://localhost:8000/v1/sessions/{id}/start

# Add supplementary input during collaboration
curl -X POST http://localhost:8000/v1/sessions/{id}/user-input \
  -d '{"input_content": "Additional requirements...", "input_type": "supplementary"}'

# Check for clarifying questions
curl "http://localhost:8000/v1/sessions/{id}/clarifying-questions?status=pending"

# Respond to clarifying question
curl -X POST http://localhost:8000/v1/sessions/{id}/clarifying-questions/{questionId}/response \
  -d '{"response_text": "Your answer..."}'
```

### Managing Sessions

```bash
# List all sessions
curl http://localhost:8000/v1/sessions

# Get session details with messages and interactions
curl http://localhost:8000/v1/sessions/{id}/messages

# Get clarifying questions for a session
curl http://localhost:8000/v1/sessions/{id}/clarifying-questions

# Cancel an active session
curl -X DELETE http://localhost:8000/v1/sessions/{id}
```

### Historical Analysis

```bash
# Search historical sessions
curl "http://localhost:8000/v1/history?query=chatbot&date_from=2025-11-01"

# Filter by session status
curl "http://localhost:8000/v1/sessions?status=completed&limit=50"
```

### WebSocket Integration

```javascript
// Connect to real-time updates
const ws = new WebSocket('ws://localhost:8000/ws/sessions/{sessionId}');

// Handle different message types
ws.onmessage = function(event) {
  const data = JSON.parse(event.data);

  switch(data.type) {
    case 'agent_message':
      console.log('Agent:', data.agent_type, '-', data.content);
      break;
    case 'clarifying_question':
      console.log('Question:', data.question_text);
      showQuestionDialog(data);
      break;
    case 'waiting_for_user':
      console.log('System waiting for user input');
      showWaitingIndicator();
      break;
    case 'session_status':
      console.log('Status:', data.status);
      updateSessionStatus(data);
      break;
  }
};
```

## Troubleshooting

### Common Issues

1. **Agents not responding**: Check GLM API key and rate limits
2. **WebSocket connection issues**: Verify backend server is running
3. **Database connection errors**: Check DATABASE_URL configuration
4. **Slow performance**: Monitor Redis cache hit rate and database query performance
5. **User input not being processed**: Check session status is not 'waiting_for_user'
6. **Clarifying questions not appearing**: Ensure Product Manager agent is active and detects ambiguity
7. **Session timeout during waiting**: Check user response timeout settings (default 30 seconds)
8. **Maximum interventions reached**: System limits user interventions to 3 per session

### Health Check

```bash
curl http://localhost:8000/v1/health
```

### Logs

```bash
# Backend logs
tail -f backend/logs/app.log

# Database queries
tail -f backend/logs/db.log

# Agent interactions
tail -f backend/logs/agents.log
```

## Performance Tuning

### Database Optimization

```sql
-- Create indexes for better query performance
CREATE INDEX CONCURRENTLY idx_sessions_created_at_desc
ON sessions(created_at DESC);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM sessions
WHERE status = 'completed'
ORDER BY created_at DESC LIMIT 20;
```

### Caching Strategy

```python
# Configure Redis session caching
SESSION_CACHE_TTL = 3600  # 1 hour
CONTEXT_CACHE_TTL = 1800  # 30 minutes
```

### Rate Limiting

```python
# Configure API rate limits
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 3600  # 1 hour
```

## Deployment

### Docker Deployment

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check service health
docker-compose ps
```

### Environment Configuration

Production environment requires:
- HTTPS certificates
- Database backups
- Monitoring and alerting
- Load balancing for high availability

## API Documentation

Full API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI Spec: `http://localhost:8000/openapi.json`

## Support

For issues and questions:
1. Check logs for error messages
2. Review this quickstart guide
3. Consult the API documentation
4. Check health endpoints for service status