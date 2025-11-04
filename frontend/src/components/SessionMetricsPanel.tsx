/**
 * Session Metrics Panel for displaying detailed session statistics
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Grid,
  LinearProgress,
  Chip,
  Avatar,
  useTheme,
  alpha,
  Stack,
  Tooltip,
  IconButton,
  Fade,
} from '@mui/material';
import {
  Timeline as TimelineIcon,
  Speed as SpeedIcon,
  Message as MessageIcon,
  QuestionAnswer as QuestionIcon,
  Timer as TimerIcon,
  TrendingUp as TrendingUpIcon,
  Refresh as RefreshIcon,
  Download as ExportIcon,
  People as PeopleIcon,
  Assessment as AnalyticsIcon,
} from '@mui/icons-material';

interface SessionMetrics {
  totalMessages: number;
  totalProcessingTime: number;
  averageResponseTime: number;
  agentParticipation: Record<string, number>;
  questionCount: number;
  userInterventions: number;
  sessionDuration: number;
  completionRate: number;
}

interface AgentMetrics {
  type: string;
  name: string;
  messageCount: number;
  totalProcessingTime: number;
  averageProcessingTime: number;
  lastMessageTime: string;
  participationRate: number;
}

interface SessionMetricsPanelProps {
  sessionId: string;
  metrics?: SessionMetrics;
  agentMetrics?: AgentMetrics[];
  onRefresh?: () => void;
  onExport?: () => void;
  compact?: boolean;
  showDetails?: boolean;
}

const SessionMetricsPanel: React.FC<SessionMetricsPanelProps> = ({
  sessionId,
  metrics,
  agentMetrics = [],
  onRefresh,
  onExport,
  compact = false,
  showDetails = true,
}) => {
  const theme = useTheme();
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    setLastUpdate(new Date());
  }, [metrics, agentMetrics]);

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getAgentInfo = (type: string) => {
    switch (type) {
      case 'product_manager':
        return {
          name: 'Product Manager',
          icon: '📋',
          color: theme.palette.info.main,
          bgColor: alpha(theme.palette.info.main, 0.1)
        };
      case 'technical_developer':
        return {
          name: 'Technical Developer',
          icon: '💻',
          color: theme.palette.success.main,
          bgColor: alpha(theme.palette.success.main, 0.1)
        };
      case 'team_lead':
        return {
          name: 'Team Lead',
          icon: '👨‍💼',
          color: theme.palette.warning.main,
          bgColor: alpha(theme.palette.warning.main, 0.1)
        };
      default:
        return {
          name: 'Unknown',
          icon: '🤖',
          color: theme.palette.grey[500],
          bgColor: alpha(theme.palette.grey[500], 0.1)
        };
    }
  };

  const getCompletionColor = (rate: number) => {
    if (rate >= 90) return 'success';
    if (rate >= 70) return 'warning';
    return 'error';
  };

  if (!metrics) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body2" color="text.secondary">
              No metrics available yet
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (compact) {
    return (
      <Fade in timeout={300}>
        <Card sx={{ mb: 2 }}>
          <CardContent sx={{ py: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <AnalyticsIcon color="primary" fontSize="small" />
                <Typography variant="subtitle2">Session Metrics</Typography>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  label={`${metrics.totalMessages} msgs`}
                  size="small"
                  variant="outlined"
                />
                <Chip
                  label={`${formatDuration(metrics.totalProcessingTime)}`}
                  size="small"
                  variant="outlined"
                />
                {onRefresh && (
                  <IconButton size="small" onClick={onRefresh}>
                    <RefreshIcon fontSize="small" />
                  </IconButton>
                )}
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Fade>
    );
  }

  return (
    <Fade in timeout={300}>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <AnalyticsIcon color="primary" />
              <Typography variant="h6" sx={{ fontWeight: 'medium' }}>
                Session Metrics
              </Typography>
              <Chip
                label={`Updated ${formatTime(lastUpdate.toISOString())}`}
                size="small"
                variant="outlined"
              />
            </Box>

            <Box sx={{ display: 'flex', gap: 1 }}>
              {onExport && (
                <Tooltip title="Export metrics">
                  <IconButton size="small" onClick={onExport}>
                    <ExportIcon />
                  </IconButton>
                </Tooltip>
              )}
              {onRefresh && (
                <Tooltip title="Refresh metrics">
                  <IconButton size="small" onClick={onRefresh}>
                    <RefreshIcon />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          </Box>

          {/* Key Metrics */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6} sm={3}>
              <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
                <MessageIcon color="primary" sx={{ fontSize: 32, mb: 1 }} />
                <Typography variant="h4" color="primary">
                  {metrics.totalMessages}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Total Messages
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
                <TimerIcon color="success" sx={{ fontSize: 32, mb: 1 }} />
                <Typography variant="h4" color="success">
                  {formatDuration(metrics.totalProcessingTime)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Processing Time
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
                <SpeedIcon color="warning" sx={{ fontSize: 32, mb: 1 }} />
                <Typography variant="h4" color="warning">
                  {formatDuration(metrics.averageResponseTime)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Avg Response
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
                <TrendingUpIcon color="info" sx={{ fontSize: 32, mb: 1 }} />
                <Typography variant="h4" color="info">
                  {metrics.completionRate}%
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Completion
                </Typography>
              </Box>
            </Grid>
          </Grid>

          {/* Completion Progress */}
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Session Completion Progress
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {metrics.completionRate}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={metrics.completionRate}
              color={getCompletionColor(metrics.completionRate) as any}
              sx={{
                height: 8,
                borderRadius: 4,
              }}
            />
          </Box>

          {/* Agent Breakdown */}
          {showDetails && agentMetrics.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <PeopleIcon fontSize="small" />
                Agent Participation
              </Typography>
              <Stack spacing={1}>
                {agentMetrics.map((agent) => {
                  const agentInfo = getAgentInfo(agent.type);

                  return (
                    <Box
                      key={agent.type}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 2,
                        p: 1.5,
                        bgcolor: 'grey.50',
                        borderRadius: 2,
                      }}
                    >
                      <Avatar
                        sx={{
                          bgcolor: agentInfo.bgColor,
                          color: agentInfo.color,
                          width: 32,
                          height: 32,
                          fontSize: 16,
                        }}
                      >
                        {agentInfo.icon}
                      </Avatar>

                      <Box sx={{ flexGrow: 1 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                          <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                            {agentInfo.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {agent.participationRate}% participation
                          </Typography>
                        </Box>

                        <LinearProgress
                          variant="determinate"
                          value={agent.participationRate}
                          sx={{
                            height: 4,
                            borderRadius: 2,
                            bgcolor: alpha(agentInfo.color, 0.1),
                            '& .MuiLinearProgress-bar': {
                              bgcolor: agentInfo.color,
                            }
                          }}
                        />

                        <Box sx={{ display: 'flex', gap: 2, mt: 0.5 }}>
                          <Typography variant="caption" color="text.secondary">
                            {agent.messageCount} messages
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {formatDuration(agent.totalProcessingTime)} total
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {formatDuration(agent.averageProcessingTime)} avg
                          </Typography>
                        </Box>
                      </Box>
                    </Box>
                  );
                })}
              </Stack>
            </Box>
          )}

          {/* Additional Stats */}
          {showDetails && (
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Chip
                icon={<QuestionIcon />}
                label={`${metrics.questionCount} questions`}
                size="small"
                variant="outlined"
              />
              <Chip
                icon={<TimelineIcon />}
                label={`${metrics.userInterventions} interventions`}
                size="small"
                variant="outlined"
              />
              <Chip
                icon={<TimerIcon />}
                label={`${formatDuration(metrics.sessionDuration)} duration`}
                size="small"
                variant="outlined"
              />
            </Box>
          )}
        </CardContent>
      </Card>
    </Fade>
  );
};

export default SessionMetricsPanel;