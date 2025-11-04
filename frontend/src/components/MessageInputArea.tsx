/**
 * Message Input Area component for real-time agent communication
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  Typography,
  Chip,
  Tooltip,
  CircularProgress,
  Alert,
  Collapse,
  useTheme,
  alpha,
  Stack,
  Badge,
  Fade,
} from '@mui/material';
import {
  Send as SendIcon,
  Mic as MicIcon,
  MicOff as MicOffIcon,
  AttachFile as AttachIcon,
  KeyboardArrowUp as ArrowUpIcon,
  Clear as ClearIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
} from '@mui/icons-material';

interface MessageInputAreaProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
  maxLength?: number;
  showVoiceInput?: boolean;
  showAttachment?: boolean;
  showCharacterCount?: boolean;
  suggestions?: string[];
  onSuggestionClick?: (suggestion: string) => void;
  sessionId?: string;
  agentType?: 'user' | 'bot';
}

const MessageInputArea: React.FC<MessageInputAreaProps> = ({
  onSendMessage,
  disabled = false,
  loading = false,
  placeholder = "Type your message...",
  maxLength = 2000,
  showVoiceInput = true,
  showAttachment = false,
  showCharacterCount = true,
  suggestions = [],
  onSuggestionClick,
  sessionId,
  agentType = 'user',
}) => {
  const theme = useTheme();
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [charCount, setCharCount] = useState(0);

  const textFieldRef = useRef<HTMLTextAreaElement>(null);
  const inputAreaRef = useRef<HTMLDivElement>(null);

  // Focus input field when component mounts or enables
  useEffect(() => {
    if (textFieldRef.current && !disabled) {
      textFieldRef.current.focus();
    }
  }, [disabled]);

  // Update character count
  useEffect(() => {
    setCharCount(message.length);
  }, [message]);

  // Auto-show suggestions when there are suggestions and input is empty
  useEffect(() => {
    if (suggestions.length > 0 && !message && !disabled) {
      setShowSuggestions(true);
    }
  }, [suggestions, message, disabled]);

  const handleSendMessage = () => {
    if (!message.trim() || disabled || loading) return;

    setError(null);

    try {
      onSendMessage(message.trim());
      setMessage('');
      setShowSuggestions(false);
      textFieldRef.current?.focus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  };

  const handleVoiceToggle = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      setError('Speech recognition is not supported in your browser');
      return;
    }

    if (isRecording) {
      setIsRecording(false);
      // Stop speech recognition logic
    } else {
      setIsRecording(true);
      // Start speech recognition logic
      setError(null);

      // Simulate voice input after 2 seconds (for demo)
      setTimeout(() => {
        setMessage("This is a simulated voice input message");
        setIsRecording(false);
      }, 2000);
    }
  };

  const handleClearInput = () => {
    setMessage('');
    setError(null);
    textFieldRef.current?.focus();
  };

  const handleSuggestionClick = (suggestion: string) => {
    setMessage(suggestion);
    setShowSuggestions(false);
    textFieldRef.current?.focus();
    onSuggestionClick?.(suggestion);
  };

  const isOverLimit = charCount > maxLength;
  const isNearLimit = charCount > maxLength * 0.8;
  const canSend = message.trim() && !disabled && !loading && !isOverLimit;

  const getAvatarIcon = () => {
    return agentType === 'bot' ? <BotIcon /> : <PersonIcon />;
  };

  const getAvatarColor = () => {
    return agentType === 'bot' ? 'primary' : 'secondary';
  };

  return (
    <Fade in timeout={300}>
      <Box ref={inputAreaRef}>
        {/* Error Display */}
        <Collapse in={!!error}>
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        </Collapse>

        {/* Suggestions */}
        <Collapse in={showSuggestions && suggestions.length > 0}>
          <Box sx={{ mb: 2 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              Suggested responses:
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              {suggestions.map((suggestion, index) => (
                <Chip
                  key={index}
                  label={suggestion}
                  variant="outlined"
                  size="small"
                  clickable
                  onClick={() => handleSuggestionClick(suggestion)}
                  sx={{
                    mb: 1,
                    '&:hover': {
                      backgroundColor: alpha(theme.palette.primary.main, 0.08),
                    }
                  }}
                />
              ))}
            </Stack>
          </Box>
        </Collapse>

        {/* Main Input Area */}
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 2,
            border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
            backgroundColor: theme.palette.background.paper,
            transition: 'all 0.2s ease-in-out',
            '&:focus-within': {
              borderColor: theme.palette.primary.main,
              boxShadow: theme.shadows[4],
            }
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 1 }}>
            {/* Avatar */}
            <Box sx={{ mb: 1 }}>
              <Box
                sx={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  backgroundColor: alpha(theme.palette[getAvatarColor()].main, 0.1),
                  color: theme.palette[getAvatarColor()].main,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {getAvatarIcon()}
              </Box>
            </Box>

            {/* Text Input */}
            <Box sx={{ flexGrow: 1 }}>
              <TextField
                inputRef={textFieldRef}
                multiline
                maxRows={4}
                minRows={1}
                fullWidth
                placeholder={placeholder}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={disabled || loading}
                error={isOverLimit}
                helperText={isOverLimit ? `Message exceeds ${maxLength} characters` : ''}
                variant="standard"
                InputProps={{
                  disableUnderline: true,
                  sx: {
                    typography: 'body1',
                    '&::before': {
                      display: 'none',
                    },
                    '&::after': {
                      display: 'none',
                    },
                  }
                }}
                sx={{
                  '& .MuiInputBase-root': {
                    padding: 0,
                  }
                }}
              />
            </Box>

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {/* Clear Input */}
              {message && (
                <Tooltip title="Clear input">
                  <IconButton
                    size="small"
                    onClick={handleClearInput}
                    disabled={disabled || loading}
                    sx={{ mb: 1 }}
                  >
                    <ClearIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}

              {/* Voice Input */}
              {showVoiceInput && (
                <Tooltip title={isRecording ? 'Stop recording' : 'Voice input'}>
                  <IconButton
                    size="small"
                    onClick={handleVoiceToggle}
                    disabled={disabled || loading}
                    color={isRecording ? 'error' : 'default'}
                    sx={{ mb: 1 }}
                  >
                    {isRecording ? <MicOffIcon fontSize="small" /> : <MicIcon fontSize="small" />}
                  </IconButton>
                </Tooltip>
              )}

              {/* Attachment */}
              {showAttachment && (
                <Tooltip title="Attach file">
                  <IconButton
                    size="small"
                    disabled={disabled || loading}
                    sx={{ mb: 1 }}
                  >
                    <AttachIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}

              {/* Send Button */}
              <Tooltip title="Send message">
                <IconButton
                  onClick={handleSendMessage}
                  disabled={!canSend}
                  color="primary"
                  sx={{ mb: 1 }}
                >
                  {loading ? (
                    <CircularProgress size={20} />
                  ) : (
                    <SendIcon />
                  )}
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {/* Character Count and Status */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {isRecording && (
                <Badge color="error" variant="dot">
                  <Typography variant="caption" color="error">
                    Recording...
                  </Typography>
                </Badge>
              )}
            </Box>

            {showCharacterCount && (
              <Typography
                variant="caption"
                color={
                  isOverLimit
                    ? 'error'
                    : isNearLimit
                    ? 'warning'
                    : 'text.secondary'
                }
              >
                {charCount}/{maxLength}
              </Typography>
            )}
          </Box>
        </Paper>

        {/* Quick Hints */}
        <Box sx={{ mt: 1, textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Press Enter to send • Shift+Enter for new line
          </Typography>
        </Box>
      </Box>
    </Fade>
  );
};

export default MessageInputArea;