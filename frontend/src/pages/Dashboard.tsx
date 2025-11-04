import React, { useEffect, useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Button,
  Paper,
  Grid,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Alert,
  IconButton,
  Tooltip,
  Badge,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  History as HistoryIcon,
  Add as AddIcon,
  Refresh as RefreshIcon,
  Launch as LaunchIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  Error as ErrorIcon,
  Notifications as NotificationsIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';

import { openModal } from '../store/slices/uiSlice';
import { RootState } from '../store';
import { useWebSocket } from '../hooks/useWebSocket';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  // Global WebSocket connection for notifications
  const { connected: wsConnected } = useWebSocket(null, {
    onSessionCreated: (data) => {
      // When a new session is created, refresh the active sessions list
      fetchActiveSessions();
    },
    onSessionStatus: (data) => {
      // When session status changes, update the active sessions list
      if (data.status === 'active' || data.status === 'processing' || data.status === 'waiting_for_user_input') {
        fetchActiveSessions();
      }
    }
  });

  // Local state for active sessions
  const [activeSessions, setActiveSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleCreateSession = () => {
    dispatch(openModal('createSession'));
  };

  const fetchActiveSessions = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch all sessions with statuses that should be shown as "active"
      const response = await fetch('/v1/sessions?page=1&page_size=10&status=active,processing,waiting_for_user_input');
      if (!response.ok) {
        throw new Error('Failed to fetch active sessions');
      }

      const data = await response.json();
      setActiveSessions(data.sessions || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActiveSessions();

    // Set up polling as fallback when WebSocket is not connected
    if (!wsConnected) {
      const interval = setInterval(fetchActiveSessions, 10000); // Update every 10 seconds
      return () => clearInterval(interval);
    }
  }, [wsConnected]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
      case 'processing':
        return <ScheduleIcon color="primary" />;
      case 'waiting_for_user_input':
        return <PlayArrowIcon color="warning" />;
      case 'completed':
        return <CheckIcon color="success" />;
      case 'cancelled':
        return <CancelIcon color="default" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      default:
        return <ScheduleIcon color="action" />;
    }
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

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  };

  const truncateText = (text: string, maxLength: number = 100) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mb: 2 }}>
          <Box>
            <Typography variant="h3" component="h1" gutterBottom>
              AI Agent Prompt Generator
            </Typography>
            <Typography variant="h6" color="text.secondary" paragraph>
              Create detailed LLM prompts through collaborative AI agents
            </Typography>
          </Box>
          <Tooltip title={wsConnected ? 'Real-time updates enabled' : 'Real-time updates disabled'}>
            <Badge badgeContent="🔴" invisible={!wsConnected}>
              <NotificationsIcon color={wsConnected ? 'success' : 'action'} />
            </Badge>
          </Tooltip>
        </Box>

        <Grid container spacing={3} sx={{ mt: 2 }}>
          {/* Action Cards */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  Create New Session
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Start a new prompt generation session with our AI agents
                </Typography>
                <Button
                  variant="contained"
                  size="large"
                  onClick={handleCreateSession}
                  fullWidth
                  startIcon={<AddIcon />}
                >
                  Create Session
                </Button>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  View History
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Browse and search previous prompt generation sessions
                </Typography>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={() => navigate('/history')}
                  fullWidth
                  startIcon={<HistoryIcon />}
                >
                  View History
                </Button>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  Active Sessions
                </Typography>
                <Typography variant="h4" color="primary" paragraph>
                  {activeSessions.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Currently running
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <Button
                    variant="text"
                    size="small"
                    onClick={fetchActiveSessions}
                    startIcon={<RefreshIcon />}
                    disabled={loading}
                  >
                    Refresh
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Active Sessions */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h5" component="h2">
                  Active Sessions
                </Typography>
                <IconButton onClick={fetchActiveSessions} disabled={loading}>
                  <RefreshIcon />
                </IconButton>
              </Box>

              {loading && <LinearProgress sx={{ mb: 2 }} />}

              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              {!loading && !error && activeSessions.length === 0 && (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography variant="body1" color="text.secondary" paragraph>
                    No active sessions found
                  </Typography>
                  <Button
                    variant="contained"
                    onClick={handleCreateSession}
                    startIcon={<AddIcon />}
                  >
                    Create Your First Session
                  </Button>
                </Box>
              )}

              {!loading && !error && activeSessions.length > 0 && (
                <Grid container spacing={2}>
                  {activeSessions.map((session) => (
                    <Grid item xs={12} md={6} lg={4} key={session.id}>
                      <Card
                        sx={{
                          cursor: 'pointer',
                          transition: 'transform 0.2s, box-shadow 0.2s',
                          '&:hover': {
                            transform: 'translateY(-2px)',
                            boxShadow: 3,
                          },
                        }}
                        onClick={() => navigate(`/session/${session.id}`)}
                      >
                        <CardContent>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              {getStatusIcon(session.status)}
                              <Chip
                                label={session.status.replace('_', ' ')}
                                color={getStatusColor(session.status) as any}
                                size="small"
                              />
                            </Box>
                            <Tooltip title="Open Session">
                              <IconButton size="small">
                                <LaunchIcon />
                              </IconButton>
                            </Tooltip>
                          </Box>

                          <Typography variant="body1" sx={{ mb: 1, fontWeight: 'medium' }}>
                            {truncateText(session.user_input)}
                          </Typography>

                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
                            <Typography variant="caption" color="text.secondary">
                              {formatTime(session.created_at)}
                            </Typography>

                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              {session.pending_questions_count > 0 && (
                                <Chip
                                  label={`${session.pending_questions_count} questions`}
                                  color="warning"
                                  size="small"
                                  variant="outlined"
                                />
                              )}
                              {session.latest_agent && (
                                <Chip
                                  label={session.latest_agent.replace('_', ' ')}
                                  size="small"
                                  variant="outlined"
                                />
                              )}
                            </Box>
                          </Box>

                          <Box sx={{ mt: 2 }}>
                            <Typography variant="caption" color="text.secondary">
                              Iteration {session.iteration_count} • {session.user_intervention_count} user inputs
                            </Typography>
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              )}
            </Paper>
          </Grid>

          {/* How It Works */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  How It Works
                </Typography>
                <Typography variant="body1" paragraph>
                  Our system uses three specialized AI agents working together:
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="h6" color="primary" gutterBottom>
                        📋 Product Manager
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Analyzes your requirements and creates detailed product specifications
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="h6" color="primary" gutterBottom>
                        💻 Technical Developer
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Designs technical solutions and implementation approaches
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="h6" color="primary" gutterBottom>
                        👨‍💼 Team Lead
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Reviews and approves the final prompt, ensuring quality and completeness
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                  Watch the agents collaborate in real-time and provide additional input or clarification as needed.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </Container>
  );
};

export default Dashboard;