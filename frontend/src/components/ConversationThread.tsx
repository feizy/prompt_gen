/**
 * Enhanced conversation thread component for agent messages
 */

import React, { useRef, useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Tooltip,
  Chip,
  LinearProgress,
  Alert,
  Fab,
  useTheme,
} from '@mui/material';
import {
  KeyboardArrowDown as ScrollDownIcon,
  MarkEmailRead as MarkReadIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../store';

import AgentMessageComponent from './AgentMessage';
import { AgentMessage } from '../store/slices/sessionSlice';

interface ConversationThreadProps {
  sessionId: string;
  messages: AgentMessage[];
  loading?: boolean;
  onRefresh?: () => void;
  onMarkAsRead?: (messageId: string) => void;
  onMessageFeedback?: (messageId: string, feedback: 'positive' | 'negative') => void;
  onCopyMessage?: (content: string) => void;
}

const ConversationThread: React.FC<ConversationThreadProps> = ({
  sessionId,
  messages,
  loading = false,
  onRefresh,
  onMarkAsRead,
  onMessageFeedback,
  onCopyMessage
}) => {
  const theme = useTheme();
  const dispatch = useDispatch();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [allRead, setAllRead] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  // Check if user is at bottom of the conversation
  const isAtBottom = () => {
    if (!containerRef.current) return true;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    return scrollTop + clientHeight >= scrollHeight - 10;
  };

  // Handle scroll events to show/hide scroll button
  const handleScroll = () => {
    const atBottom = isAtBottom();
    setShowScrollButton(!atBottom);
  };

  // Scroll to bottom and hide button
  const handleScrollToBottom = () => {
    scrollToBottom();
    setShowScrollButton(false);
  };

  // Mark all messages as read
  const handleMarkAllAsRead = () => {
    messages.forEach(message => {
      onMarkAsRead?.(message.id);
    });
    setAllRead(true);
    setUnreadCount(0);
  };

  // Monitor scroll position
  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, []);

  // Auto-scroll when new messages arrive
  useEffect(() => {
    if (messages.length > 0) {
      const timer = setTimeout(() => {
        scrollToBottom();
        setShowScrollButton(false);
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [messages]);

  // Check unread messages
  useEffect(() => {
    // This would typically come from Redux store or WebSocket
    // For now, we'll assume all messages are read when displayed
    setAllRead(true);
    setUnreadCount(0);
  }, [messages]);

  const getAgentStats = () => {
    const stats = messages.reduce((acc, message) => {
      acc[message.agent_type] = (acc[message.agent_type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return stats;
  };

  const agentStats = getAgentStats();
  const totalMessages = messages.length;

  if (totalMessages === 0 && !loading) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Box
          sx={{
            display: 'inline-flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
            p: 4,
            borderRadius: 2,
            bgcolor: 'background.paper',
            boxShadow: theme.shadows[2]
          }}
        >
          <Typography variant="h6" color="text.secondary" gutterBottom>
            Waiting for agents to start collaborating...
          </Typography>
          <Typography variant="body2" color="text.secondary">
            The AI agents will begin working on your requirements shortly.
          </Typography>
          {loading && <LinearProgress sx={{ width: 200, mt: 2 }} />}
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          backgroundColor: theme.palette.background.paper
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 'medium' }}>
              Agent Collaboration
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
              {totalMessages} messages
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Agent Statistics */}
            <Box sx={{ display: 'flex', gap: 1 }}>
              {Object.entries(agentStats).map(([agent, count]) => (
                <Chip
                  key={agent}
                  label={`${agent.replace('_', ' ')}: ${count}`}
                  size="small"
                  variant="outlined"
                />
              ))}
            </Box>

            {/* Unread Indicator */}
            {unreadCount > 0 && (
              <Chip
                label={`${unreadCount} unread`}
                color="primary"
                size="small"
                onClick={handleMarkAllAsRead}
                clickable
              />
            )}

            {/* Actions */}
            <Tooltip title="Refresh messages">
              <IconButton size="small" onClick={onRefresh} disabled={loading}>
                <RefreshIcon fontSize="small" />
              </IconButton>
            </Tooltip>

            <Tooltip title="Mark all as read">
              <IconButton
                size="small"
                onClick={handleMarkAllAsRead}
                disabled={allRead}
              >
                <MarkReadIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Loading Progress */}
        {loading && (
          <Box sx={{ mt: 1 }}>
            <LinearProgress />
          </Box>
        )}
      </Paper>

      {/* Messages Container */}
      <Box
        ref={containerRef}
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          p: 2,
          backgroundColor: theme.palette.grey[50],
          scrollBehavior: 'smooth'
        }}
      >
        <Box sx={{ maxWidth: 800, mx: 'auto' }}>
          {messages.map((message, index) => (
            <AgentMessageComponent
              key={message.id}
              message={message}
              isLatest={index === messages.length - 1}
              showActions={true}
              onCopy={onCopyMessage}
              onFeedback={onMessageFeedback}
            />
          ))}
          <div ref={messagesEndRef} />
        </Box>
      </Box>

      {/* Scroll to Bottom Button */}
      {showScrollButton && (
        <Fab
          color="primary"
          size="medium"
          onClick={handleScrollToBottom}
          sx={{
            position: 'absolute',
            bottom: 20,
            right: 20,
            zIndex: 1
          }}
        >
          <ScrollDownIcon />
        </Fab>
      )}

      {/* Connection Status Alert */}
      {!loading && totalMessages > 0 && (
        <Alert
          severity="info"
          sx={{
            m: 2,
            position: 'sticky',
            bottom: 0
          }}
          action={
            <IconButton
              aria-label="close"
              color="inherit"
              size="small"
              onClick={() => {/* Handle close */}}
            >
              ×
            </IconButton>
          }
        >
          <Typography variant="body2">
            You're viewing {totalMessages} messages from the agent collaboration.
            {unreadCount > 0 && ` ${unreadCount} unread messages.`}
          </Typography>
        </Alert>
      )}
    </Box>
  );
};

export default ConversationThread;