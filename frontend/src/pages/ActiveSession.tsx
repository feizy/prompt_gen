import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
  Alert,
  Grid,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
  Button,
  Snackbar,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Refresh as RefreshIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
} from '@mui/icons-material';
import { useSelector, useDispatch } from 'react-redux';

import { RootState } from '../store';
import { clearCurrentSession } from '../store/slices/sessionSlice';
import { useWebSocketWithReconnect } from '../hooks/useWebSocket';

// Enhanced components
import ConversationThread from '../components/ConversationThread';
import UserInputPanel from '../components/UserInputPanel';
import AgentStatusPanel from '../components/AgentStatusPanel';

interface AgentMessage {
  id: string;
  agent_type: 'product_manager' | 'technical_developer' | 'team_lead';
  message_content: string;
  message_type: string;
  sequence_number: number;
  created_at: string;
  processing_time_ms: number | null;
}

interface ClarifyingQuestion {
  id: string;
  question_text: string;
  question_type: string;
  priority: number;
  asked_at: string;
  status: 'pending' | 'answered' | 'expired';
  response_text: string | null;
}

interface Session {
  id: string;
  user_input: string;
  status: string;
  final_prompt: string | null;
  created_at: string;
  updated_at: string;
  iteration_count: number;
  user_intervention_count: number;
  waiting_for_user_since: string | null;
}

