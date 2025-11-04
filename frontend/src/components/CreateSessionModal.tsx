import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Stack,
  LinearProgress,
} from '@mui/material';
import {
  Send as SendIcon,
  Lightbulb as LightbulbIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';

import { closeModal } from '../store/slices/uiSlice';

interface CreateSessionModalProps {
  open: boolean;
  onClose: () => void;
}

const CreateSessionModal: React.FC<CreateSessionModalProps> = ({ open, onClose }) => {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const [userInput, setUserInput] = useState('');
  const [maxIterations, setMaxIterations] = useState(5);
  const [maxInterventions, setMaxInterventions] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const examplePrompts = [
    "Create a chatbot for customer service that can handle common inquiries and escalate complex issues to human agents",
    "Design a project management tool for remote teams with real-time collaboration and task tracking",
    "Build an e-commerce recommendation system that suggests products based on user behavior and preferences",
    "Develop a content scheduling platform for social media managers with analytics and automation features",
    "Create a fitness tracking app with personalized workout plans and progress monitoring",
  ];

  const handleSubmit = async () => {
    if (!userInput.trim() || submitting) return;

    try {
      setSubmitting(true);
      setError(null);

      const response = await fetch('/v1/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_input: userInput.trim(),
          max_iterations: maxIterations,
          max_interventions: maxInterventions,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create session');
      }

      const data = await response.json();

      // Close modal and navigate to the new session
      dispatch(closeModal());
      navigate(`/session/${data.session_id}`);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!submitting) {
      setUserInput('');
      setError(null);
      onClose();
    }
  };

  const useExamplePrompt = (prompt: string) => {
    setUserInput(prompt);
  };

  const characterCount = userInput.length;
  const characterLimit = 2000;
  const isValid = characterCount >= 10 && characterCount <= characterLimit;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <LightbulbIcon />
          Create New Session
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <Typography variant="body1" gutterBottom>
            Describe what you want to create or achieve. Our AI agents will collaborate to generate a comprehensive prompt.
          </Typography>

          {/* User Input */}
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Your Requirements"
            placeholder="Describe your project, goals, and what you want the AI to help you create..."
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            disabled={submitting}
            helperText={`${characterCount}/${characterLimit} characters`}
            error={characterCount > 0 && !isValid}
            sx={{ mt: 2 }}
          />

          {/* Example Prompts */}
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Example Prompts:
            </Typography>
            <Stack spacing={1}>
              {examplePrompts.map((prompt, index) => (
                <Chip
                  key={index}
                  label={prompt.length > 80 ? `${prompt.substring(0, 80)}...` : prompt}
                  variant="outlined"
                  size="small"
                  onClick={() => useExamplePrompt(prompt)}
                  clickable
                  sx={{ justifyContent: 'flex-start', height: 'auto', py: 1 }}
                />
              ))}
            </Stack>
          </Box>

          {/* Advanced Settings */}
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SettingsIcon fontSize="small" />
              Advanced Settings
            </Typography>

            <Box sx={{ pl: 3, mt: 2 }}>
              {/* Max Iterations */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" gutterBottom>
                  Maximum Iterations: {maxIterations}
                </Typography>
                <Slider
                  value={maxIterations}
                  onChange={(_, value) => setMaxIterations(value as number)}
                  min={1}
                  max={10}
                  step={1}
                  marks={[
                    { value: 3, label: '3' },
                    { value: 5, label: '5' },
                    { value: 7, label: '7' },
                    { value: 10, label: '10' },
                  ]}
                  disabled={submitting}
                />
                <Typography variant="caption" color="text.secondary">
                  How many times the agents will collaborate to refine the prompt
                </Typography>
              </Box>

              {/* Max Interventions */}
              <Box>
                <Typography variant="body2" gutterBottom>
                  Maximum User Interventions: {maxInterventions}
                </Typography>
                <Slider
                  value={maxInterventions}
                  onChange={(_, value) => setMaxInterventions(value as number)}
                  min={1}
                  max={10}
                  step={1}
                  marks={[
                    { value: 1, label: '1' },
                    { value: 3, label: '3' },
                    { value: 5, label: '5' },
                    { value: 10, label: '10' },
                  ]}
                  disabled={submitting}
                />
                <Typography variant="caption" color="text.secondary">
                  How many times you can provide additional input during the process
                </Typography>
              </Box>
            </Box>
          </Box>

          {/* Error Display */}
          {error && (
            <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* Submitting Progress */}
          {submitting && (
            <Box sx={{ mt: 2 }}>
              <LinearProgress />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Creating session and starting agent collaboration...
              </Typography>
            </Box>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 3 }}>
        <Button onClick={handleClose} disabled={submitting}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={!isValid || submitting}
          startIcon={<SendIcon />}
        >
          {submitting ? 'Creating...' : 'Create Session'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CreateSessionModal;