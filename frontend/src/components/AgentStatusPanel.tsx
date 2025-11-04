/**
 * Enhanced Agent Status Panel for monitoring agent activity and states
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
  Avatar,
  IconButton,
  Tooltip,
  Badge,
  useTheme,
  alpha,
  Stack,
  Fade,
  Collapse,
  Button,
} from '@mui/material';
import {
  Person as PersonIcon,
  Engineering as EngineerIcon,
  SupervisorAccount as LeadIcon,
  Schedule as WaitingIcon,
  PlayArrow as ActiveIcon,
  CheckCircle as CompletedIcon,
  Error as ErrorIcon,
  Pause as PausedIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';

interface Agent {
  id: string;
  name: string;
  type: 'product_manager' | 'technical_developer' | 'team_lead';
  status: 'idle' | 'thinking' | 'processing' | 'waiting' | 'completed' | 'error';
  lastActivity: string;
  messageCount: number;
  processingTime?: number;
  currentTask?: string;
  avatar?: string;
}

interface AgentStatusPanelProps {
  agents: Agent[];
  sessionId: string;
  overallStatus: string;
  onRefresh?: () => void;
  onAgentClick?: (agent: Agent) => void;
  compact?: boolean;
  showDetails?: boolean;
}

const AgentStatusPanel: React.FC<AgentStatusPanelProps> = ({
  agents,
  sessionId,
  overallStatus,
  onRefresh,
  onAgentClick,
  compact = false,
  showDetails = true,
}) => {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(!compact);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    setLastUpdate(new Date());
  }, [agents]);

  const getAgentInfo = (type: string) => {
    switch (type) {
      case 'product_manager':
        return {
          name: 'Product Manager',
          icon: <PersonIcon />,
          color: theme.palette.info.main,
          bgColor: alpha(theme.palette.info.main, 0.1),
          description: 'Analyzing requirements and creating specifications'
        };
      case 'technical_developer':
        return {
          name: 'Technical Developer',
          icon: <EngineerIcon />,
          color: theme.palette.success.main,
          bgColor: alpha(theme.palette.success.main, 0.1),
          description: 'Designing technical solutions and implementation'
        };
      case 'team_lead':
        return {
          name: 'Team Lead',
          icon: <LeadIcon />,
          color: theme.palette.warning.main,
          bgColor: alpha(theme.palette.warning.main, 0.1),
          description: 'Reviewing and ensuring quality standards'
        };
      default:
        return {
          name: 'Unknown Agent',
          icon: <PersonIcon />,
          color: theme.palette.grey[500],
          bgColor: alpha(theme.palette.grey[500], 0.1),
          description: 'AI Assistant'
        };
    }
  };

  const getStatusInfo = (status: string) => {
    switch (status) {
      case 'idle':
        return {
          label: 'Idle',
          icon: <PauseIcon />,
          color: 'default',
          progress: 0
        };
      case 'thinking':
        return {
          label: 'Thinking',
          icon: <WaitingIcon />,
          color: 'info',
          progress: 30
        };
      case 'processing':
        return {
          label: 'Processing',
          icon: <ActiveIcon />,
          color: 'primary',
          progress: 60
        };
      case 'waiting':
        return {
          label: 'Waiting',
          icon: <WaitingIcon />,
          color: 'warning',
          progress: 45
        };
      case 'completed':
        return {
          label: 'Completed',
          icon: <CompletedIcon />,
          color: 'success',
          progress: 100
        };
      case 'error':
        return {
          label: 'Error',
          icon: <ErrorIcon />,
          color: 'error',
          progress: 0
        };
      default:
        return {
          label: 'Unknown',
          icon: <ErrorIcon />,
          color: 'default',
          progress: 0
        };
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const getTotalMessages = () => agents.reduce((sum, agent) => sum + agent.messageCount, 0);

  const getActiveAgents = () => agents.filter(agent =>
    agent.status === 'thinking' || agent.status === 'processing'
  ).length;

  const getOverallProgress = () => {
    const totalProgress = agents.reduce((sum, agent) => {
      const statusInfo = getStatusInfo(agent.status);
      return sum + statusInfo.progress;
    }, 0);
    return Math.round(totalProgress / agents.length);
  };

  if (compact) {
    return (
      <Card sx={{ mb: 2 }}>
        <CardContent sx={{ py: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 'medium' }}>
                Agent Status
              </Typography>
              <Badge badgeContent={getActiveAgents()} color="primary">
                <Chip
                  label={overallStatus.replace('_', ' ')}
                  color="primary"
                  size="small"
                />
              </Badge>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="caption" color="text.secondary">
                {getTotalMessages()} messages
              </Typography>
              <IconButton size="small" onClick={() => setExpanded(!expanded)}>
                {expanded ? <ExpandIcon /> : <CollapseIcon />}
              </IconButton>
              {onRefresh && (
                <IconButton size="small" onClick={onRefresh}>
                  <RefreshIcon />
                </IconButton>
              )}
            </Box>
          </Box>

          <Collapse in={expanded}>
            <Box sx={{ mt: 2 }}>
              <LinearProgress
                variant="determinate"
                value={getOverallProgress()}
                sx={{ mb: 2 }}
              />
              <Stack direction="row" spacing={1}>
                {agents.map((agent) => {
                  const agentInfo = getAgentInfo(agent.type);
                  const statusInfo = getStatusInfo(agent.status);

                  return (
                    <Chip
                      key={agent.id}
                      avatar={
                        <Avatar sx={{ bgcolor: agentInfo.bgColor, width: 24, height: 24 }}>
                          {agentInfo.icon}
                        </Avatar>
                      }
                      label={`${agentInfo.name} (${statusInfo.label})`}
                      color={statusInfo.color as any}
                      size="small"
                      variant="outlined"
                      onClick={() => onAgentClick?.(agent)}
                      clickable
                    />
                  );
                })}
              </Stack>
            </Box>
          </Collapse>
        </CardContent>
      </Card>
    );
  }

  return (
    <Fade in timeout={300}>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 'medium', mb: 1 }}>
                Agent Collaboration Status
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  label={overallStatus.replace('_', ' ')}
                  color="primary"
                  size="small"
                />
                <Typography variant="caption" color="text.secondary">
                  {getActiveAgents()} active • {getTotalMessages()} total messages
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Updated {formatTime(lastUpdate.toISOString())}
                </Typography>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {onRefresh && (
                <Tooltip title="Refresh agent status">
                  <IconButton size="small" onClick={onRefresh}>
                    <RefreshIcon />
                  </IconButton>
                </Tooltip>
              )}
              <Tooltip title="Agent settings">
                <IconButton size="small">
                  <SettingsIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {/* Overall Progress */}
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Overall Progress
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {getOverallProgress()}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={getOverallProgress()}
              sx={{
                height: 8,
                borderRadius: 4,
                bgcolor: alpha(theme.palette.primary.main, 0.1)
              }}
            />
          </Box>

          {/* Agent Cards */}
          <Stack spacing={2}>
            {agents.map((agent) => {
              const agentInfo = getAgentInfo(agent.type);
              const statusInfo = getStatusInfo(agent.status);

              return (
                <Card
                  key={agent.id}
                  variant="outlined"
                  sx={{
                    cursor: onAgentClick ? 'pointer' : 'default',
                    transition: 'all 0.2s ease-in-out',
                    border: `1px solid ${alpha(agentInfo.color, 0.3)}`,
                    '&:hover': {
                      boxShadow: theme.shadows[2],
                      transform: 'translateY(-1px)',
                    }
                  }}
                  onClick={() => onAgentClick?.(agent)}
                >
                  <CardContent sx={{ py: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      {/* Agent Avatar */}
                      <Avatar
                        sx={{
                          bgcolor: agentInfo.bgColor,
                          color: agentInfo.color,
                          width: 48,
                          height: 48
                        }}
                      >
                        {agentInfo.icon}
                      </Avatar>

                      {/* Agent Info */}
                      <Box sx={{ flexGrow: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 'medium' }}>
                            {agentInfo.name}
                          </Typography>
                          <Chip
                            label={statusInfo.label}
                            color={statusInfo.color as any}
                            size="small"
                            icon={statusInfo.icon}
                          />
                          {agent.currentTask && (
                            <Tooltip title={agent.currentTask}>
                              <Chip
                                label={agent.currentTask}
                                size="small"
                                variant="outlined"
                              />
                            </Tooltip>
                          )}
                        </Box>

                        <Typography variant="caption" color="text.secondary" sx={{ mb: 1 }}>
                          {agentInfo.description}
                        </Typography>

                        {/* Progress Bar */}
                        {statusInfo.progress > 0 && statusInfo.progress < 100 && (
                          <LinearProgress
                            variant="indeterminate"
                            size="small"
                            sx={{ mb: 1 }}
                          />
                        )}

                        {/* Stats */}
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                          <Typography variant="caption" color="text.secondary">
                            {agent.messageCount} messages
                          </Typography>
                          {agent.processingTime && (
                            <Typography variant="caption" color="text.secondary">
                              {formatDuration(agent.processingTime)}
                            </Typography>
                          )}
                          <Typography variant="caption" color="text.secondary">
                            Last active {formatTime(agent.lastActivity)}
                          </Typography>
                        </Box>
                      </Box>

                      {/* Actions */}
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Tooltip title="View agent details">
                          <IconButton size="small">
                            <ViewIcon />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              );
            })}
          </Stack>

          {/* Session Info */}
          {showDetails && (
            <Box sx={{ mt: 3, pt: 2, borderTop: 1, borderColor: 'divider' }}>
              <Typography variant="caption" color="text.secondary">
                Session ID: {sessionId}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    </Fade>
  );
};

export default AgentStatusPanel;