import React from 'react';
import {
  Container,
  Typography,
  Box,
  Button,
  Paper,
  Grid,
  Card,
  CardContent,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';

import { openModal } from '../store/slices/uiSlice';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const handleCreateSession = () => {
    dispatch(openModal('createSession'));
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          AI Agent Prompt Generator
        </Typography>
        <Typography variant="h6" color="text.secondary" paragraph>
          Create detailed LLM prompts through collaborative AI agents
        </Typography>

        <Grid container spacing={3} sx={{ mt: 2 }}>
          <Grid item xs={12} md={6}>
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
                >
                  Create Session
                </Button>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
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
                >
                  View History
                </Button>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  How It Works
                </Typography>
                <Typography variant="body1" paragraph>
                  Our system uses three specialized AI agents working together:
                </Typography>
                <ul>
                  <li><strong>Product Manager</strong>: Analyzes your requirements and creates detailed product specifications</li>
                  <li><strong>Technical Developer</strong>: Designs technical solutions and implementation approaches</li>
                  <li><strong>Team Lead</strong>: Reviews and approves the final prompt, ensuring quality and completeness</li>
                </ul>
                <Typography variant="body2" color="text.secondary">
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