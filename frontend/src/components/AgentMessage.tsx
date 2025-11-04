/**
 * Enhanced Agent Message component for displaying agent conversations
 */

import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Chip,
  Box,
  Avatar,
  IconButton,
  Tooltip,
  Collapse,
  useTheme,
  alpha,
  LinearProgress,
  Fade,
} from '@mui/material';
import {
  Person as PersonIcon,
  Engineering as EngineerIcon,
  SupervisorAccount as LeadIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  ContentCopy as CopyIcon,
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
  Share as ShareIcon,
  Speed as SpeedIcon,
  AccessTime as AccessTimeIcon,
} from '@mui/icons-material';
import { AgentMessage } from '../store/slices/sessionSlice';

interface AgentMessageComponentProps {
  message: AgentMessage;
  isLatest?: boolean;
  showActions?: boolean;
  onCopy?: (content: string) => void;
  onFeedback?: (messageId: string, feedback: 'positive' | 'negative') => void;
}

const AgentMessageComponent: React.FC<AgentMessageComponentProps> = ({
  message,
  isLatest = false,
  showActions = true,
  onCopy,
  onFeedback
}) => {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const getAgentInfo = (agentType: string) => {
    switch (agentType) {
      case 'product_manager':
        return {
          name: 'Product Manager',
          icon: <PersonIcon />,
          color: theme.palette.info.main,
          bgColor: alpha(theme.palette.info.main, 0.1),
          description: 'Analyzes requirements and creates product specifications'
        };
      case 'technical_developer':
        return {
          name: 'Technical Developer',
          icon: <EngineerIcon />,
          color: theme.palette.success.main,
          bgColor: alpha(theme.palette.success.main, 0.1),
          description: 'Designs technical solutions and implementation approaches'
        };
      case 'team_lead':
        return {
          name: 'Team Lead',
          icon: <LeadIcon />,
          color: theme.palette.warning.main,
          bgColor: alpha(theme.palette.warning.main, 0.1),
          description: 'Reviews and approves final prompts, ensures quality'
        };
      default:
        return {
          name: 'Agent',
          icon: <PersonIcon />,
          color: theme.palette.grey[500],
          bgColor: alpha(theme.palette.grey[500], 0.1),
          description: 'AI Assistant'
        };
    }
  };

  const getMessageTypeColor = (messageType: string) => {
    switch (messageType) {
      case 'requirement':
        return { color: 'info', label: 'Requirement', icon: '📋' };
      case 'technical_solution':
        return { color: 'success', label: 'Solution', icon: '💻' };
      case 'review':
        return { color: 'warning', label: 'Review', icon: '👁️' };
      case 'approval':
        return { color: 'success', label: 'Approved', icon: '✅' };
      case 'rejection':
        return { color: 'error', label: 'Rejected', icon: '❌' };
      case 'question':
        return { color: 'info', label: 'Question', icon: '❓' };
      default:
        return { color: 'default', label: messageType, icon: '💬' };
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDuration = (ms: number | null) => {
    if (!ms) return '';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(message.message_content);
    setCopied(true);
    onCopy?.(message.message_content);
    setTimeout(() => setCopied(false), 2000);
  };

  const agentInfo = getAgentInfo(message.agent_type);
  const messageTypeInfo = getMessageTypeColor(message.message_type);

  return (
    <Fade in timeout={300}>
      <Card
        sx={{
          mb: 2,
          border: isLatest ? `2px solid ${agentInfo.color}` : '1px solid rgba(0, 0, 0, 0.12)',
          borderRadius: 2,
          overflow: 'visible',
          position: 'relative',
          '&:hover': {
            boxShadow: theme.shadows[4],
          }
        }}
      >
        {isLatest && (
          <Box
            sx={{
              position: 'absolute',
              top: -1,
              left: 16,
              backgroundColor: 'background.paper',
              px: 1,
              borderRadius: 1,
              border: `1px solid ${agentInfo.color}`,
            }}
          >
            <Typography variant="caption" sx={{ color: agentInfo.color, fontWeight: 'bold' }}>
              Latest
            </Typography>
          </Box>
        )}

        <CardContent sx={{ pb: 2 }}>
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Avatar
              sx={{
                bgcolor: agentInfo.bgColor,
                color: agentInfo.color,
                width: 40,
                height: 40
              }}
            >
              {agentInfo.icon}
            </Avatar>

            <Box sx={{ flexGrow: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'medium' }}>
                  {agentInfo.name}
                </Typography>
                <Chip
                  label={messageTypeInfo.label}
                  color={messageTypeInfo.color as any}
                  size="small"
                  icon={<span>{messageTypeInfo.icon}</span>}
                />
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  {formatTime(message.created_at)}
                </Typography>

                {message.processing_time_ms && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <SpeedIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                    <Typography variant="caption" color="text.secondary">
                      {formatDuration(message.processing_time_ms)}
                    </Typography>
                  </Box>
                )}

                <Tooltip title={agentInfo.description}>
                  <IconButton size="small">
                    <ExpandMoreIcon
                      fontSize="small"
                      onClick={() => setExpanded(!expanded)}
                      sx={{
                        transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.2s'
                      }}
                    />
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
          </Box>

          {/* Message Content */}
          <Box sx={{ ml: 7 }}>
            <Typography
              variant="body1"
              sx={{
                whiteSpace: 'pre-wrap',
                lineHeight: 1.6,
                color: theme.palette.text.primary,
                fontSize: '0.95rem'
              }}
            >
              {message.message_content}
            </Typography>

            {/* Expandable content */}
            <Collapse in={expanded} timeout="auto" unmountOnExit>
              <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  <strong>Message Details:</strong>
                </Typography>
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" display="block">
                    • Sequence: #{message.sequence_number}
                  </Typography>
                  <Typography variant="caption" display="block">
                    • Type: {message.message_type}
                  </Typography>
                  <Typography variant="caption" display="block">
                    • Agent: {message.agent_type}
                  </Typography>
                  {message.processing_time_ms && (
                    <Typography variant="caption" display="block">
                      • Processing Time: {formatDuration(message.processing_time_ms)}
                    </Typography>
                  )}
                  <Typography variant="caption" display="block">
                    • Created: {new Date(message.created_at).toLocaleString()}
                  </Typography>
                </Box>
              </Box>
            </Collapse>
          </Box>

          {/* Message Footer */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2, ml: 7 }}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Tooltip title="Copy message">
                <IconButton
                  size="small"
                  onClick={handleCopy}
                  color={copied ? 'success' : 'default'}
                >
                  <CopyIcon fontSize="small" />
                </IconButton>
              </Tooltip>

              {showActions && onFeedback && (
                <>
                  <Tooltip title="Helpful">
                    <IconButton
                      size="small"
                      onClick={() => onFeedback(message.id, 'positive')}
                      color="primary"
                    >
                      <ThumbUpIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>

                  <Tooltip title="Not helpful">
                    <IconButton
                      size="small"
                      onClick={() => onFeedback(message.id, 'negative')}
                      color="error"
                    >
                      <ThumbDownIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>

                  <Tooltip title="Share">
                    <IconButton size="small">
                      <ShareIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </>
              )}
            </Box>

            <Typography variant="caption" color="text.secondary">
              <AccessTimeIcon sx={{ fontSize: 12, mr: 0.5 }} />
              {formatTime(message.created_at)}
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Fade>
  );
};

export default AgentMessageComponent;