/**
 * Enhanced User Input Panel for interactive agent communication
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  Paper,
  TextField,
  Button,
  Box,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  Alert,
  Collapse,
  useTheme,
  alpha,
  Stack,
  Badge,
  Fade,
  CircularProgress,
} from '@mui/material';
import {
  Send as SendIcon,
  Mic as MicIcon,
  MicOff as MicOffIcon,
  AttachFile as AttachIcon,
  History as HistoryIcon,
  SmartToy as BotIcon,
  Help as HelpIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  KeyboardArrowUp as ArrowUpIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';

interface UserInputPanelProps {
  sessionId: string;
  disabled?: boolean;
  onSubmit: (input: string, type: string) => Promise<boolean>;
  onContinueWithoutInput?: () => Promise<boolean>;
  placeholder?: string;
  suggestions?: string[];
  isLoading?: boolean;
  characterLimit?: number;
  showShortcuts?: boolean;
  sessionId?: string;
}

const UserInputPanel: React.FC<UserInputPanelProps> = ({
  sessionId,
  disabled = false,
  onSubmit,
  onContinueWithoutInput,
  placeholder = "Type your message here...",
  suggestions = [],
  isLoading = false,
  characterLimit = 2000,
  showShortcuts = true,
}) => {
  const theme = useTheme();
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inputHistory, setInputHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [charCount, setCharCount] = useState(0);

  const textFieldRef = useRef<HTMLTextAreaElement>(null);
  const inputContainerRef = useRef<HTMLDivElement>(null);

  // Focus input field when component mounts
  useEffect(() => {
    if (textFieldRef.current && !disabled) {
      textFieldRef.current.focus();
    }
  }, [disabled]);

  // Update character count
  useEffect(() => {
    setCharCount(input.length);
  }, [input]);

  // Load input history from localStorage
  useEffect(() => {
    try {
      const savedHistory = localStorage.getItem(`input_history_${sessionId}`);
      if (savedHistory) {
        setInputHistory(JSON.parse(savedHistory));
      }
    } catch (error) {
      console.warn('Failed to load input history:', error);
    }
  }, [sessionId]);

  // Save input history to localStorage
  const saveToHistory = (text: string) => {
    if (!text.trim()) return;

    const newHistory = [text, ...inputHistory.filter(h => h !== text)].slice(0, 10);
    setInputHistory(newHistory);

    try {
      localStorage.setItem(`input_history_${sessionId}`, JSON.stringify(newHistory));
    } catch (error) {
      console.warn('Failed to save input history:', error);
    }
  };

  const handleSubmit = async () => {
    if (!input.trim() || disabled || isLoading) return;

    setError(null);

    try {
      const success = await onSubmit(input.trim(), 'supplementary');
      if (success) {
        saveToHistory(input.trim());
        setInput('');
        setHistoryIndex(-1);
        textFieldRef.current?.focus();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    } else if (event.key === 'ArrowUp' && !input) {
      // Navigate through history when input is empty
      event.preventDefault();
      if (inputHistory.length > 0 && historyIndex < inputHistory.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setInput(inputHistory[newIndex]);
      }
    } else if (event.key === 'ArrowDown' && historyIndex >= 0) {
      // Navigate back through history
      event.preventDefault();
      const newIndex = historyIndex - 1;
      setHistoryIndex(newIndex);
      setInput(newIndex >= 0 ? inputHistory[newIndex] : '');
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
    setShowSuggestions(false);
    textFieldRef.current?.focus();
  };

  const handleHistoryItemClick = (item: string) => {
    setInput(item);
    setShowHistory(false);
    setHistoryIndex(-1);
    textFieldRef.current?.focus();
  };

  const handleClearInput = () => {
    setInput('');
    setHistoryIndex(-1);
    setError(null);
    textFieldRef.current?.focus();
  };

  const handleVoiceToggle = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      setError('Speech recognition is not supported in your browser');
      return;
    }

    if (isRecording) {
      setIsRecording(false);
      // Stop speech recognition logic here
    } else {
      setIsRecording(true);
      // Start speech recognition logic here
      setTimeout(() => setIsRecording(false), 5000); // Auto-stop after 5 seconds for demo
    }
  };

  const getQuickActions = () => [
    { label: "Add more details", action: () => setInput("Can you provide more details about...") },
    { label: "Ask for clarification", action: () => setInput("I need clarification on...") },
    { label: "Request alternative", action: () => setInput("Can you suggest an alternative approach?") },
    { label: "Provide example", action: () => setInput("Here's an example of what I'm looking for...") },
  ];

  const isOverLimit = charCount > characterLimit;
  const isNearLimit = charCount > characterLimit * 0.8;

  return (
    <Fade in timeout={300}>
      <Paper
        ref={inputContainerRef}
        sx={{
          p: 3,
          border: `2px solid ${alpha(theme.palette.primary.main, 0.1)}`,
          borderRadius: 2,
          backgroundColor: theme.palette.background.paper,
          boxShadow: theme.shadows[2],
          transition: 'all 0.2s ease-in-out',
          '&:focus-within': {
            borderColor: theme.palette.primary.main,
            boxShadow: theme.shadows[4],
          }
        }}
      >
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <BotIcon color="primary" />
            <Typography variant="h6" sx={{ fontWeight: 'medium' }}>
              Agent Communication
            </Typography>
            {isLoading && <CircularProgress size={20} />}
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Character Count */}
            <Chip
              label={`${charCount}/${characterLimit}`}
              size="small"
              color={isOverLimit ? 'error' : isNearLimit ? 'warning' : 'default'}
              variant="outlined"
            />

            {/* Clear Input */}
            {input && (
              <Tooltip title="Clear input">
                <IconButton size="small" onClick={handleClearInput}>
                  <ClearIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>

        {/* Error Display */}
        <Collapse in={!!error}>
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        </Collapse>

        {/* Main Input Area */}
        <Box sx={{ mb: 2 }}>
          <TextField
            inputRef={textFieldRef}
            multiline
            rows={3}
            fullWidth
            placeholder={placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={disabled || isLoading}
            error={isOverLimit}
            helperText={isOverLimit ? `Input exceeds ${characterLimit} character limit` : ''}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
                transition: 'all 0.2s ease-in-out',
              }
            }}
          />
        </Box>

        {/* Suggestions */}
        {suggestions.length > 0 && (
          <Collapse in={showSuggestions}>
            <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
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
                    sx={{ mb: 1 }}
                  />
                ))}
              </Stack>
            </Box>
          </Collapse>
        )}

        {/* History */}
        <Collapse in={showHistory}>
          <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 2, maxHeight: 200, overflow: 'auto' }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              Recent inputs:
            </Typography>
            <Stack spacing={1}>
              {inputHistory.map((item, index) => (
                <Paper
                  key={index}
                  variant="outlined"
                  sx={{ p: 1, cursor: 'pointer', '&:hover': { bgcolor: 'grey.100' } }}
                  onClick={() => handleHistoryItemClick(item)}
                >
                  <Typography variant="body2" noWrap>
                    {item}
                  </Typography>
                </Paper>
              ))}
            </Stack>
          </Box>
        </Collapse>

        {/* Quick Actions */}
        {showShortcuts && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              Quick actions:
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              {getQuickActions().map((action, index) => (
                <Chip
                  key={index}
                  label={action.label}
                  variant="outlined"
                  size="small"
                  clickable
                  onClick={action.action}
                  sx={{ mb: 1 }}
                />
              ))}
            </Stack>
          </Box>
        )}

        {/* Action Buttons */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Suggestions Toggle */}
            {suggestions.length > 0 && (
              <Tooltip title="Toggle suggestions">
                <IconButton
                  size="small"
                  onClick={() => setShowSuggestions(!showSuggestions)}
                  color={showSuggestions ? 'primary' : 'default'}
                >
                  <HelpIcon />
                </IconButton>
              </Tooltip>
            )}

            {/* History Toggle */}
            <Tooltip title="Toggle history">
              <IconButton
                size="small"
                onClick={() => setShowHistory(!showHistory)}
                color={showHistory ? 'primary' : 'default'}
              >
                <HistoryIcon />
              </IconButton>
            </Tooltip>

            {/* Voice Input */}
            <Tooltip title={isRecording ? 'Stop recording' : 'Voice input'}>
              <IconButton
                size="small"
                onClick={handleVoiceToggle}
                color={isRecording ? 'error' : 'default'}
              >
                {isRecording ? <MicOffIcon /> : <MicIcon />}
              </IconButton>
            </Tooltip>

            {/* File Attach */}
            <Tooltip title="Attach file">
              <IconButton size="small" disabled>
                <AttachIcon />
              </IconButton>
            </Tooltip>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Continue Without Input */}
            {onContinueWithoutInput && (
              <Button
                variant="outlined"
                onClick={onContinueWithoutInput}
                disabled={disabled || isLoading}
                size="small"
              >
                Continue
              </Button>
            )}

            {/* Send Button */}
            <Button
              variant="contained"
              onClick={handleSubmit}
              disabled={!input.trim() || disabled || isLoading || isOverLimit}
              startIcon={<SendIcon />}
              sx={{ minWidth: 100 }}
            >
              {isLoading ? 'Sending...' : 'Send'}
            </Button>
          </Box>
        </Box>

        {/* Keyboard Shortcuts Help */}
        {showShortcuts && (
          <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
            <Typography variant="caption" color="text.secondary">
              <strong>Shortcuts:</strong> Enter to send • Shift+Enter for new line • ↑/↓ for history
            </Typography>
          </Box>
        )}
      </Paper>
    </Fade>
  );
};

export default UserInputPanel;