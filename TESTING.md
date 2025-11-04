# Testing and Validation Guide

This document provides comprehensive information about the testing framework and validation procedures for the AI Agent Prompt Generator system.

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Backend Testing](#backend-testing)
3. [Frontend Testing](#frontend-testing)
4. [Integration Testing](#integration-testing)
5. [System Validation](#system-validation)
6. [Running Tests](#running-tests)
7. [Test Coverage](#test-coverage)
8. [Continuous Integration](#continuous-integration)

## Testing Overview

The AI Agent Prompt Generator uses a multi-layered testing approach:

- **Unit Tests**: Test individual components and functions in isolation
- **Integration Tests**: Test component interactions and API endpoints
- **End-to-End Tests**: Test complete workflows and user scenarios
- **System Validation**: Comprehensive health checks and performance benchmarks

### Testing Pyramid

```
    🔺 E2E Tests (Critical paths only)
   /🔺\
  /🔺🔺\
 /🔺🔺🔺\
/🔺🔺🔺🔺\
🔺🔺🔺🔺🔺🔺
Unit Tests (Comprehensive)
```

## Backend Testing

### Structure

```
backend/
├── tests/
│   ├── test_glm_api.py              # GLM API client tests
│   ├── test_orchestration_engine.py # Agent orchestration tests
│   ├── test_api_endpoints.py       # API endpoint tests
│   ├── test_integration.py         # Integration tests
│   └── conftest.py                 # Test configuration
├── pytest.ini                      # Pytest configuration
└── requirements-dev.txt            # Testing dependencies
```

### Key Test Files

#### GLM API Tests (`test_glm_api.py`)
- ✅ API client initialization
- ✅ Request/response handling
- ✅ Error handling (auth, rate limits, server errors)
- ✅ Retry mechanism
- ✅ Response validation
- ✅ Rate limiting

#### Orchestration Engine Tests (`test_orchestration_engine.py`)
- ✅ Session lifecycle management
- ✅ Agent coordination
- ✅ Task status transitions
- ✅ Error handling and recovery
- ✅ Concurrent session processing
- ✅ Context building and sharing

#### API Endpoint Tests (`test_api_endpoints.py`)
- ✅ Session CRUD operations
- ✅ User input handling
- ✅ Message retrieval
- ✅ Request validation
- ✅ Error responses
- ✅ CORS and headers

### Running Backend Tests

```bash
# Navigate to backend directory
cd backend

# Install testing dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run specific test file
pytest tests/test_glm_api.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run with specific markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests
```

## Frontend Testing

### Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── __tests__/
│   │       ├── ConversationThread.test.tsx
│   │       ├── UserInputPanel.test.tsx
│   │       ├── AgentStatusPanel.test.tsx
│   │       └── MessageInputArea.test.tsx
│   ├── hooks/
│   │   └── __tests__/
│   │       └── useWebSocket.test.tsx
│   └── pages/
│       └── __tests__/
│           ├── Dashboard.test.tsx
│           └── ActiveSession.test.tsx
├── package.json
└── jest.config.js
```

### Key Test Files

#### Component Tests
- **ConversationThread**: Message rendering, interactions, scroll behavior
- **UserInputPanel**: Input handling, validation, voice input, history
- **AgentStatusPanel**: Agent status display, progress indicators
- **MessageInputArea**: Message composition, character limits

#### Hook Tests
- **useWebSocket**: Connection management, message handling, reconnection

### Running Frontend Tests

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage

# Run specific test file
npm test -- ConversationThread.test.tsx
```

## Integration Testing

### Integration Test Suite (`test_integration.py`)

Comprehensive integration tests covering:

#### API Integration
- ✅ Complete session workflow
- ✅ Error handling across endpoints
- ✅ Concurrent session management
- ✅ Pagination and filtering

#### WebSocket Integration
- ✅ Connection lifecycle
- ✅ Real-time message streaming
- ✅ Error handling and reconnection
- ✅ Session isolation

#### Agent Integration
- ✅ Agent collaboration workflow
- ✅ Error recovery mechanisms
- ✅ User input integration
- ✅ Context sharing

#### End-to-End Integration
- ✅ Full system integration
- ✅ Performance under load
- ✅ System resilience
- ✅ Data consistency

## System Validation

### Automated System Validator (`system_validation.py`)

A comprehensive validation tool that performs health checks on the entire system:

#### Validation Components

1. **API Health Check**
   - Endpoint availability
   - Response time measurements
   - Status code validation

2. **Database Connectivity**
   - Connection testing
   - CRUD operations
   - Data integrity verification

3. **GLM API Integration**
   - API connectivity
   - Message generation
   - Error handling

4. **Agent Orchestration**
   - Agent participation
   - Workflow progression
   - Task completion

5. **WebSocket Functionality**
   - Connection testing
   - Message exchange
   - Real-time updates

6. **End-to-End Workflow**
   - Complete session lifecycle
   - Performance measurement
   - Error recovery

7. **Performance Benchmarks**
   - Concurrent request handling
   - Response time analysis
   - Success rate metrics

8. **Error Handling**
   - Invalid input handling
   - HTTP error codes
   - Graceful degradation

9. **Security Validation**
   - Security headers
   - Information disclosure
   - Basic security measures

10. **Data Consistency**
    - CRUD consistency
    - Data integrity
    - Transaction safety

#### Running System Validation

```bash
# Run full system validation
python system_validation.py

# Run with custom base URL
python system_validation.py --base-url http://localhost:8080

# Run specific component validation
python system_validation.py --component api_health

# Generate custom report name
python system_validation.py --output my_validation_report.json
```

#### Validation Output

The validator generates:
- **Console Summary**: Real-time status updates
- **JSON Report**: Detailed results for CI/CD
- **Log File**: Complete validation log

Example output:
```
============================================================
SYSTEM VALIDATION SUMMARY
============================================================
Overall Status: EXCELLENT
Score: 92.5/100
Timestamp: 2024-01-01T10:00:00

Component Status:
----------------------------------------
api_health               : HEALTHY
database                 : CONNECTED
glm_api                  : INTEGRATED
agent_orchestration      : ORCHESTRATING
websocket                : CONNECTED
end_to_end_workflow      : COMPLETE
performance              : OPTIMAL
error_handling           : ROBUST
security                 : SECURE
data_consistency         : CONSISTENT
```

## Running Tests

### Prerequisites

1. **Backend Dependencies**
   ```bash
   cd backend
   pip install -r requirements-dev.txt
   ```

2. **Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   ```

3. **Database Setup**
   - PostgreSQL running and accessible
   - Test database created
   - Environment variables configured

4. **External Services**
   - GLM API credentials configured
   - WebSocket port available

### Full Test Suite

```bash
# Run backend tests
cd backend
pytest --cov=src --cov-report=html

# Run frontend tests
cd frontend
npm test -- --coverage --watchAll=false

# Run integration tests
cd backend
pytest tests/test_integration.py -v

# Run system validation
python system_validation.py
```

### Quick Development Tests

```bash
# Backend: Unit tests only
pytest -m unit -x

# Frontend: Component tests only
npm test -- --testPathPattern=__tests__/components/

# System: Health check only
python system_validation.py --component api_health
```

## Test Coverage

### Coverage Targets

- **Backend**: ≥ 80% line coverage
- **Frontend**: ≥ 75% line coverage
- **Integration**: Critical path coverage
- **E2E**: User journey coverage

### Coverage Reports

#### Backend Coverage
```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html to view detailed report
```

#### Frontend Coverage
```bash
npm test -- --coverage
# Open coverage/lcov-report/index.html to view detailed report
```

### Coverage Standards

- **Critical Components**: ≥ 90% coverage
- **Business Logic**: ≥ 85% coverage
- **Utility Functions**: ≥ 80% coverage
- **Error Handling**: ≥ 95% coverage

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements-dev.txt
      - name: Run tests
        run: |
          cd backend
          pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v1

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run tests
        run: |
          cd frontend
          npm test -- --coverage --watchAll=false

  system-validation:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    steps:
      - uses: actions/checkout@v2
      - name: Run system validation
        run: python system_validation.py
```

### Quality Gates

- **All tests must pass**
- **Coverage thresholds must be met**
- **System validation must score ≥ GOOD**
- **No critical security vulnerabilities**

## Best Practices

### Test Writing

1. **Arrange-Act-Assert Pattern**
   ```python
   def test_example():
       # Arrange
       setup_data = create_test_data()

       # Act
       result = function_under_test(setup_data)

       # Assert
       assert result.success is True
   ```

2. **Descriptive Test Names**
   ```python
   def test_agent_orchestration_handles_concurrent_sessions():
       # Clear what the test validates
   ```

3. **Test Data Management**
   ```python
   @pytest.fixture
   def sample_session():
       return {
           "id": "test-123",
           "user_input": "Test request"
       }
   ```

### Mock Usage

1. **Mock External Dependencies**
   ```python
   @patch('backend.src.services.glm_api.GLMClient')
   def test_with_mock_glm(mock_glm):
       mock_glm.return_value.complete.return_value = mock_response
   ```

2. **Avoid Over-Mocking**
   - Mock only external dependencies
   - Test real interactions between components
   - Use integration tests for component interaction

### Performance Testing

1. **Load Testing**
   ```python
   async def test_concurrent_requests():
       tasks = [make_request() for _ in range(100)]
       results = await asyncio.gather(*tasks)
       assert all(r.success for r in results)
   ```

2. **Benchmarking**
   ```python
   def test_api_response_time():
       start = time.time()
       response = make_api_call()
       duration = time.time() - start
       assert duration < 1.0  # 1 second max
   ```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify PostgreSQL is running
   - Check connection string
   - Ensure test database exists

2. **GLM API Failures**
   - Verify API credentials
   - Check rate limits
   - Mock for development if needed

3. **WebSocket Connection Issues**
   - Check port availability
   - Verify firewall settings
   - Test with WebSocket client

4. **Test Timeouts**
   - Increase timeout values
   - Check for infinite loops
   - Verify async/await usage

### Debug Mode

Enable debug logging:
```bash
# Backend
pytest --log-cli-level=DEBUG

# System Validation
python system_validation.py --verbose
```

## Contributing

When adding new features:

1. **Write tests first** (TDD approach)
2. **Achieve coverage targets**
3. **Update integration tests**
4. **Run system validation**
5. **Update documentation**

### Test Checklist

- [ ] Unit tests for new functions
- [ ] Integration tests for new endpoints
- [ ] Component tests for UI changes
- [ ] Update system validation if needed
- [ ] Documentation updated
- [ ] All tests passing locally
- [ ] Coverage thresholds met