const ActiveSession: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const dispatch = useDispatch();

  // WebSocket connection
  const {
    connected: wsConnected,
    connecting: wsConnecting,
    error: wsError,
    sendUserInput: wsSendUserInput,
    sendContinueWithoutInput: wsSendContinueWithoutInput,
    reconnectAttempts
  } = useWebSocketWithReconnect(sessionId, {
    onSessionStatus: (data) => {
      setSession(data);
    },
    onAgentMessage: (data) => {
      if (data.messages) {
        setMessages(prev => {
          // Merge new messages with existing ones, avoiding duplicates
          const existingIds = new Set(prev.map(m => m.id));
          const newMessages = data.messages.filter((m: AgentMessage) => !existingIds.has(m.id));
          return [...prev, ...newMessages].sort((a, b) => a.sequence_number - b.sequence_number);
        });
      } else if (data.message) {
        setMessages(prev => [...prev, data.message].sort((a, b) => a.sequence_number - b.sequence_number));
      }
    },
    onError: (data) => {
      setError(data.message);
    }
  });

  // Local state
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [questions, setQuestions] = useState<ClarifyingQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userInput, setUserInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchSessionData = async () => {
    if (!sessionId) return;

    try {
      setLoading(true);
      setError(null);

      // Fetch session details
      const sessionResponse = await fetch(`/v1/sessions/${sessionId}`);
      if (!sessionResponse.ok) {
        throw new Error('Session not found');
      }
      const sessionData = await sessionResponse.json();
      setSession(sessionData);

      // Fetch messages only if WebSocket is not connected
      if (!wsConnected) {
        const messagesResponse = await fetch(`/v1/sessions/${sessionId}/messages?limit=50`);
        if (messagesResponse.ok) {
          const messagesData = await messagesResponse.json();
          setMessages(messagesData.messages || []);
        }
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load session data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (sessionId) {
      fetchSessionData();

      return () => {
        dispatch(clearCurrentSession());
      };
    }
  }, [sessionId, dispatch]);

  const handleUserInput = async () => {
    if (!userInput.trim() || !sessionId || submitting) return;

    try {
      setSubmitting(true);

      // Send via WebSocket if connected, otherwise fall back to HTTP
      const success = wsConnected
        ? wsSendUserInput(userInput.trim(), 'supplementary')
        : await sendUserInputViaHTTP(userInput.trim());

      if (success) {
        setUserInput('');
        setSnackbarMessage('Input submitted successfully');
        setSnackbarOpen(true);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit input');
    } finally {
      setSubmitting(false);
    }
  };

  const sendUserInputViaHTTP = async (input: string): Promise<boolean> => {
    const response = await fetch(`/v1/sessions/${sessionId}/user-input`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        input_content: input,
        input_type: 'supplementary'
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to submit user input');
    }

    // Refresh session data after HTTP submission
    setTimeout(fetchSessionData, 1000);
    return true;
  };

  const handleContinueWithoutInput = async () => {
    if (!sessionId) return;

    try {
      setSubmitting(true);

      // Send via WebSocket if connected, otherwise fall back to HTTP
      const success = wsConnected
        ? wsSendContinueWithoutInput()
        : await continueViaHTTP();

      if (success) {
        setSnackbarMessage('Continuing without additional input');
        setSnackbarOpen(true);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to continue session');
    } finally {
      setSubmitting(false);
    }
  };

  const continueViaHTTP = async (): Promise<boolean> => {
    const response = await fetch(`/v1/sessions/${sessionId}/continue`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        force_continue: false
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to continue session');
    }

    // Refresh session data after HTTP submission
    setTimeout(fetchSessionData, 1000);
    return true;
  };

  const getAgentIcon = (agentType: string) => {
    switch (agentType) {
      case 'product_manager':
        return <PersonIcon />;
      case 'technical_developer':
        return <EngineerIcon />;
      case 'team_lead':
        return <LeadIcon />;
      default:
        return <PersonIcon />;
    }
  };

  const getAgentColor = (agentType: string) => {
    switch (agentType) {
      case 'product_manager':
        return 'info';
      case 'technical_developer':
        return 'success';
      case 'team_lead':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getAgentName = (agentType: string) => {
    switch (agentType) {
      case 'product_manager':
        return 'Product Manager';
      case 'technical_developer':
        return 'Technical Developer';
      case 'team_lead':
        return 'Team Lead';
      default:
        return 'Unknown Agent';
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
      case 'processing':
        return 'primary';
      case 'waiting_for_user_input':
        return 'warning';
      case 'completed':
        return 'success';
      case 'cancelled':
        return 'default';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getAgentStatusData = () => {
    const agentTypes = ['product_manager', 'technical_developer', 'team_lead'] as const;

    return agentTypes.map(type => {
      const agentMessages = messages.filter(m => m.agent_type === type);
      const lastMessage = agentMessages[agentMessages.length - 1];

      let status: 'idle' | 'thinking' | 'processing' | 'waiting' | 'completed' | 'error' = 'idle';
      let currentTask = '';

      if (session?.status === 'processing' && !lastMessage) {
        status = type === 'product_manager' ? 'thinking' : 'idle';
        currentTask = 'Preparing to analyze requirements';
      } else if (lastMessage) {
        if (session?.status === 'processing') {
          status = 'processing';
          currentTask = 'Working on next steps';
        } else if (session?.status === 'waiting_for_user_input') {
          status = 'waiting';
          currentTask = 'Waiting for user input';
        } else if (session?.status === 'completed') {
          status = 'completed';
          currentTask = 'Task completed';
        }
      }

      return {
        id: type,
        name: type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
        type,
        status,
        lastActivity: lastMessage?.created_at || new Date().toISOString(),
        messageCount: agentMessages.length,
        processingTime: lastMessage?.processing_time_ms || undefined,
        currentTask,
      };
    });
  };

  if (!sessionId) {
    return (
      <Container maxWidth="lg">
        <Alert severity="error" sx={{ mt: 2 }}>
          No session ID provided
        </Alert>
      </Container>
    );
  }

  if (loading) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <LinearProgress sx={{ mb: 2 }} />
          <Typography variant="h6">Loading session...</Typography>
        </Box>
      </Container>
    );
  }

  if (error && !session) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
          <Button
            variant="contained"
            startIcon={<BackIcon />}
            onClick={() => navigate('/dashboard')}
          >
            Back to Dashboard
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <IconButton onClick={() => navigate('/dashboard')}>
                <BackIcon />
              </IconButton>
              <Typography variant="h4" component="h1">
                Active Session
              </Typography>
              <IconButton onClick={fetchSessionData} disabled={loading}>
                <RefreshIcon />
              </IconButton>
              <Tooltip title={wsConnected ? 'WebSocket Connected' : `WebSocket Disconnected${reconnectAttempts > 0 ? ` (${reconnectAttempts} reconnect attempts)` : ''}`}>
                {wsConnected ? (
                  <WifiIcon color="success" />
                ) : (
                  <WifiOffIcon color={reconnectAttempts > 0 ? 'warning' : 'error'} />
                )}
              </Tooltip>
            </Box>

            {session && (
              <Box>
                <Typography variant="body1" color="text.secondary" paragraph>
                  <strong>Original Request:</strong> {session.user_input}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                  <Chip
                    label={session.status.replace('_', ' ')}
                    color={getStatusColor(session.status) as any}
                    size="small"
                  />
                  <Typography variant="caption" color="text.secondary">
                    Iteration {session.iteration_count} • {session.user_intervention_count} user inputs
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Started {new Date(session.created_at).toLocaleString()}
                  </Typography>
                  <Chip
                    label={wsConnected ? 'Real-time' : 'Polling'}
                    size="small"
                    color={wsConnected ? 'success' : 'warning'}
                    variant="outlined"
                  />
                </Box>
              </Box>
            )}
          </Box>
        </Box>

        {/* Main Content */}
        <Grid container spacing={3}>
          {/* Agent Conversation */}
          <Grid item xs={12} md={8}>
            <ConversationThread
              sessionId={sessionId!}
              messages={messages}
              loading={loading}
              onRefresh={fetchSessionData}
              onMarkAsRead={(messageId) => console.log('Marked as read:', messageId)}
              onMessageFeedback={(messageId, feedback) => console.log('Feedback:', messageId, feedback)}
              onCopyMessage={(content) => navigator.clipboard.writeText(content)}
            />
          </Grid>

          {/* Side Panel */}
          <Grid item xs={12} md={4}>
            <Stack spacing={2}>
              {/* Agent Status Panel */}
              <AgentStatusPanel
                agents={getAgentStatusData()}
                sessionId={sessionId!}
                overallStatus={session?.status || 'unknown'}
                onRefresh={fetchSessionData}
                onAgentClick={(agent) => console.log('Agent clicked:', agent)}
                compact={false}
                showDetails={true}
              />

              {/* Final Prompt */}
              {session?.final_prompt && (
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CheckIcon color="success" />
                      Final Prompt
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 2, maxHeight: 200, overflow: 'auto' }}>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {session.final_prompt}
                      </Typography>
                    </Paper>
                  </CardContent>
                </Card>
              )}

              {/* Pending Questions */}
              {questions.filter(q => q.status === 'pending').length > 0 && (
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Badge badgeContent={questions.filter(q => q.status === 'pending').length} color="warning">
                        <QuestionIcon />
                      </Badge>
                      Pending Questions
                    </Typography>
                    <Stack spacing={1}>
                      {questions.filter(q => q.status === 'pending').map((question) => (
                        <Paper key={question.id} variant="outlined" sx={{ p: 1 }}>
                          <Typography variant="body2">
                            {question.question_text}
                          </Typography>
                        </Paper>
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              )}
            </Stack>
          </Grid>
        </Grid>

        {/* User Input Section */}
        {session?.status === 'waiting_for_user_input' && (
          <UserInputPanel
            sessionId={sessionId!}
            disabled={submitting}
            onSubmit={async (input, type) => {
              const success = wsConnected
                ? wsSendUserInput(input, type)
                : await sendUserInputViaHTTP(input);
              if (success) {
                setSnackbarMessage('Input submitted successfully');
                setSnackbarOpen(true);
              }
              return success;
            }}
            onContinueWithoutInput={async () => {
              const success = wsConnected
                ? wsSendContinueWithoutInput()
                : await continueViaHTTP();
              if (success) {
                setSnackbarMessage('Continuing without additional input');
                setSnackbarOpen(true);
              }
              return success;
            }}
            placeholder="The agents need more information to continue. Please provide additional details or clarification..."
            suggestions={[
              "Can you provide more specific requirements?",
              "What are the key constraints or limitations?",
              "Are there any specific technologies or frameworks to consider?",
              "What would be the ideal format for the final output?"
            ]}
            isLoading={submitting}
            characterLimit={2000}
            showShortcuts={true}
          />
        )}

        {/* Error Display */}
        {error && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* WebSocket Connection Status */}
        {wsError && (
          <Alert severity="warning" sx={{ mt: 2 }} onClose={() => {}}>
            WebSocket connection error: {wsError}. Falling back to polling.
          </Alert>
        )}

        {/* Snackbar for user feedback */}
        <Snackbar
          open={snackbarOpen}
          autoHideDuration={3000}
          onClose={() => setSnackbarOpen(false)}
          message={snackbarMessage}
        />
      </Box>
    </Container>
  );
};

export default ActiveSession;