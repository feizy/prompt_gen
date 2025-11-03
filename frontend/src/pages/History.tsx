import React from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';

const History: React.FC = () => {
  // TODO: Fetch actual session data from API
  const mockSessions = [
    {
      id: '1',
      user_input: 'I want to create a chatbot for customer service',
      status: 'completed',
      created_at: '2025-11-03T10:00:00Z',
      final_prompt: 'Customer service chatbot prompt...',
    },
    {
      id: '2',
      user_input: 'Create a data analysis script for sales data',
      status: 'completed',
      created_at: '2025-11-03T09:30:00Z',
      final_prompt: 'Data analysis script prompt...',
    },
  ];

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Session History
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          View and search previous prompt generation sessions
        </Typography>

        <TableContainer component={Paper} sx={{ mt: 3 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>User Input</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {mockSessions.map((session) => (
                <TableRow key={session.id}>
                  <TableCell>
                    {new Date(session.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {session.user_input.substring(0, 100)}
                    {session.user_input.length > 100 ? '...' : ''}
                  </TableCell>
                  <TableCell>
                    <Box
                      component="span"
                      sx={{
                        px: 2,
                        py: 1,
                        bgcolor:
                          session.status === 'completed'
                            ? 'success.light'
                            : 'warning.light',
                        borderRadius: 1,
                        color:
                          session.status === 'completed'
                            ? 'success.dark'
                            : 'warning.dark',
                        fontSize: '0.875rem',
                        fontWeight: 'bold',
                      }}
                    >
                      {session.status}
                    </Box>
                  </TableCell>
                  <TableCell>
                    {/* TODO: Add view details button */}
                    View Details
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {mockSessions.length === 0 && (
          <Paper sx={{ p: 3, mt: 3, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              No sessions found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Create your first session to get started
            </Typography>
          </Paper>
        )}
      </Box>
    </Container>
  );
};

export default History;