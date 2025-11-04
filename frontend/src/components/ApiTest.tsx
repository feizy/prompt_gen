import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Alert, CircularProgress } from '@mui/material';
import apiService from '../services/apiService';

const ApiTest: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const testHealthCheck = async () => {
    setLoading(true);
    setError(null);
    try {
      const health = await apiService.healthCheck();
      setResult(health);
      console.log('Health check result:', health);
    } catch (err: any) {
      setError(err.message);
      console.error('Health check error:', err);
    } finally {
      setLoading(false);
    }
  };

  const testCreateSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.createSession({
        user_input: 'Create a prompt for a productivity app that helps users manage their daily tasks',
        max_iterations: 5,
        max_interventions: 3
      });
      setResult(response);
      console.log('Create session result:', response);
    } catch (err: any) {
      setError(err.message);
      console.error('Create session error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    testHealthCheck();
  }, []);

  return (
    <Box p={3} maxWidth={600} mx="auto">
      <Typography variant="h4" gutterBottom>
        API Connection Test
      </Typography>

      <Typography variant="body1" color="text.secondary" gutterBottom>
        Testing connection to backend API at {apiService.getApiUrl()}
      </Typography>

      {loading && (
        <Box display="flex" justifyContent="center" my={2}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {result && (
        <Alert severity="success" sx={{ mb: 2 }}>
          API connection successful!
          <pre style={{ fontSize: '12px', marginTop: '8px' }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </Alert>
      )}

      <Box display="flex" gap={2} flexWrap="wrap">
        <Button variant="contained" onClick={testHealthCheck} disabled={loading}>
          Test Health Check
        </Button>
        <Button variant="outlined" onClick={testCreateSession} disabled={loading}>
          Test Create Session
        </Button>
      </Box>
    </Box>
  );
};

export default ApiTest;