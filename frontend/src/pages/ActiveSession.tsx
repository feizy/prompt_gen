import React from 'react';
import { useParams } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
  Alert,
} from '@mui/material';

const ActiveSession: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();

  if (!sessionId) {
    return (
      <Container maxWidth="lg">
        <Alert severity="error" sx={{ mt: 2 }}>
          No session ID provided
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Active Session
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Session ID: {sessionId}
        </Typography>

        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Agent Collaboration
          </Typography>
          <Typography variant="body2" color="text.secondary">
            TODO: Implement real-time agent chat interface
          </Typography>
        </Paper>

        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            User Input
          </Typography>
          <Typography variant="body2" color="text.secondary">
            TODO: Implement supplementary input and clarifying questions
          </Typography>
        </Paper>

        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Generated Prompt
          </Typography>
          <Typography variant="body2" color="text.secondary">
            TODO: Display final generated prompt
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
};

export default ActiveSession;