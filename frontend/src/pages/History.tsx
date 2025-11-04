import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Chip,
  LinearProgress,
  Alert,
  IconButton,
  Tooltip,
  TextField,
  Grid,
  Card,
  CardContent,
  Pagination,
  Fab,
  InputAdornment,
} from '@mui/material';
import {
  Search as SearchIcon,
  Visibility as ViewIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  Launch as LaunchIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material';
import { useDispatch } from 'react-redux';

import { openModal } from '../store/slices/uiSlice';

interface Session {
  id: string;
  user_input: string;
  status: string;
  final_prompt: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  iteration_count: number;
  user_intervention_count: number;
}

const History: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  // State
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const pageSize = 20;

  const fetchSessions = async (currentPage: number = 1) => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: pageSize.toString(),
      });

      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }

      const response = await fetch(`/v1/sessions?${params}`);
      if (!response.ok) {
        throw new Error('Failed to fetch sessions');
      }

      const data = await response.json();
      setSessions(data.sessions || []);
      setTotalPages(Math.ceil(data.total_count / pageSize));

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions(page);
  }, [page, statusFilter]);

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  };

  const filteredSessions = sessions.filter(session =>
    session.user_input.toLowerCase().includes(searchTerm.toLowerCase()) ||
    session.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckIcon color="success" />;
      case 'cancelled':
        return <CancelIcon color="default" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'active':
      case 'processing':
        return <ScheduleIcon color="primary" />;
      default:
        return <ScheduleIcon color="action" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'cancelled':
        return 'default';
      case 'failed':
        return 'error';
      case 'active':
      case 'processing':
        return 'primary';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const truncateText = (text: string, maxLength: number = 100) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const getStatusOptions = [
    { value: 'all', label: 'All Status' },
    { value: 'active', label: 'Active' },
    { value: 'processing', label: 'Processing' },
    { value: 'completed', label: 'Completed' },
    { value: 'cancelled', label: 'Cancelled' },
    { value: 'failed', label: 'Failed' },
  ];

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography variant="h4" component="h1" gutterBottom>
              Session History
            </Typography>
            <Typography variant="body2" color="text.secondary">
              View and search previous prompt generation sessions
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              onClick={() => dispatch(openModal('createSession'))}
              startIcon={<AddIcon />}
            >
              New Session
            </Button>
            <IconButton onClick={() => fetchSessions(page)} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Box>
        </Box>

        {/* Filters */}
        <Paper sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                placeholder="Search sessions..."
                value={searchTerm}
                onChange={handleSearch}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                select
                label="Status Filter"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
              >
                {getStatusOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="body2" color="text.secondary" sx={{ pt: 2 }}>
                {filteredSessions.length} sessions found
              </Typography>
            </Grid>
          </Grid>
        </Paper>

        {/* Loading */}
        {loading && <LinearProgress sx={{ mb: 2 }} />}

        {/* Error */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Sessions List */}
        {!loading && !error && (
          <>
            {filteredSessions.length === 0 ? (
              <Paper sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  {searchTerm || statusFilter !== 'all' ? 'No matching sessions found' : 'No sessions found'}
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  {searchTerm || statusFilter !== 'all'
                    ? 'Try adjusting your search or filters'
                    : 'Create your first session to get started'
                  }
                </Typography>
                {(!searchTerm && statusFilter === 'all') && (
                  <Button
                    variant="contained"
                    onClick={() => dispatch(openModal('createSession'))}
                    startIcon={<AddIcon />}
                  >
                    Create Your First Session
                  </Button>
                )}
              </Paper>
            ) : (
              <Grid container spacing={2}>
                {filteredSessions.map((session) => (
                  <Grid item xs={12} md={6} lg={4} key={session.id}>
                    <Card
                      sx={{
                        height: '100%',
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
                          {truncateText(session.user_input, 120)}
                        </Typography>

                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
                          <Typography variant="caption" color="text.secondary">
                            {formatDate(session.created_at)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Iteration {session.iteration_count}
                          </Typography>
                        </Box>

                        <Box sx={{ mt: 2 }}>
                          <Typography variant="caption" color="text.secondary">
                            {session.user_intervention_count} user inputs
                          </Typography>
                        </Box>

                        {session.final_prompt && (
                          <Box sx={{ mt: 2 }}>
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={(e) => {
                                e.stopPropagation();
                                copyToClipboard(session.final_prompt!);
                              }}
                              startIcon={<CopyIcon />}
                            >
                              Copy Prompt
                            </Button>
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                <Pagination
                  count={totalPages}
                  page={page}
                  onChange={(_, newPage) => setPage(newPage)}
                  color="primary"
                />
              </Box>
            )}
          </>
        )}
      </Box>

      {/* Floating Action Button */}
      <Fab
        color="primary"
        aria-label="create session"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
        onClick={() => dispatch(openModal('createSession'))}
      >
        <AddIcon />
      </Fab>
    </Container>
  );
};

export default History;